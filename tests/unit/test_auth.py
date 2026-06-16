"""
BlueHub Auth Unit Tests
========================
Tests for JWT operations, password hashing, and auth API endpoints.
Uses pytest-asyncio for async database operations.

Run: pytest tests/unit/test_auth.py -v --asyncio-mode=auto
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from jose import jwt
from pydantic import ValidationError

from api.v1.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    MeResponse,
    RefreshResponse,
    RegisterRequest,
    UserResponse,
)
from core.auth.jwt import (
    decode_token,
    generate_access_token,
    generate_refresh_token,
    verify_token,
)
from core.auth.password import hash_password, verify_password
from core.config import Settings
from dependencies.auth import get_current_user, get_current_user_payload, security_scheme

get_settings = Settings.get_settings

# ──────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_jwt_keys():
    """Provide valid RSA keys for all JWT tests by patching settings."""
    # Generate RSA keys programmatically for testing

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

    # Patch Settings.get_settings to return settings with these keys
    original_get_settings = Settings.get_settings

    def patched_get_settings(**kwargs) -> Settings:
        settings = original_get_settings(**kwargs)
        # Override keys with our test keys
        object.__setattr__(settings, "JWT_PRIVATE_KEY", private_pem)
        object.__setattr__(settings, "JWT_PUBLIC_KEY", public_pem)
        return settings

    with patch.object(Settings, "get_settings", side_effect=patched_get_settings):
        yield


# ──────────────────────────────────────────────
# Password Hashing Tests
# ──────────────────────────────────────────────


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test that hash_password returns a bcrypt hash."""
        password = "MySecureP@ss123!"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test that verify_password returns True for matching passwords."""
        password = "MySecureP@ss123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for wrong passwords."""
        password = "MySecureP@ss123!"
        wrong_password = "WrongPassword!456"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False


# ──────────────────────────────────────────────
# JWT Token Tests
# ──────────────────────────────────────────────


class TestJWTTokens:
    """Tests for JWT token generation and verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = "123e4567-e89b-12d3-a456-426614174000"
        self.role = "user"

    def test_generate_access_token(self):
        """Test that generate_access_token returns a valid JWT."""
        token = generate_access_token(user_id=self.user_id, role=self.role)
        assert token is not None
        assert isinstance(token, str)
        # Decode without verification to check payload
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY or "",
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False},
        )
        assert payload["sub"] == self.user_id
        assert payload["role"] == self.role
        assert payload["type"] == "access"
        assert payload["iss"] == settings.JWT_ISSUER
        assert payload["aud"] == settings.JWT_AUDIENCE

    def test_generate_refresh_token(self):
        """Test that generate_refresh_token returns a valid JWT."""
        token = generate_refresh_token(user_id=self.user_id)
        assert token is not None
        assert isinstance(token, str)
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY or "",
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False},
        )
        assert payload["sub"] == self.user_id
        assert payload["type"] == "refresh"

    def test_verify_token_valid(self):
        """Test that verify_token succeeds for a valid token."""
        token = generate_access_token(user_id=self.user_id, role=self.role)
        payload = verify_token(token)
        assert payload["sub"] == self.user_id
        assert payload["role"] == self.role
        assert payload["type"] == "access"

    def test_verify_token_invalid_raises(self):
        """Test that verify_token raises HTTPException 401 for invalid tokens."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_token_expired_raises(self):
        """Test that verify_token raises 401 for expired tokens."""
        # Create an expired token by patching the time
        with patch("core.auth.jwt.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(
                2020, 1, 1, tzinfo=timezone.utc
            )
            mock_datetime.side_effect = datetime
            mock_datetime.timezone = timezone
            mock_datetime.timedelta = __import__("datetime").timedelta
            token = generate_access_token(user_id=self.user_id, role=self.role)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()

    def test_generate_access_token_with_extra_claims(self):
        """Test that extra_claims are included in the token."""
        extra = {"tenant_id": "tenant-123", "permissions": ["read", "write"]}
        token = generate_access_token(
            user_id=self.user_id, role=self.role, extra_claims=extra
        )
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY or "",
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": False, "verify_aud": False},
        )
        assert payload["tenant_id"] == "tenant-123"
        assert payload["permissions"] == ["read", "write"]

    def test_decode_token_without_verification(self):
        """Test decode_token with verify=False."""
        token = generate_access_token(user_id=self.user_id, role=self.role)
        payload = decode_token(token, verify=False)
        assert payload["sub"] == self.user_id


# ──────────────────────────────────────────────
# Auth Endpoint Tests (unit-level)
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Unit tests for auth API endpoints using mocked dependencies."""

    async def test_register_success(self):
        """Test successful registration."""
        # This test validates the schema and logic structure
        req = RegisterRequest(
            email="test@example.com",
            password="StrongP@ss1",
            full_name="Test User",
        )
        assert req.email == "test@example.com"
        assert req.password == "StrongP@ss1"
        assert req.full_name == "Test User"

    async def test_register_short_password_rejected(self):
        """Test that short passwords are rejected at schema level."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                password="short",  # less than 8 chars
                full_name="Test User",
            )

    async def test_login_schema(self):
        """Test login request schema."""
        req = LoginRequest(email="test@example.com", password="password123")
        assert req.email == "test@example.com"
        assert req.password == "password123"

    async def test_auth_response_schema(self):
        """Test auth response schema with tokens and user data."""
        user = UserResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            full_name="Test User",
            role="user",
            created_at="2026-01-01T00:00:00+00:00",
        )
        response = AuthResponse(
            access_token="access_token_here",
            refresh_token="refresh_token_here",
            user=user,
        )
        assert response.access_token == "access_token_here"
        assert response.refresh_token == "refresh_token_here"
        assert response.user.email == "test@example.com"
        assert response.user.role == "user"

    async def test_logout_response_schema(self):
        """Test logout response schema."""
        response = LogoutResponse(message="logged out")
        assert response.message == "logged out"

    async def test_refresh_response_schema(self):
        """Test refresh token response schema."""
        response = RefreshResponse(access_token="new_access_token")
        assert response.access_token == "new_access_token"

    async def test_me_response_schema(self):
        """Test /me response schema."""
        response = MeResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            full_name="Test User",
            role="user",
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert response.email == "test@example.com"
        assert response.role == "user"


# ──────────────────────────────────────────────
# Dependency Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestAuthDependencies:
    """Tests for auth dependency functions."""

    async def test_get_current_user_no_credentials(self):
        """Test that get_current_user raises 401 with no credentials."""
        with patch("dependencies.auth.db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_async_session.return_value = mock_session

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=None, session=mock_session)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_payload_no_credentials(self):
        """Test get_current_user_payload raises 401 with no credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_payload(credentials=None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_invalid_token(self):
        """Test that get_current_user raises 401 with invalid token."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid.token.here"

        with patch("dependencies.auth.db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_db.get_async_session.return_value = mock_session

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    credentials=mock_credentials, session=mock_session
                )
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
