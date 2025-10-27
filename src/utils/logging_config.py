"""
Logging configuration module.
"""

import logging
from pathlib import Path
from core.config import settings


def setup_logging():
    """Set up logging configuration for the application."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "notion_webhook.log"),
            logging.StreamHandler(),  # Also log to console
        ],
        force=True,  # Override any existing configuration
    )

    # Set specific loggers to WARNING to reduce noise
    logging.getLogger("notion_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log configuration info
    logger = get_logger(__name__)
    logger.info(f"Logging configured with level: {settings.log_level}")
    logger.info(f"HTML audit enabled: {settings.enable_html_audit}")
    logger.info(f"HTML audit max chars: {settings.html_audit_max_chars}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
