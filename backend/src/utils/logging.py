"""
Logging configuration module.
"""

import logging
import os
from pathlib import Path

from core.config import settings


def setup_logging():
    """Set up logging configuration for the application.

    Works in both local and serverless (Vercel) environments.
    In serverless, only uses StreamHandler since filesystem is read-only.
    """
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Prepare handlers
    handlers = [logging.StreamHandler()]  # Always log to console/stdout

    # Only add file handler if not in serverless environment
    # Vercel and other serverless platforms have read-only filesystems
    is_serverless = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")

    if not is_serverless:
        try:
            # Try to create logs directory for local development
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(logs_dir / "notion_webhook.log")
            handlers.append(file_handler)
        except (OSError, PermissionError):
            # If we can't create the directory, just use console logging
            pass

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Set specific loggers to WARNING to reduce noise
    logging.getLogger("notion_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log configuration info
    logger = get_logger(__name__)
    logger.info(f"Logging configured with level: {settings.log_level}")
    logger.info(f"Environment: {'Serverless' if is_serverless else 'Local'}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
