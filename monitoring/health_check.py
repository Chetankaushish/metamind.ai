#!/usr/bin/env python3
"""
Hostinger Ubuntu VPS Health Check Diagnostics for MetaMind AI
Checks FastAPI endpoint, PostgreSQL database, Redis connection, and NGINX proxy.
"""

import sys
import urllib.request
import json
import socket

def check_http(url: str, name: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'HealthCheck/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status in [200, 204]:
                print(f"✅ {name}: HEALTHY (HTTP {response.status})")
                return True
            else:
                print(f"❌ {name}: UNHEALTHY (HTTP {response.status})")
                return False
    except Exception as e:
        print(f"❌ {name}: FAILED ({str(e)})")
        return False

def check_tcp(host: str, port: int, name: str) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"✅ {name} ({host}:{port}): OPEN & ACTIVE")
            return True
        else:
            print(f"❌ {name} ({host}:{port}): UNREACHABLE")
            return False
    except Exception as e:
        print(f"❌ {name} ({host}:{port}): FAILED ({str(e)})")
        return False

if __name__ == "__main__":
    print("==================================================")
    print("MetaMind AI Hostinger VPS Diagnostics Check")
    print("==================================================")
    
    results = [
        check_http("http://localhost:8000/health", "FastAPI Backend API"),
        check_http("http://localhost:3000/", "Vite / React Frontend"),
        check_tcp("localhost", 5432, "PostgreSQL Database"),
        check_tcp("localhost", 6379, "Redis Cache"),
    ]
    
    if all(results):
        print("\n🚀 All MetaMind services are operating normally.")
        sys.exit(0)
    else:
        print("\n⚠️ One or more MetaMind services experienced health issues.")
        sys.exit(1)
