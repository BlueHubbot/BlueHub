"""
BlueHub I18n Middleware
=======================
FastAPI middleware for automatic language detection and request-based localization.
Detects language from:
1. User's saved preference (via authenticated user in request)
2. Accept-Language header
3. Default to English
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.i18n.engine import i18n_engine

if TYPE_CHECKING:
    pass


class I18nMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that detects the user's language preference
    and attaches the I18nEngine to the request state.

    The language detection priority is:
    1. User's saved preference (from request.state.user if authenticated)
    2. Accept-Language HTTP header
    3. Default locale from settings
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process the request, detect language, and attach i18n to request state.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Detect user's preferred language
        user_preferred = None
        if hasattr(request.state, "user") and request.state.user is not None:
            user_preferred = getattr(request.state.user, "language_code", None)

        accept_language = request.headers.get("Accept-Language")

        detected_language = i18n_engine.detect_language(
            accept_language=accept_language,
            user_preferred=user_preferred,
        )

        # Attach language info to request state for use in route handlers
        request.state.language = detected_language
        request.state.i18n = i18n_engine

        # Process the request
        response = await call_next(request)

        # Set Content-Language header on the response
        response.headers["Content-Language"] = detected_language

        return response


# Convenience function to get translated message in request handlers
async def t(
    request: Request,
    key: str,
    default: str | None = None,
    **kwargs,
) -> str:
    """
    Translate a key using the request's detected language.

    Args:
        request: FastAPI request object
        key: Translation key (supports dot notation)
        default: Fallback message if translation not found
        **kwargs: Variables for substitution

    Returns:
        Translated message

    Example:
        msg = await t(request, "errors.not_found")
        msg = await t(request, "user.wallet_credited", amount="100,000")
    """
    locale = getattr(request.state, "language", None)
    return await i18n_engine.get(key, locale=locale, default=default, **kwargs)


__all__ = [
    "I18nMiddleware",
    "t",
]
