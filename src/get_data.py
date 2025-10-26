"""
Main entry point for webhook processing.

This module provides the main function to process webhook data from Notion.
The heavy lifting is now done by dedicated service classes.
"""

from models import WebhookRequest
from models.generation import GenerationMetadata
from services.webhook_processor import WebhookProcessor
from utils.logging_config import setup_logging, get_logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv("environments/.env")

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


# Legacy functions have been moved to dedicated service classes:
# - get_notion_page -> NotionService.get_page
# - get_database_title -> NotionService.get_database_title
# - get_plots_data -> PlotDataExtractor.extract_plots_data
#
# This keeps the code organized and makes it easier to maintain and test.
