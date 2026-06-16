"""
BlueHub API Monitoring Router
=============================
Placeholder for monitoring and metrics endpoints.
Will be implemented with Prometheus metrics, health checks, and monitoring.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics")
async def metrics() -> Any:
    """Prometheus metrics endpoint placeholder."""
    return {"message": "Monitoring not yet implemented"}


__all__ = ["router"]
