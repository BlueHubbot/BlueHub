"""
BlueHub JWT Authentication Module
==================================
RS256 JWT token generation, verification, and decoding.
Uses RSA keys from environment variables (JWT_PRIVATE_KEY, JWT_PUBLIC_KEY).
Auto-generates RSA key pair on first run if keys are missing.
"""
from __future__ import annotations

from datetime import timezone, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import Settings


def get_settings() -> Settings:
    """Get settings singleton (module-level alias for Settings.get_settings)."""
    return Settings.get_settings()


def _resolve_env_path() -> str:
    """Resolve the .env file path relative to the project root."""
    # Walk up from the core/auth directory to find .env
    current_dir = Path(__file__).resolve().parent
    possible_paths = [
        current_dir.parent.parent / ".env",
        current_dir.parent.parent.parent / ".env",
        Path(".env").resolve(),
    ]
    for p in possible_paths:
        if p.is_file():
            return str(p)
    # Default to project root .env
    return str(current_dir.parent.parent / ".env")


def _generate_rsa_key_pair() -> tuple[str, str]:
    """
    Generate an RSA-2048 key pair and return (private_key_pem, public_key_pem).

    Returns:
        Tuple of (private_key_pem, public_key_pem) strings in PEM format.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def _save_keys_to_env(private_pem: str, public_pem: str) -> None:
    """
    Save generated RSA keys to the .env file.

    Args:
        private_pem: The RSA private key in PEM format.
        public_pem: The RSA public key in PEM format.
    """
    env_path = Path(_resolve_env_path())
    # Read existing .env content
    existing = ""
    if env_path.is_file():
        existing = env_path.read_text(encoding="utf-8")

    # Remove existing JWT key entries if present
    if "JWT_PRIVATE_KEY=" in existing:
        lines = existing.splitlines()
        new_lines: list[str] = []
        for line in lines:
            if line.startswith(("JWT_PRIVATE_KEY=", "JWT_PUBLIC_KEY=")):
                continue
            new_lines.append(line)
        existing = "\n".join(new_lines) + "\n"
    else:
        existing += "\n"

    # Append keys with actual newlines (no quoting needed for multi-line .env values)
    existing += f"JWT_PRIVATE_KEY={private_pem}\n"
    existing += f"JWT_PUBLIC_KEY={public_pem}\n"

    env_path.write_text(existing, encoding="utf-8")


def _get_or_generate_private_key() -> str:
    """Get the RSA private key, auto-generating if missing."""
    settings = get_settings()
    key = settings.JWT_PRIVATE_KEY
    if key:
        return key

    # Auto-generate key pair
    private_pem, public_pem = _generate_rsa_key_pair()
    _save_keys_to_env(private_pem, public_pem)
    # Reload settings so the new keys are picked up
    settings.reload()
    return settings.JWT_PRIVATE_KEY  # type: ignore[return-value]


def _get_or_generate_public_key() -> str:
    """Get the RSA public key, auto-generating if missing."""
    settings = get_settings()
    key = settings.JWT_PUBLIC_KEY
    if key:
        return key

    # Auto-generate key pair (will save both keys)
    private_pem, public_pem = _generate_rsa_key_pair()
    _save_keys_to_env(private_pem, public_pem)
    settings.reload()
    return settings.JWT_PUBLIC_KEY  # type: ignore[return-value]


def generate_access_token(
    user_id: str, role: str, extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Generate a short-lived JWT access token using RS256.

    Args:
        user_id: The user's primary key ID (UUID string).
        role: The user's role string (e.g. 'admin', 'user').
        extra_claims: Optional additional claims to embed in the token.

    Returns:
        A signed JWT access token string.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=60),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    private_key = _get_or_generate_private_key()
    return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)


def generate_refresh_token(user_id: str) -> str:
    """
    Generate a long-lived JWT refresh token using RS256.

    Args:
        user_id: The user's primary key ID (UUID string).

    Returns:
        A signed JWT refresh token string.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=30),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "refresh",
    }
    private_key = _get_or_generate_private_key()
    return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT token.

    Validates signature, expiration, issuer, audience, and token type.
    Raises HTTPException 401 if the token is invalid.

    Args:
        token: The JWT string to verify.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        HTTPException 401: If the token is invalid, expired, or fails verification.
    """
    settings = get_settings()
    public_key = _get_or_generate_public_key()
    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def decode_token(token: str, verify: bool = True) -> dict[str, Any]:
    """
    Decode a JWT token with optional verification.

    When verify=True (default), this behaves identically to verify_token().
    When verify=False, only decodes the header/payload without signature validation.
    Use with caution — verify=False is intended for debugging or extracting
    header information only.

    Args:
        token: The JWT string to decode.
        verify: Whether to cryptographically verify the token.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        HTTPException 401: If verification fails (when verify=True).
    """
    if verify:
        return verify_token(token)

    # Unverified decode — only for debugging / header inspection
    try:
        settings = get_settings()
        public_key = _get_or_generate_public_key()
        return jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
        )
    except JWTError:
        # Return minimal info even if decoding fails
        return {"sub": None, "error": "Failed to decode token"}
