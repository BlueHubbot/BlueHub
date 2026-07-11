"""
BlueHub Configuration Module
============================
Multi-environment configuration using Pydantic Settings v2.
Supports dev, test, and production environments.
Loaded from .env file and environment variables.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    """Application environment enumeration."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class LogLevel(str, Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuthAlgorithm(str, Enum):
    """JWT signing algorithm enumeration."""

    HS256 = "HS256"
    RS256 = "RS256"


class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment variables.
    Supports multiple environments via APP_ENV variable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = Field(default="BlueHub", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    APP_ENV: AppEnv = Field(default=AppEnv.DEV, description="Runtime environment")
    APP_DEBUG: bool = Field(default=False, description="Debug mode flag")
    APP_SECRET_KEY: str = Field(
        default="change-me-in-production",
        min_length=16,
        description="Secret key for JWT & encryption",
    )

    # --- JWT ---
    JWT_ALGORITHM: AuthAlgorithm = Field(
        default=AuthAlgorithm.RS256,
        description="JWT signing algorithm",
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        ge=1,
        description="Access token expiry in minutes",
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        ge=1,
        description="Refresh token expiry in days",
    )
    JWT_PUBLIC_KEY: str | None = Field(
        default=None,
        description="RSA public key in PEM format",
    )
    JWT_PRIVATE_KEY: str | None = Field(
        default=None,
        description="RSA private key in PEM format",
    )
    JWT_ISSUER: str = Field(
        default="bluehub",
        description="JWT issuer claim",
    )
    JWT_AUDIENCE: str = Field(
        default="bluehub-api",
        description="JWT audience claim",
    )

    # --- Server ---
    HOST: str = Field(default="0.0.0.0", description="Server bind address")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Server port")
    WORKERS: int = Field(default=4, ge=1, le=32, description="Number of workers")
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://109.199.108.30:3001",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://109.199.108.30:8000",
        ],
        description="Allowed CORS origins"
    )

    # --- Database (async with asyncpg) ---
    DATABASE_URL: PostgresDsn | None = Field(
        default=None,
        description="PostgreSQL async connection string (asyncpg)",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, description="DB pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, description="DB pool overflow")
    DATABASE_ECHO: bool = Field(default=False, description="SQL echo mode")
    DATABASE_MIGRATE_ON_START: bool = Field(
        default=True, description="Auto-run migrations on startup"
    )
    DATABASE_TIMEOUT: int = Field(
        default=30, ge=1, description="Database connection timeout in seconds"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None, info) -> str | None:
        """Build async database URL from parts if not provided."""
        if v:
            return v
        # Build from parts as fallback using asyncpg
        base = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub",
        )
        env = info.data.get("APP_ENV", AppEnv.DEV)
        if env == AppEnv.TEST:
            base = "postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub_test"
        elif env == AppEnv.PROD:
            base = os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub",
            )
        return base

    # --- Redis ---
    REDIS_URL: RedisDsn | None = Field(
        default=None, description="Redis connection string"
    )
    REDIS_POOL_SIZE: int = Field(default=10, ge=1, description="Redis pool size")
    REDIS_TIMEOUT: int = Field(
        default=5, ge=1, description="Redis connection timeout in seconds"
    )
    REDIS_SOCKET_KEEPALIVE: bool = Field(
        default=True, description="Enable Redis socket keepalive"
    )
    REDIS_RETRY_ON_TIMEOUT: bool = Field(
        default=True, description="Retry Redis on timeout"
    )

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, v: str | None) -> str | None:
        """Build Redis URL from parts if not provided."""
        if v:
            return v
        return os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- Celery ---
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend"
    )
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default=False, description="Run tasks synchronously"
    )
    CELERY_TASK_EAGER_PROPAGATES: bool = Field(
        default=False, description="Propagate eager task exceptions"
    )
    CELERY_TASK_SERIALIZER: str = Field(
        default="json", description="Task serializer"
    )
    CELERY_RESULT_SERIALIZER: str = Field(
        default="json", description="Result serializer"
    )
    CELERY_ACCEPT_CONTENT: list[str] = Field(
        default=["json"], description="Accepted content types"
    )
    CELERY_MAX_RETRIES: int = Field(
        default=3, ge=0, description="Max task retries"
    )
    CELERY_TASK_TRACK_STARTED: bool = Field(
        default=True, description="Track started tasks"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=3600, ge=1, description="Task time limit in seconds"
    )
    CELERY_BEAT_SCHEDULE_FILENAME: str = Field(
        default="celerybeat-schedule", description="Beat schedule filename"
    )

    # --- Logging ---
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    LOG_FORMAT: str = Field(
        default="json", description="Log format: json or console"
    )
    LOG_FILE: str | None = Field(
        default=None, description="Optional log file path"
    )
    LOG_INCLUDE_TRACEBACK: bool = Field(
        default=True, description="Include traceback in log entries"
    )

    # --- File Storage ---
    STORAGE_DIR: str = Field(
        default="./storage", description="Local file storage path"
    )
    STORAGE_MAX_FILE_SIZE: int = Field(
        default=100 * 1024 * 1024,  # 100 MB
        description="Max upload file size in bytes",
    )
    STORAGE_ALLOWED_EXTENSIONS: list[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "pdf", "txt", "zip", "tar", "gz"],
        description="Allowed file extensions for upload",
    )

    # --- 2FA / TOTP ---
    TOTP_ISSUER_NAME: str = Field(
        default="BlueHub",
        description="TOTP issuer name for authenticator apps",
    )
    TOTP_VALID_WINDOW: int = Field(
        default=1,
        ge=0,
        description="TOTP valid window (steps before/after)",
    )

    # --- MinIO / S3 Object Storage ---
    MINIO_ENDPOINT: str | None = Field(
        default=None, description="MinIO server endpoint"
    )
    MINIO_ACCESS_KEY: str | None = Field(
        default=None, description="MinIO access key"
    )
    MINIO_SECRET_KEY: str | None = Field(
        default=None, description="MinIO secret key"
    )
    MINIO_BUCKET: str = Field(
        default="bluehub", description="Default MinIO bucket"
    )
    MINIO_SECURE: bool = Field(
        default=False, description="Use TLS for MinIO"
    )
    MINIO_REGION: str = Field(
        default="us-east-1", description="MinIO region"
    )

    # --- Billing / Paymenter Integration ---
    PAYMENTER_BASE_URL: str | None = Field(
        default=None, description="Paymenter API base URL"
    )
    PAYMENTER_API_KEY: str | None = Field(
        default=None, description="Paymenter API key"
    )
    PAYMENTER_WEBHOOK_SECRET: str | None = Field(
        default=None, description="Paymenter webhook signing secret"
    )
    PAYMENTER_REQUEST_TIMEOUT: int = Field(
        default=30, ge=1, description="Paymenter HTTP timeout in seconds"
    )

    # --- PowerDNS / SmartDNS Integration ---
    PDNS_API_URL: str = Field(
        default="http://localhost:8081",
        description="PowerDNS Authoritative Server API base URL",
    )
    PDNS_API_KEY: str = Field(
        default="changeme",
        description="PowerDNS API key",
    )
    PDNS_SERVER_ID: str = Field(
        default="localhost",
        description="PowerDNS server ID",
    )
    PDNS_DEFAULT_ZONE_SUFFIX: str = Field(
        default="smartdns.bluehub.local",
        description="Default zone suffix for SmartDNS profiles",
    )
    PDNS_DEFAULT_NAMESERVERS: list[str] = Field(
        default=["ns1.bluehub.local.", "ns2.bluehub.local."],
        description="Default nameservers for created zones",
    )

    # --- Proxmox VE Integration ---
    PROXMOX_HOST: str | None = Field(
        default=None, description="Proxmox VE host"
    )
    PROXMOX_PORT: int = Field(
        default=8006, ge=1, le=65535, description="Proxmox VE API port"
    )
    PROXMOX_USER: str | None = Field(
        default=None, description="Proxmox VE API user"
    )
    PROXMOX_PASSWORD: str | None = Field(
        default=None, description="Proxmox VE API password"
    )
    PROXMOX_VERIFY_SSL: bool = Field(
        default=False, description="Verify Proxmox SSL certificate"
    )
    PROXMOX_NODE: str = Field(
        default="pve", description="Default Proxmox node"
    )
    PROXMOX_STORAGE: str = Field(
        default="local-lvm", description="Default Proxmox storage"
    )
    PROXMOX_BRIDGE: str = Field(
        default="vmbr0", description="Default Proxmox network bridge"
    )

    # --- MaxMind GeoIP ---
    MAXMIND_LICENSE_KEY: str | None = Field(
        default=None, description="MaxMind license key for GeoIP"
    )
    MAXMIND_DB_PATH: str = Field(
        default="./data/geolite2.mmdb",
        description="Path to MaxMind GeoIP database file",
    )
    MAXMIND_AUTO_UPDATE: bool = Field(
        default=True, description="Auto-update GeoIP database"
    )

    # --- Prometheus / Monitoring ---
    PROMETHEUS_ENABLED: bool = Field(
        default=True, description="Enable Prometheus metrics endpoint"
    )
    PROMETHEUS_PORT: int = Field(
        default=9090, ge=1, le=65535, description="Prometheus metrics port"
    )
    PROMETHEUS_NAMESPACE: str = Field(
        default="bluehub", description="Prometheus metric namespace"
    )

    # --- Rate Limiting ---
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting"
    )
    RATE_LIMIT_DEFAULT: str = Field(
        default="100/minute", description="Default rate limit"
    )
    RATE_LIMIT_GLOBAL: str = Field(
        default="1000/minute", description="Global rate limit"
    )

    # --- Circuit Breaker ---
    CIRCUIT_BREAKER_FAIL_MAX: int = Field(
        default=5,
        ge=1,
        description="Max failures before circuit opens",
    )
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = Field(
        default=60,
        ge=1,
        description="Seconds before circuit reset attempt",
    )

    # --- i18n ---
    DEFAULT_LOCALE: str = Field(
        default="en", description="Default locale"
    )
    SUPPORTED_LOCALES: list[str] = Field(
        default=["en", "fa", "ar", "tr", "ru", "de", "fr", "es"],
        description="Supported locales",
    )
    LOCALES_PATH: str = Field(
        default="./config/locales",
        description="Path to translation files",
    )

    # --- Telegram Bot ---
    TELEGRAM_BOT_TOKEN: str | None = Field(
        default=None, description="Telegram Bot API token"
    )
    TELEGRAM_WEBHOOK_URL: str | None = Field(
        default=None, description="Telegram webhook URL"
    )
    TELEGRAM_WEBHOOK_SECRET: str | None = Field(
        default=None, description="Telegram webhook secret token"
    )
    TELEGRAM_DROP_PENDING_UPDATES: bool = Field(
        default=True, description="Drop pending updates on start"
    )
    TELEGRAM_ADMIN_IDS: list[int] = Field(
        default_factory=list, description="Admin user IDs"
    )
    TELEGRAM_MAX_MESSAGE_LENGTH: int = Field(
        default=4096,
        ge=1,
        description="Max Telegram message length",
    )

    # --- Module Feature Flags ---
    MODULE_VPN_ENABLED: bool = Field(default=True, description="Enable VPN module")
    MODULE_VPN_STOP_NEW_SALES: bool = Field(
        default=False, description="Stop new VPN sales flag"
    )
    MODULE_VPN_TERMINATE_SERVICES: bool = Field(
        default=False, description="Terminate VPN services flag"
    )

    MODULE_VPS_ENABLED: bool = Field(default=True, description="Enable VPS module")
    MODULE_VPS_STOP_NEW_SALES: bool = Field(
        default=False, description="Stop new VPS sales flag"
    )
    MODULE_VPS_TERMINATE_SERVICES: bool = Field(
        default=False, description="Terminate VPS services flag"
    )

    MODULE_SMARTDNS_ENABLED: bool = Field(
        default=True, description="Enable SmartDNS module"
    )
    MODULE_SMARTDNS_STOP_NEW_SALES: bool = Field(
        default=False, description="Stop new SmartDNS sales flag"
    )
    MODULE_SMARTDNS_TERMINATE_SERVICES: bool = Field(
        default=False, description="Terminate SmartDNS services flag"
    )

    MODULE_STREAMING_ENABLED: bool = Field(
        default=True, description="Enable Streaming module"
    )
    MODULE_STREAMING_STOP_NEW_SALES: bool = Field(
        default=False, description="Stop new Streaming sales flag"
    )
    MODULE_STREAMING_TERMINATE_SERVICES: bool = Field(
        default=False, description="Terminate Streaming services flag"
    )

    MODULE_GAME_ENABLED: bool = Field(default=True, description="Enable Game module")
    MODULE_GAME_STOP_NEW_SALES: bool = Field(
        default=False, description="Stop new Game sales flag"
    )
    MODULE_GAME_TERMINATE_SERVICES: bool = Field(
        default=False, description="Terminate Game services flag"
    )

    # --- Webhook Settings ---
    WEBHOOK_MAX_RETRIES: int = Field(
        default=3, ge=0, description="Max webhook delivery retries"
    )
    WEBHOOK_RETRY_DELAY: int = Field(
        default=5, ge=1, description="Webhook retry delay in seconds"
    )
    WEBHOOK_SIGNATURE_HEADER: str = Field(
        default="X-Webhook-Signature",
        description="Webhook signature HTTP header name",
    )
    WEBHOOK_SIGNATURE_ALGORITHM: str = Field(
        default="HMAC-SHA256",
        description="Webhook signature algorithm",
    )

    # --- Backup ---
    BACKUP_ENABLED: bool = Field(
        default=True, description="Enable automated backups"
    )
    BACKUP_SCHEDULE: str = Field(
        default="0 3 * * *",
        description="Backup cron schedule (daily at 3 AM)",
    )
    BACKUP_RETENTION_DAYS: int = Field(
        default=30, ge=1, description="Backup retention in days"
    )
    BACKUP_S3_BUCKET: str | None = Field(
        default=None, description="S3 bucket for backup sync"
    )
    BACKUP_S3_PREFIX: str = Field(
        default="backups/", description="S3 backup key prefix"
    )

    # --- Derived Properties ---
    @property
    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == AppEnv.DEV

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.APP_ENV == AppEnv.TEST

    @property
    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == AppEnv.PROD

    @property
    def log_level_int(self) -> int:
        """Get numeric log level for Python logging."""
        import logging

        return getattr(logging, self.LOG_LEVEL.value, logging.INFO)

    @property
    def storage_path(self) -> Path:
        """Get resolved storage directory path."""
        path = Path(self.STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    @property
    def db_connection_string(self) -> str:
        """Get database connection string without async driver prefix."""
        return str(self.DATABASE_URL).replace("+asyncpg", "")

    @property
    def db_url_sync(self) -> str:
        """Get sync database URL for Alembic migrations (psycopg2)."""
        return str(self.DATABASE_URL).replace("+asyncpg", "+psycopg2")

    @property
    def module_flags(self) -> dict[str, dict[str, bool]]:
        """Get all module feature flags as a nested dict."""
        return {
            "vpn": {
                "enabled": self.MODULE_VPN_ENABLED,
                "stop_new_sales": self.MODULE_VPN_STOP_NEW_SALES,
                "terminate_services": self.MODULE_VPN_TERMINATE_SERVICES,
            },
            "vps": {
                "enabled": self.MODULE_VPS_ENABLED,
                "stop_new_sales": self.MODULE_VPS_STOP_NEW_SALES,
                "terminate_services": self.MODULE_VPS_TERMINATE_SERVICES,
            },
            "smartdns": {
                "enabled": self.MODULE_SMARTDNS_ENABLED,
                "stop_new_sales": self.MODULE_SMARTDNS_STOP_NEW_SALES,
                "terminate_services": self.MODULE_SMARTDNS_TERMINATE_SERVICES,
            },
            "streaming": {
                "enabled": self.MODULE_STREAMING_ENABLED,
                "stop_new_sales": self.MODULE_STREAMING_STOP_NEW_SALES,
                "terminate_services": self.MODULE_STREAMING_TERMINATE_SERVICES,
            },
            "game": {
                "enabled": self.MODULE_GAME_ENABLED,
                "stop_new_sales": self.MODULE_GAME_STOP_NEW_SALES,
                "terminate_services": self.MODULE_GAME_TERMINATE_SERVICES,
            },
        }

    # --- Cached Singleton ---
    _instance: ClassVar[Settings | None] = None

    @classmethod
    def get_settings(cls, **kwargs) -> Settings:
        """Get or create the singleton settings instance."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reload(cls, **kwargs) -> Settings:
        """Force reload settings (useful for testing)."""
        cls._instance = cls(**kwargs)
        return cls._instance


# Module-level convenience accessor
settings = Settings.get_settings()

__all__ = [
    "AppEnv",
    "AuthAlgorithm",
    "LogLevel",
    "Settings",
    "settings",
]
