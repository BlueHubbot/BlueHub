"""
BlueHub Authentication Module
==============================
JWT-based authentication with RS256 support, 2FA/TOTP, session management.
"""

from __future__ import annotations

from core.auth.jwt import (
    decode_token,
    generate_access_token,
    generate_refresh_token,
    verify_token,
)
from core.auth.password import hash_password, verify_password

__all__: list[str] = [
    "decode_token",
    "generate_access_token",
    "generate_refresh_token",
    "hash_password",
    "verify_password",
    "verify_token",
]
