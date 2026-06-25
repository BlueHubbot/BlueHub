"""
BlueHub Application Entry Point
================================
FastAPI application with router registration, middleware,
lifecycle events, and exception handlers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1 import (
    admin,
    audit,
    auth,
    billing,
    modules,
    monitoring,
    rbac,
    smartdns,
    tenants,
    users,
    vpn,
    vps,
    webhooks,
)
from core.config import settings
from core.database import db_manager
from core.i18n import I18nMiddleware
from core.registry import module_registry_service

# ── Application Lifespan ───────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup/shutdown events.
    Initialize and dispose of database connections.
    """
    # Startup: verify database connectivity
    db_ok = await db_manager.check_connection()
    if not db_ok:
        app.logger.warning(
            "Database connection check failed on startup. "
            "Service may be unavailable until database is reachable."
        )
    else:
        # Register modules on startup
        try:
            async with db_manager.async_session_factory() as session:
                count = await module_registry_service.register_modules(session)
                app.logger.info("Registered %d modules on startup", count)
        except Exception:
            app.logger.exception("Failed to register modules on startup")

    yield

    # Shutdown: dispose of all engine connections
    await db_manager.close()


# ── Exception Handlers ─────────────────────────────────────────────────────


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle database-related errors gracefully."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database service unavailable. Please try again later.",
            "error": str(exc) if settings.APP_DEBUG else None,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
            "error": str(exc) if settings.APP_DEBUG else None,
        },
    )


# ── FastAPI Application ────────────────────────────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    # Disable default 422 error detail in production
    debug=settings.APP_DEBUG,
)


# ── CORS Middleware ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── I18n Middleware ────────────────────────────────────────────────────────

app.add_middleware(I18nMiddleware)


# ── Router Registration ────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(modules.router)
app.include_router(admin.router)
app.include_router(webhooks.router)
app.include_router(monitoring.router)
app.include_router(rbac.router)
app.include_router(billing.router)
app.include_router(audit.router)
app.include_router(tenants.router)
app.include_router(vpn.router)
app.include_router(vps.router)
app.include_router(smartdns.router)


# ── Exception Handler Registration ─────────────────────────────────────────

app.add_exception_handler(Exception, generic_error_handler)


# ── Root Health Check ──────────────────────────────────────────────────────


@app.get(
    "/",
    tags=["Health"],
    summary="Root health check",
    description="Health check endpoint to verify the API is running.",
)
async def root():
    """Health check endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Detailed health check",
    description="Detailed health check including database connectivity.",
)
async def health_check():
    """Detailed health check with database status."""
    db_healthy = await db_manager.check_connection()
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
    }


# ── Direct Execution ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_DEBUG,
        log_level="debug" if settings.APP_DEBUG else "info",
    )


__all__ = ["app"]
