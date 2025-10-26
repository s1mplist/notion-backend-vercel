"""
Vercel serverless function entry point.
This file is required for Vercel to properly route requests to our FastAPI application.
"""

import os
import sys
import logging
from mangum import Mangum

# Configure logging for serverless environment
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from main import app

    logger.info("FastAPI app imported successfully")
except ImportError as e:
    logger.error(f"Failed to import FastAPI app: {e}")
    raise

# Create a handler for Vercel with optimized settings
handler = Mangum(
    app,
    lifespan="off",
    api_gateway_base_path=None,
    text_mime_types=[
        "application/json",
        "application/javascript",
        "application/xml",
        "application/vnd.api+json",
    ],
)


# Main handler function for Vercel
def handler_func(event, context):
    """
    Vercel serverless function handler.

    Args:
        event: The event data from Vercel
        context: The context object from Vercel

    Returns:
        Response from the FastAPI application
    """
    try:
        logger.info(
            f"Processing request: {event.get('httpMethod', 'UNKNOWN')} {event.get('path', '/')}"
        )
        return handler(event, context)
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": '{"error": "Internal server error"}',
            "headers": {"Content-Type": "application/json"},
        }


# Alternative direct handler for Vercel (default export)
def default_handler(event, context):
    """Direct handler function for Vercel."""
    return handler_func(event, context)


# Export handlers
__all__ = ["handler_func", "default_handler", "handler"]
