"""
Logging configuration for Vercel deployment.
This module provides structured logging that works well with Vercel's logging system.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict


class VercelJSONFormatter(logging.Formatter):
    """Custom JSON formatter for Vercel logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


def setup_vercel_logging(level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration optimized for Vercel.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler for stdout (Vercel requirement)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Use JSON formatter for structured logs
    json_formatter = VercelJSONFormatter()
    console_handler.setFormatter(json_formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger


def log_request(
    logger: logging.Logger,
    method: str,
    url: str,
    headers: Dict[str, Any],
    body_size: int = 0,
) -> None:
    """Log incoming request in structured format."""
    logger.info(
        "Incoming request",
        extra={
            "request_method": method,
            "request_url": str(url),
            "request_body_size": body_size,
            "request_headers": dict(headers),
            "event_type": "request_start",
        },
    )


def log_response(
    logger: logging.Logger, status_code: int, response_time_ms: float
) -> None:
    """Log response in structured format."""
    logger.info(
        "Request completed",
        extra={
            "response_status": status_code,
            "response_time_ms": response_time_ms,
            "event_type": "request_end",
        },
    )


def log_webhook(
    logger: logging.Logger,
    payload_size: int,
    content_type: str,
    user_agent: str,
    payload_keys: list = None,
) -> None:
    """Log webhook-specific information."""
    logger.info(
        "Webhook received",
        extra={
            "webhook_payload_size": payload_size,
            "webhook_content_type": content_type,
            "webhook_user_agent": user_agent,
            "webhook_payload_keys": payload_keys or [],
            "event_type": "webhook_received",
        },
    )
