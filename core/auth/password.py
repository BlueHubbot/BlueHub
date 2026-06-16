"""
BlueHub Password Hashing Module
================================
bcrypt-based password hashing and verification with configurable rounds.
"""
from __future__ import annotations

from passlib.context import CryptContext

# bcrypt context with 12 rounds as specified in requirements
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The bcrypt hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)
