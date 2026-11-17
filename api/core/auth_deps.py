"""Shared auth dependencies and utilities."""

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from typing import Optional

from fastapi import Header, HTTPException, status
from api.config import get_settings


# ── Password hashing (stdlib PBKDF2, no extra deps) ──────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000)
    return f"pbkdf2:sha256:260000${salt}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    if not stored.startswith("pbkdf2:"):
        # Backward compat: existing plaintext mock-DB passwords
        return hmac.compare_digest(plain, stored)
    try:
        _, params, salt, dk_stored = stored.split("$")
        rounds = int(params.split(":")[2])
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), rounds)
        return hmac.compare_digest(dk.hex(), dk_stored)
    except Exception:
        return False


# ── Admin API key guard ───────────────────────────────────────────────────────

async def require_admin(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    settings = get_settings()
    if not settings.ADMIN_API_KEY:
        # No key configured — deny all; forces explicit setup in production
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


# ── Simple in-memory rate limiter ────────────────────────────────────────────

_rate_store: dict = defaultdict(list)


def check_rate_limit(identifier: str, limit: int = 5, window_secs: int = 60) -> bool:
    """Return True (and raise) if the identifier exceeds `limit` calls per `window_secs`."""
    now = time.time()
    _rate_store[identifier] = [t for t in _rate_store[identifier] if now - t < window_secs]
    if len(_rate_store[identifier]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please wait {window_secs} seconds.",
        )
    _rate_store[identifier].append(now)
