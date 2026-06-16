"""
BlueHub Exception Hierarchy
=============================
Structured exception classes for consistent error handling
across all modules and API responses.
"""

from __future__ import annotations

from typing import Any


class BlueHubError(Exception):
    """
    Base exception for all BlueHub application errors.
    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a serializable dictionary."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# --- HTTP / API Errors ---


class NotFoundError(BlueHubError):
    """Resource not found (404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if resource_type:
            extra_details["resource_type"] = resource_type
        if resource_id:
            extra_details["resource_id"] = str(resource_id)
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=extra_details,
        )


class ConflictError(BlueHubError):
    """Resource conflict (409)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class ValidationError(BlueHubError):
    """Validation error (422)."""

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: dict[str, list[str]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if field_errors:
            extra_details["field_errors"] = field_errors
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=extra_details,
        )


class UnauthorizedError(BlueHubError):
    """Authentication required (401)."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class ForbiddenError(BlueHubError):
    """Permission denied (403)."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class RateLimitError(BlueHubError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if retry_after is not None:
            extra_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code="RATE_LIMIT",
            status_code=429,
            details=extra_details,
        )


# --- Business Logic Errors ---


class ServiceError(BlueHubError):
    """Base for service-level errors (500)."""

    def __init__(
        self,
        message: str = "Service error occurred",
        service: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if service:
            extra_details["service"] = service
        super().__init__(
            message=message,
            code="SERVICE_ERROR",
            status_code=500,
            details=extra_details,
        )


class ConfigurationError(BlueHubError):
    """Configuration or setup error (500)."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if config_key:
            extra_details["config_key"] = config_key
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=extra_details,
        )


class ExternalServiceError(BlueHubError):
    """External service/dependency failure (502)."""

    def __init__(
        self,
        message: str = "External service error",
        service: str | None = None,
        original_error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if service:
            extra_details["service"] = service
        if original_error:
            extra_details["original_error"] = original_error
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=extra_details,
        )


class DatabaseError(BlueHubError):
    """Database operation error (500)."""

    def __init__(
        self,
        message: str = "Database error occurred",
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if operation:
            extra_details["operation"] = operation
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=extra_details,
        )


# --- Module-specific Errors ---


class ModuleError(BlueHubError):
    """Base error for module-level failures."""

    def __init__(
        self,
        message: str = "Module error",
        module: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if module:
            extra_details["module"] = module
        super().__init__(
            message=message,
            code="MODULE_ERROR",
            status_code=500,
            details=extra_details,
        )


class ResourceExhaustedError(BlueHubError):
    """Resource capacity exhausted (507)."""

    def __init__(
        self,
        message: str = "Resource capacity exhausted",
        resource: str | None = None,
        current: int | None = None,
        limit: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra_details = details or {}
        if resource:
            extra_details["resource"] = resource
        if current is not None:
            extra_details["current"] = current
        if limit is not None:
            extra_details["limit"] = limit
        super().__init__(
            message=message,
            code="RESOURCE_EXHAUSTED",
            status_code=507,
            details=extra_details,
        )


__all__ = [
    "BlueHubError",
    "ConfigurationError",
    "ConflictError",
    "DatabaseError",
    "ExternalServiceError",
    "ForbiddenError",
    "ModuleError",
    "NotFoundError",
    "RateLimitError",
    "ResourceExhaustedError",
    "ServiceError",
    "UnauthorizedError",
    "ValidationError",
]
