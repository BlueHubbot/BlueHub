"""
BlueHub Logging Module
======================
Structured logging with standard library logging module.
Supports JSON and console formats, file logging, and request correlation.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings


class StructuredFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value
        log_entry["app"] = settings.APP_NAME
        log_entry["env"] = settings.APP_ENV.value
        log_entry["version"] = settings.APP_VERSION
        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Colorful console formatter for development."""
    FORMATS = {
        logging.DEBUG: "\033[36m[%(levelname)s]\033[0m %(message)s",
        logging.INFO: "\033[32m[%(levelname)s]\033[0m %(message)s",
        logging.WARNING: "\033[33m[%(levelname)s]\033[0m %(message)s",
        logging.ERROR: "\033[31m[%(levelname)s]\033[0m %(message)s",
        logging.CRITICAL: "\033[41m[%(levelname)s]\033[0m %(message)s",
    }

    def format(self, record: logging.LogRecord) -> str:
        fmt = self.FORMATS.get(record.levelno, "[%(levelname)s] %(message)s")
        return logging.Formatter(fmt, datefmt="%H:%M:%S").format(record)


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
    log_file: str | None = None,
) -> None:
    """Configure logging with appropriate formatters and handlers."""
    level = log_level or settings.LOG_LEVEL.value
    fmt = log_format or settings.LOG_FORMAT
    file_path = log_file or settings.LOG_FILE

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    formatter: logging.Formatter = StructuredFormatter() if fmt == "json" else ConsoleFormatter()

    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(str(log_path))
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    for noisy_logger in ["uvicorn.access", "httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name or __name__)


logger = get_logger(__name__)

__all__ = ["ConsoleFormatter", "StructuredFormatter", "get_logger", "logger", "setup_logging"]
