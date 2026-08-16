import secrets
import datetime
import html
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Cookie, Header, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.core.config import settings
from app.core.redis import redis_client
from app.core.security import (
    encrypt_token,
    decrypt_token,
    mask_token,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    verify_password,
    hash_password
)
from app.core.logging import logger
from app.models.models import (
    User,
    MetaAccount,
    OAuthToken,
    BusinessManager,
    AdAccount,
    Organization,
    OrganizationMember,
    UserSession,
    AuditLog
)
from app.schemas.schemas import (
    MetaLoginResponse,
    MetaSelectionRequest,
    MetaAuthStatusResponse,
    BusinessManagerResponse,
    AdAccountResponse,
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    VerifyEmailRequest,
    AuthTokenResponse,
    SessionResponse
)
from app.services.security_service import security_service
from app.services.tenant_middleware import get_tenant_context, TenantContext

router = APIRouter(tags=["Production Authentication & OAuth"])

SCOPES = [
    "ads_management",
    "ads_read",
    "business_management",
    "pages_read_engagement",
    "instagram_basic",
    "leads_retrieval"
]

def _parse_user_agent(user_agent: str) -> Dict[str, str]:
    device_type = "desktop"
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "iphone" in ua_lower or "android" in ua_lower:
        device_type = "mobile"
    elif "ipad" in ua_lower or "tablet" in ua_lower:
        device_type = "tablet"

    browser = "Chrome Browser"
    if "firefox" in ua_lower:
        browser = "Firefox Browser"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari Browser"
    elif "edge" in ua_lower:
        browser = "Microsoft Edge"

    return {
        "device_name": f"{browser} ({device_type.capitalize()})",
        "device_type": device_type,
        "browser": browser
    }

# =============================================================================
# Core Authentication Routes (Register, Login, Refresh, Logout, Password)
# =============================================================================

@router.post("/auth/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new MetaMind user, hash password with PBKDF2/bcrypt, create default Organization,
    generate JWT access token, and establish active UserSession.
    """
    # Check existing user
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email address already exists.")

    hashed_pw = hash_password(payload.password)
    verification_token = secrets.token_urlsafe(32)

    new_user = User(
        email=payload.email,
        hashed_password=hashed_pw,
        full_name=payload.full_name or payload.email.split("@")[0].title(),
        company_name=payload.company_name or "MetaMind Enterprise",
        role="Admin",
        plan="Enterprise",
        is_active=True,
        is_verified=True,  # Default auto-verified for frictionless onboarding
        verification_token=verification_token
    )
    db.add(new_user)
    await db.flush()

    # Create default Organization
    org_slug = f"org-{(payload.company_name or 'default').lower().replace(' ', '-')}-{secrets.token_hex(3)}"
    new_org = Organization(
        name=payload.company_name or f"{new_user.full_name}'s Organization",
        slug=org_slug,
        is_active=True
    )
    db.add(new_org)
    await db.flush()

    # Add user as Organization Owner
    org_member = OrganizationMember(
        organization_id=new_org.id,
        user_id=new_user.id,
        role="Owner"
    )
    db.add(org_member)

    # Log Audit
    audit = AuditLog(
        organization_id=new_org.id,
        user_id=new_user.id,
        action="USER_REGISTER_SUCCESS",
        resource_type="user",
        resource_id=new_user.id,
        ip_address=request.client.host if request.client else None,
        details={"email": new_user.email, "org_id": new_org.id}
    )
    db.add(audit)

    # Issue Tokens
    token_payload = {
        "sub": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "org_id": new_org.id
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token({"sub": new_user.id, "email": new_user.email})

    # Register Active User Session
    ua = request.headers.get("User-Agent", "Browser")
    ua_info = _parse_user_agent(ua)
    ip_addr = request.client.host if request.client else None

    now = datetime.datetime.now(datetime.timezone.utc)
    user_session = UserSession(
        user_id=new_user.id,
        organization_id=new_org.id,
        session_token=refresh_token,
        device_name=ua_info["device_name"],
        device_type=ua_info["device_type"],
        browser=ua_info["browser"],
        ip_address=ip_addr,
        is_trusted=True,
        expires_at=now + datetime.timedelta(days=7),
        is_revoked=False
    )
    db.add(user_session)

    await db.commit()

    # Set HTTP-only Cookie for Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=604800
    )

    logger.info("user_registered_successfully", user_id=new_user.id, email=new_user.email)

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "company_name": new_user.company_name,
            "organization_id": new_org.id,
            "is_verified": new_user.is_verified
        }
    )

@router.post("/auth/login", response_model=AuthTokenResponse)
async def user_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email & password, create active device session, log audit event,
    and return JWT access token with HTTP-only refresh cookie.
    """
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    ip_addr = request.client.host if request.client else None

    if not user or not verify_password(payload.password, user.hashed_password):
        audit = AuditLog(
            user_id="usr_unauthenticated",
            action="USER_LOGIN_FAILED",
            resource_type="auth",
            ip_address=ip_addr,
            result="FAILURE",
            details={"attempted_email": payload.email}
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Contact your administrator.")

    # Find primary organization
    stmt_org = select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    res_org = await db.execute(stmt_org)
    member = res_org.scalars().first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User organization membership not found.")
    org_id = member.organization_id

    # Issue Tokens
    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "org_id": org_id
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token({"sub": user.id, "email": user.email})

    # Track Active Device Session
    ua = request.headers.get("User-Agent", "Browser")
    ua_info = _parse_user_agent(ua)
    now = datetime.datetime.now(datetime.timezone.utc)

    session_record = UserSession(
        user_id=user.id,
        organization_id=org_id,
        session_token=refresh_token,
        device_name=ua_info["device_name"],
        device_type=ua_info["device_type"],
        browser=ua_info["browser"],
        ip_address=ip_addr,
        is_trusted=True,
        expires_at=now + datetime.timedelta(days=7),
        is_revoked=False
    )
    db.add(session_record)

    # Audit Log
    audit = AuditLog(
        organization_id=org_id,
        user_id=user.id,
        action="USER_LOGIN_SUCCESS",
        resource_type="auth",
        ip_address=ip_addr,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()

    # Set HTTP-only refresh cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=604800
    )

    logger.info("user_login_successful", user_id=user.id, email=user.email)

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company_name": user.company_name,
            "organization_id": org_id,
            "is_verified": getattr(user, "is_verified", True)
        }
    )

@router.post("/auth/logout")
async def user_logout(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user, revoke current session token in database, and delete HTTP-only cookie.
    """
    token_to_revoke = refresh_token
    if not token_to_revoke and authorization and authorization.startswith("Bearer "):
        token_to_revoke = authorization[7:].strip()

    if token_to_revoke:
        stmt = select(UserSession).where(UserSession.session_token == token_to_revoke)
        res = await db.execute(stmt)
        sess = res.scalar_one_or_none()
        if sess:
            sess.is_revoked = True
            audit = AuditLog(
                organization_id=sess.organization_id,
                user_id=sess.user_id,
                action="USER_LOGOUT",
                resource_type="session",
                resource_id=sess.id
            )
            db.add(audit)

    await db.commit()
    response.delete_cookie(key="refresh_token", path="/")

    logger.info("user_logout_completed")
    return {"status": "success", "message": "Successfully logged out and session revoked."}

@router.post("/auth/refresh")
async def refresh_access_token(
    request: Request,
    refresh_token: Optional[str] = Cookie(None),
    payload_token: Optional[dict] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange valid HTTP-only refresh token or body token for a new short-lived JWT access token.
    """
    token = refresh_token
    if not token and payload_token and "refresh_token" in payload_token:
        token = payload_token["refresh_token"]

    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing in request.")

    jwt_payload = decode_jwt_token(token)
    if not jwt_payload or jwt_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user_id = jwt_payload.get("sub")
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User account not found or inactive.")

    # Check session revoked
    stmt_sess = select(UserSession).where(UserSession.session_token == token)
    sess = (await db.execute(stmt_sess)).scalar_one_or_none()
    if sess and sess.is_revoked:
        raise HTTPException(status_code=401, detail="Session has been revoked.")

    stmt_org = select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    member = (await db.execute(stmt_org)).scalars().first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User organization membership not found.")
    org_id = member.organization_id

    new_access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "org_id": org_id
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/auth/me")
async def get_current_user_profile(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch authenticated user's current profile, role permissions, and active organization context.
    """
    stmt = select(User).where(User.id == tenant_ctx.user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "company_name": user.company_name,
        "plan": user.plan,
        "organization_id": tenant_ctx.organization_id,
        "is_verified": getattr(user, "is_verified", True)
    }

@router.post("/auth/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate password reset token for user account and log request.
    """
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        # Prevent user enumeration attacks
        return {"status": "success", "message": "If an account exists with this email, password reset instructions have been sent."}

    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    audit = AuditLog(
        organization_id=(await db.execute(select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id))).scalar(),
        user_id=user.id,
        action="FORGOT_PASSWORD_REQUESTED",
        resource_type="user",
        details={"email": user.email}
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": "Password reset instructions generated successfully.",
        "reset_token": reset_token  # Provided for immediate client consumption in VPS preview
    }

@router.post("/auth/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset account password using verified token and revoke active sessions for security.
    """
    stmt = select(User).where(User.reset_token == payload.token)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    now = datetime.datetime.now(datetime.timezone.utc)
    if not user or not user.reset_token_expires or user.reset_token_expires < now:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None

    # Revoke all existing sessions for security
    stmt_revoke = select(UserSession).where(UserSession.user_id == user.id)
    res_revoke = await db.execute(stmt_revoke)
    for sess in res_revoke.scalars().all():
        sess.is_revoked = True

    audit = AuditLog(
        organization_id=(await db.execute(select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id))).scalar(),
        user_id=user.id,
        action="PASSWORD_RESET_SUCCESS",
        resource_type="user"
    )
    db.add(audit)
    await db.commit()

    return {"status": "success", "message": "Password reset successfully. Please log in with your new credentials."}

@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for authenticated user.
    """
    stmt = select(User).where(User.id == tenant_ctx.user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    user.hashed_password = hash_password(payload.new_password)

    audit = AuditLog(
        organization_id=tenant_ctx.organization_id,
        user_id=user.id,
        action="PASSWORD_CHANGED",
        resource_type="user"
    )
    db.add(audit)
    await db.commit()

    return {"status": "success", "message": "Password changed successfully."}

@router.post("/auth/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email using verification token.
    """
    stmt = select(User).where(User.verification_token == payload.token)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token.")

    user.is_verified = True
    user.verification_token = None

    audit = AuditLog(
        organization_id=(await db.execute(select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id))).scalar(),
        user_id=user.id,
        action="EMAIL_VERIFIED",
        resource_type="user"
    )
    db.add(audit)
    await db.commit()

    return {"status": "success", "message": "Email address verified successfully."}

# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.get("/auth/sessions", response_model=List[SessionResponse])
async def get_active_sessions(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve active devices and sessions for authenticated user.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return await security_service.list_sessions(
        db=db,
        user_id=tenant_ctx.user_id,
        org_id=tenant_ctx.organization_id,
        current_token=token
    )

@router.post("/auth/sessions/logout-others")
async def logout_other_sessions(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke all active sessions except the current active request session.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    count = await security_service.logout_all_devices(
        db=db,
        user_id=tenant_ctx.user_id,
        current_token=token
    )
    return {"status": "success", "revoked_count": count, "message": "All other device sessions logged out."}

@router.delete("/auth/sessions/{session_id}")
async def revoke_specific_session(
    session_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke specific device session by ID.
    """
    success = await security_service.revoke_session(
        db=db,
        session_id=session_id,
        user_id=tenant_ctx.user_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or already revoked.")
    return {"status": "success", "message": f"Session '{session_id}' revoked successfully."}

# =============================================================================
# Meta OAuth & Account Integration Routes
# =============================================================================


def _require_meta_oauth_settings() -> tuple[str, str, str]:
    """Return required Meta OAuth settings; fail fast when configuration is missing."""
    app_id = settings.META_APP_ID
    app_secret = settings.META_APP_SECRET
    redirect_uri = settings.META_REDIRECT_URI

    if not app_id or not app_secret or not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meta OAuth is not configured. Set META_APP_ID, META_APP_SECRET and META_REDIRECT_URI.",
        )

    return app_id, app_secret, redirect_uri


def _normalize_ad_account_id(value: Optional[str]) -> Optional[str]:
    """Normalize Meta account IDs to the canonical act_<id> form."""
    if not value:
        return None
    value = str(value).strip()
    return value if value.startswith("act_") else f"act_{value}"


def _meta_account_status(raw_status: Any) -> str:
    """Translate Meta's numeric account status into a stable application status."""
    status_map = {
        1: "active",
        2: "disabled",
        3: "unapproved",
        7: "pending_risk_review",
        8: "pending_closure",
        9: "grace_period",
        100: "pending_risk_payment",
        101: "grace_period",
    }
    try:
        return status_map.get(int(raw_status), "unknown")
    except (TypeError, ValueError):
        return str(raw_status or "unknown").lower()


async def _meta_graph_error(response: httpx.Response, operation: str) -> str:
    """Build a safe, useful error message from a Meta Graph API response."""
    try:
        data = response.json()
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") or data.get("message") if isinstance(data, dict) else None
        return f"Meta {operation} failed ({response.status_code}): {message or 'Unknown Meta API error'}"
    except Exception:
        return f"Meta {operation} failed with HTTP {response.status_code}."


@router.post("/auth/meta/login", response_model=MetaLoginResponse, tags=["Meta OAuth"])
async def meta_oauth_login():
    """Initiate the Meta OAuth flow using only configured application credentials."""
    app_id, _, redirect_uri = _require_meta_oauth_settings()
    state = secrets.token_urlsafe(32)

    if redis_client:
        try:
            await redis_client.setex(f"oauth_state:{state}", 600, "valid")
        except Exception as exc:
            logger.warning("oauth_state_redis_save_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OAuth state storage is unavailable. Please try again.",
            ) from exc

    scope_str = ",".join(SCOPES)
    auth_url = (
        f"https://www.facebook.com/{settings.META_GRAPH_API_VERSION}/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={scope_str}"
        f"&response_type=code"
    )

    logger.info("meta_oauth_login_initiated", app_id=app_id, redirect_uri=redirect_uri)
    return MetaLoginResponse(authorization_url=auth_url, state=state)


@router.get("/auth/meta/callback", response_class=HTMLResponse, tags=["Meta OAuth"])
async def meta_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange the Meta authorization code, fetch the real Meta user/business/ad-account
    data, encrypt the token, and persist everything in PostgreSQL.
    """
    if error:
        safe_error = html.escape(error_description or error)
        return HTMLResponse(
            content=f"<h2>Meta Authentication Failed</h2><p>{safe_error}</p>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Meta OAuth code or state parameter.",
        )

    if redis_client:
        try:
            valid = await redis_client.get(f"oauth_state:{state}")
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OAuth state.",
                )
            await redis_client.delete(f"oauth_state:{state}")
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("oauth_state_redis_check_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OAuth state validation is unavailable. Please try again.",
            ) from exc

    app_id, app_secret, redirect_uri = _require_meta_oauth_settings()
    graph_version = settings.META_GRAPH_API_VERSION
    token_url = f"https://graph.facebook.com/{graph_version}/oauth/access_token"

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_res = await client.get(
            token_url,
            params={
                "client_id": app_id,
                "redirect_uri": redirect_uri,
                "client_secret": app_secret,
                "code": code,
            },
        )
        if token_res.status_code != 200:
            detail = await _meta_graph_error(token_res, "authorization-code exchange")
            logger.error("meta_oauth_code_exchange_failed", status=token_res.status_code)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        short_token = token_res.json().get("access_token")
        if not short_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Meta did not return an access token.",
            )

        long_res = await client.get(
            token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
        )
        if long_res.status_code != 200:
            detail = await _meta_graph_error(long_res, "long-lived token exchange")
            logger.error("meta_long_lived_token_exchange_failed", status=long_res.status_code)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        long_token = long_res.json().get("access_token")
        if not long_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Meta did not return a long-lived access token.",
            )

        me_res = await client.get(
            f"https://graph.facebook.com/{graph_version}/me",
            params={"fields": "id,name,email", "access_token": long_token},
        )
        if me_res.status_code != 200:
            detail = await _meta_graph_error(me_res, "user profile fetch")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        me_data = me_res.json()
        meta_user_id = me_data.get("id")
        if not meta_user_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Meta user ID was not returned by the Graph API.",
            )

        meta_user_name = me_data.get("name") or meta_user_id
        meta_user_email = me_data.get("email")

        bm_res = await client.get(
            f"https://graph.facebook.com/{graph_version}/me/businesses",
            params={
                "fields": "id,name,verification_status",
                "access_token": long_token,
            },
        )
        if bm_res.status_code != 200:
            detail = await _meta_graph_error(bm_res, "business manager fetch")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
        fetched_bms = bm_res.json().get("data", [])

        ad_res = await client.get(
            f"https://graph.facebook.com/{graph_version}/me/adaccounts",
            params={
                "fields": "id,name,account_id,currency,timezone,account_status,spend_cap,amount_spent,business",
                "access_token": long_token,
            },
        )
        if ad_res.status_code != 200:
            detail = await _meta_graph_error(ad_res, "ad account fetch")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
        fetched_ads = ad_res.json().get("data", [])

    encrypted_tok = encrypt_token(long_token)

    # Meta's long-lived user token lifetime is returned by the token exchange when
    # available. Keep a conservative application-side expiry for the stored record.
    expires_datetime = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=60)

    account_stmt = select(MetaAccount).where(MetaAccount.meta_user_id == meta_user_id)
    meta_acc = (await db.execute(account_stmt)).scalar_one_or_none()

    if not meta_acc:
        meta_acc = MetaAccount(
            meta_user_id=meta_user_id,
            name=meta_user_name,
            email=meta_user_email,
            connection_status="connected",
        )
        db.add(meta_acc)
        await db.flush()
    else:
        meta_acc.connection_status = "connected"
        meta_acc.name = meta_user_name
        meta_acc.email = meta_user_email

    db.add(
        OAuthToken(
            meta_account_id=meta_acc.id,
            encrypted_access_token=encrypted_tok,
            token_type="long_lived_user",
            scopes=SCOPES,
            expires_at=expires_datetime,
            is_valid=True,
        )
    )

    # Upsert Business Managers from Meta. No fallback or fabricated accounts.
    bm_db_by_meta_id: Dict[str, BusinessManager] = {}
    for index, business in enumerate(fetched_bms):
        bm_meta_id = business.get("id")
        if not bm_meta_id:
            continue

        bm_stmt = select(BusinessManager).where(
            BusinessManager.bm_meta_id == bm_meta_id
        )
        existing_bm = (await db.execute(bm_stmt)).scalar_one_or_none()

        if existing_bm:
            existing_bm.meta_account_id = meta_acc.id
            existing_bm.name = business.get("name") or existing_bm.name
            existing_bm.verification_status = business.get("verification_status") or existing_bm.verification_status
            existing_bm.is_primary = index == 0
            bm_db_by_meta_id[bm_meta_id] = existing_bm
        else:
            new_bm = BusinessManager(
                bm_meta_id=bm_meta_id,
                meta_account_id=meta_acc.id,
                name=business.get("name") or bm_meta_id,
                verification_status=business.get("verification_status") or "unknown",
                ad_accounts_count=0,
                is_primary=index == 0,
            )
            db.add(new_bm)
            bm_db_by_meta_id[bm_meta_id] = new_bm

    await db.flush()

    # Refresh the mapping with database IDs after flush.
    if bm_db_by_meta_id:
        bm_ids = list(bm_db_by_meta_id.keys())
        bm_rows = (
            await db.execute(
                select(BusinessManager).where(BusinessManager.bm_meta_id.in_(bm_ids))
            )
        ).scalars().all()
        bm_db_by_meta_id = {row.bm_meta_id: row for row in bm_rows}

    # Upsert real Meta ad accounts and associate each one with its real Business Manager.
    for account in fetched_ads:
        account_id = _normalize_ad_account_id(account.get("account_id") or account.get("id"))
        if not account_id:
            continue

        business = account.get("business") or {}
        business_meta_id = business.get("id") if isinstance(business, dict) else None
        linked_bm = bm_db_by_meta_id.get(business_meta_id)

        raw_spend_cap = account.get("spend_cap")
        raw_amount_spent = account.get("amount_spent")

        try:
            spend_limit = float(raw_spend_cap) / 100 if raw_spend_cap is not None else 0.0
        except (TypeError, ValueError):
            spend_limit = 0.0

        try:
            amount_spent = float(raw_amount_spent) / 100 if raw_amount_spent is not None else 0.0
        except (TypeError, ValueError):
            amount_spent = 0.0

        ad_acc_stmt = select(AdAccount).where(AdAccount.account_id == account_id)
        existing_ad = (await db.execute(ad_acc_stmt)).scalar_one_or_none()

        values = {
            "account_id": account_id,
            "account_name": account.get("name") or account_id,
            "meta_account_id": meta_acc.id,
            "business_manager_id": linked_bm.id if linked_bm else None,
            "currency": account.get("currency") or "",
            "timezone": account.get("timezone") or "",
            "spend_limit": spend_limit,
            "amount_spent": amount_spent,
            "status": _meta_account_status(account.get("account_status")),
        }

        if existing_ad:
            for field, value in values.items():
                setattr(existing_ad, field, value)
        else:
            db.add(AdAccount(**values))

    # Keep Business Manager account counts consistent with the real Meta payload.
    counts: Dict[str, int] = {}
    for account in fetched_ads:
        business = account.get("business") or {}
        business_meta_id = business.get("id") if isinstance(business, dict) else None
        if business_meta_id:
            counts[business_meta_id] = counts.get(business_meta_id, 0) + 1

    for bm_meta_id, bm in bm_db_by_meta_id.items():
        bm.ad_accounts_count = counts.get(bm_meta_id, 0)

    await db.commit()

    safe_name = html.escape(meta_user_name)
    safe_uid = html.escape(meta_user_id)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Meta Authentication Successful</title></head>
    <body style="font-family: system-ui, sans-serif; text-align: center; padding: 50px;">
        <h2>Meta Account Connected</h2>
        <p>Connected as <strong>{safe_name}</strong></p>
        <p>Closing window and returning to dashboard...</p>
        <script>
            if (window.opener) {{
                window.opener.postMessage({{ type: 'META_AUTH_SUCCESS', userId: '{safe_uid}' }}, '*');
                setTimeout(() => window.close(), 1200);
            }} else {{
                setTimeout(() => {{ window.location.href = '/'; }}, 1500);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get("/auth/meta/status", response_model=MetaAuthStatusResponse, tags=["Meta OAuth"])
async def get_meta_auth_status(db: AsyncSession = Depends(get_db)):
    """Return the current stored Meta connection and token status."""
    account_stmt = (
        select(MetaAccount)
        .where(MetaAccount.connection_status == "connected")
        .order_by(MetaAccount.created_at.desc())
    )
    meta_acc = (await db.execute(account_stmt)).scalar_one_or_none()

    if not meta_acc:
        return MetaAuthStatusResponse(
            connected=False,
            is_valid=False,
            scopes=SCOPES,
        )

    token_stmt = (
        select(OAuthToken)
        .where(
            OAuthToken.meta_account_id == meta_acc.id,
            OAuthToken.is_valid == True,
        )
        .order_by(OAuthToken.created_at.desc())
    )
    token_rec = (await db.execute(token_stmt)).scalar_one_or_none()

    masked = mask_token(decrypt_token(token_rec.encrypted_access_token)) if token_rec else None
    expires_str = token_rec.expires_at.isoformat() if token_rec and token_rec.expires_at else None
    is_valid = bool(token_rec and token_rec.is_valid)

    if token_rec and token_rec.expires_at and token_rec.expires_at < datetime.datetime.now(datetime.timezone.utc):
        is_valid = False
        meta_acc.connection_status = "expired"
        token_rec.is_valid = False
        await db.commit()

    bm_stmt = select(BusinessManager).where(
        BusinessManager.meta_account_id == meta_acc.id,
        BusinessManager.is_primary == True,
    )
    bm = (await db.execute(bm_stmt)).scalar_one_or_none()

    ad_acc_stmt = select(AdAccount).where(AdAccount.meta_account_id == meta_acc.id)
    ad_acc = (await db.execute(ad_acc_stmt)).scalars().first()

    return MetaAuthStatusResponse(
        connected=meta_acc.connection_status == "connected",
        meta_user_id=meta_acc.meta_user_id,
        meta_user_name=meta_acc.name,
        masked_token=masked,
        token_type=token_rec.token_type if token_rec else None,
        is_valid=is_valid,
        expires_at=expires_str,
        scopes=token_rec.scopes if token_rec else SCOPES,
        last_connected=meta_acc.last_connected.isoformat() if meta_acc.last_connected else None,
        primary_business_name=bm.name if bm else None,
        primary_ad_account_name=ad_acc.account_name if ad_acc else None,
    )


@router.post("/auth/meta/reconnect", response_model=MetaLoginResponse, tags=["Meta OAuth"])
async def meta_oauth_reconnect():
    """Start a fresh Meta OAuth flow for a disconnected or expired connection."""
    return await meta_oauth_login()


@router.post("/auth/meta/logout", tags=["Meta OAuth"])
async def meta_oauth_logout(db: AsyncSession = Depends(get_db)):
    """Disconnect the stored Meta account and invalidate its access tokens."""
    account_stmt = select(MetaAccount).where(MetaAccount.connection_status == "connected")
    meta_accounts = (await db.execute(account_stmt)).scalars().all()

    for account in meta_accounts:
        account.connection_status = "disconnected"
        token_stmt = select(OAuthToken).where(OAuthToken.meta_account_id == account.id)
        tokens = (await db.execute(token_stmt)).scalars().all()
        for token in tokens:
            token.is_valid = False

    await db.commit()
    logger.info("meta_oauth_logout_completed")
    return {"status": "disconnected", "message": "Meta Business account disconnected successfully."}


@router.get("/auth/meta/businesses", response_model=List[BusinessManagerResponse], tags=["Meta OAuth"])
async def list_meta_businesses(db: AsyncSession = Depends(get_db)):
    """Return Business Managers that were actually synced from Meta into PostgreSQL."""
    result = await db.execute(
        select(BusinessManager).order_by(BusinessManager.is_primary.desc(), BusinessManager.name.asc())
    )
    return result.scalars().all()


@router.get("/auth/meta/adaccounts", response_model=List[AdAccountResponse], tags=["Meta OAuth"])
async def list_meta_ad_accounts(db: AsyncSession = Depends(get_db)):
    """Return ad accounts that were actually synced from Meta into PostgreSQL."""
    result = await db.execute(
        select(AdAccount).order_by(AdAccount.account_name.asc())
    )
    return result.scalars().all()


@router.post("/auth/meta/select", tags=["Meta OAuth"])
async def select_meta_account_and_bm(
    body: MetaSelectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Persist the user's selected real Business Manager and ad account."""
    bm_stmt = select(BusinessManager).where(
        (BusinessManager.bm_meta_id == body.business_manager_id)
        | (BusinessManager.id == body.business_manager_id)
    )
    bm = (await db.execute(bm_stmt)).scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business Manager not found.")

    # Make the selected BM primary and clear the previous primary flag for the same Meta account.
    await db.execute(
        BusinessManager.__table__.update()
        .where(BusinessManager.meta_account_id == bm.meta_account_id)
        .values(is_primary=False)
    )
    bm.is_primary = True

    ad_acc_stmt = select(AdAccount).where(
        (AdAccount.account_id == body.ad_account_id)
        | (AdAccount.id == body.ad_account_id)
    )
    ad_acc = (await db.execute(ad_acc_stmt)).scalar_one_or_none()
    if not ad_acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad account not found.")

    ad_acc.business_manager_id = bm.id
    ad_acc.status = ad_acc.status or "unknown"

    await db.commit()
    logger.info(
        "meta_selection_saved",
        bm_id=body.business_manager_id,
        ad_account_id=body.ad_account_id,
    )
    return {
        "status": "success",
        "message": "Selection stored successfully in PostgreSQL.",
        "business_manager_id": body.business_manager_id,
        "ad_account_id": body.ad_account_id,
    }
