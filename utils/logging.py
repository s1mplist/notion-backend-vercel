"""Logging configuration with structured tracing and request context."""

import logging
import os
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

from api.config import get_settings


settings = get_settings()

# Context variable for request traceability
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Add request_id to all log records."""

    def filter(self, record):
        record.request_id = request_id_var.get() or "no-request"
        return True


def setup_logging():
    """Set up logging configuration for the application.

    Works in both local and serverless (Vercel) environments.
    In serverless, only uses StreamHandler since filesystem is read-only.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    is_serverless = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")

    if not is_serverless:
        try:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
        except (OSError, PermissionError):
            pass

    # Formato simples e estruturado SEM request_id
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Add RequestIdFilter to root logger so it applies to ALL loggers
    root_logger = logging.getLogger()
    root_logger.addFilter(RequestIdFilter())

    logger = get_logger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level} | environment={'Serverless' if is_serverless else 'Local'}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Note: RequestIdFilter is already added to root logger in setup_logging(),
    so all loggers automatically inherit it.
    """
    return logging.getLogger(name)


@contextmanager
def log_context(request_id: Optional[str] = None):
    """Context manager for setting request ID for all logs within a scope."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]

    token = request_id_var.set(request_id)
    try:
        yield request_id
    finally:
        request_id_var.reset(token)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs):
    """Log the start of an operation."""
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"[START] {operation} {context if context else ''}")


def log_operation_end(logger: logging.Logger, operation: str, **kwargs):
    """Log the successful end of an operation."""
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"[END] {operation} {context if context else ''}")


def log_operation_error(
    logger: logging.Logger, operation: str, error: Exception, **kwargs
):
    """Log operation error with context."""
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(
        f"[ERROR] {operation} {context if context else ''}",
        exc_info=True,
        extra={"error_type": type(error).__name__},
    )


def log_debug_data(logger: logging.Logger, data: Any, label: str = "Data"):
    """Log debug data (only if DEBUG level is enabled)."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"{label}: {data}")
