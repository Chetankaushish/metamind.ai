import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
import urllib.parse
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict, Any, Optional
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet_key() -> bytes:
    # Derive a valid 32-byte base64 key from settings.SECRET_KEY
    key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)

def encrypt_token(plain_token: str) -> str:
    if not plain_token:
        return ""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception:
        return ""

def mask_token(token: str) -> str:
    if not token or len(token) < 10:
        return "EAAG...9420xZ19"
    return f"{token[:4]}...{token[-6:]}"

# =============================================================================
# JWT & Refresh Token Management
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access", "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT refresh token (7-day default duration)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return {}

# =============================================================================
# SSRF Protection Helper
# =============================================================================

BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_url(url: str) -> bool:
    """Validates destination URL against internal network ranges to prevent SSRF attacks."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Reject obvious localhost / internal hostnames
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            for blocked in BLOCKED_NETWORKS:
                if ip in blocked:
                    return False
        except ValueError:
            # Hostname is a domain name, not direct IP
            pass

        return True
    except Exception:
        return False

# =============================================================================
# Password Hashing & History Security
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    if not plain_password or not stored_hash:
        return False
    try:
        # Backward compatibility check for plain SHA256 hex hashes from early seeds
        if len(stored_hash) == 64 and not stored_hash.endswith('='):
            computed = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
            return hmac.compare_digest(computed, stored_hash)

        decoded = base64.b64decode(stored_hash.encode('utf-8'))
        salt = decoded[:16]
        stored_key = decoded[16:]
        computed_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(stored_key, computed_key)
    except Exception:
        return False

# =============================================================================
# RFC 6238 Standard TOTP MFA Engine
# =============================================================================

def generate_totp_secret() -> str:
    """Generate a random Base32 secret for TOTP MFA."""
    raw_bytes = os.urandom(20)
    return base64.b32encode(raw_bytes).decode('utf-8').replace('=', '')

def compute_totp(secret: str, time_step: int = 30, interval_offset: int = 0) -> str:
    """Compute 6-digit TOTP code according to RFC 6238 standard."""
    try:
        # Pad Base32 secret
        padding = '=' * (8 - len(secret) % 8) if len(secret) % 8 != 0 else ''
        key = base64.b32decode((secret + padding).upper())
        
        counter = (int(time.time()) // time_step) + interval_offset
        msg = struct.pack(">Q", counter)
        
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        binary = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
        code = binary % 1000000
        return f"{code:06d}"
    except Exception:
        return ""

def verify_totp(secret: str, user_code: str, window: int = 1) -> bool:
    """Verify user code against TOTP secret with clock skew tolerance window."""
    clean_code = user_code.strip()
    if not clean_code or len(clean_code) != 6:
        return False
    
    for offset in range(-window, window + 1):
        if compute_totp(secret, interval_offset=offset) == clean_code:
            return True
    return False

def generate_recovery_codes(count: int = 10) -> List[str]:
    """Generate secure single-use recovery codes."""
    return [secrets.token_hex(4).upper() + "-" + secrets.token_hex(4).upper() for _ in range(count)]

# =============================================================================
# Security Headers & Policy Specification
# =============================================================================

SECURITY_HEADERS: Dict[str, str] = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https: wss:; "
        "frame-ancestors 'self';"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "X-XSS-Protection": "1; mode=block"
}


