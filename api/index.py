"""
Vercel serverless function entry point.
This file is required for Vercel to properly route requests to our FastAPI application.
"""

import os
import sys
import logging

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

# Export the FastAPI app directly for Vercel
# Vercel's Python runtime supports ASGI applications natively
__all__ = ["app"]
