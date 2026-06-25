"""
BlueHub Password Hashing Module
================================
bcrypt-based password hashing and verification with configurable rounds.
Uses bcrypt directly for compatibility with bcrypt >= 4.x.
"""
from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt (12 rounds).

    Args:
        password: The plain-text password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The bcrypt hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
