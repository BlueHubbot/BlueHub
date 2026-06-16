"""
BlueHub API Admin Router
========================
Placeholder for admin dashboard and system management endpoints.
Will be implemented with system health, stats, and configuration management.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
async def health_check() -> Any:
    """Basic health check endpoint."""
    return {"status": "healthy", "message": "Admin panel not yet implemented"}


__all__ = ["router"]
