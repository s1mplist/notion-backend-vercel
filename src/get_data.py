"""
Main entry point for webhook processing.

This module provides the main function to process webhook data from Notion.
The heavy lifting is now done by dedicated service classes.
"""

from models import WebhookRequest
from models.generation import GenerationMetadata
from services.webhook_processor import WebhookProcessor
from utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def process_webhook_data(
    gen_meta: GenerationMetadata, webhook_data: WebhookRequest
) -> dict:
    """
    Process webhook data from Notion and coordinate report generation.

    This function is now a thin wrapper around the WebhookProcessor service,
    which handles all the complex logic in a modular way.

    Args:
        gen_meta: Generation metadata
        webhook_data: Validated webhook data from Notion

    Returns:
        dict: Processing result with status information
    """
    processor = WebhookProcessor()
    return await processor.process_webhook_data(gen_meta, webhook_data)
