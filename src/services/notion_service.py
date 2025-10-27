"""
Notion API client service for data retrieval operations.
"""

import logging
from typing import Dict, List
from notion_client import AsyncClient
from ..core.config import settings

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API."""

    def __init__(self):
        self.token = settings.notion_token

    async def get_page(self, page_id: str) -> Dict:
        """
        Get page data from Notion API.

        Args:
            page_id: Notion page ID

        Returns:
            dict: Page data with properties
        """
        try:
            async with AsyncClient(auth=self.token) as notion:
                page = await notion.pages.retrieve(page_id=page_id)
                return page

        except Exception as e:
            logger.error(f"Error getting Notion page {page_id}: {str(e)}")
            raise

    async def get_database_title(self, database_id: str) -> str:
        """
        Retrieve the Notion database title (plain text) given its ID.

        The Notion API returns the database title as a list of rich_text objects in the
        top-level "title" field. We join their plain_text to form the final title.
        """
        try:
            async with AsyncClient(auth=self.token) as notion:
                db = await notion.databases.retrieve(database_id=database_id)
                parts = db.get("title", []) or []
                title = "".join(
                    (p.get("plain_text") or p.get("text", {}).get("content", ""))
                    for p in parts
                ).strip()
                return title
        except Exception as e:
            logger.error(f"Error getting Notion database {database_id}: {str(e)}")
            raise

    async def get_page_blocks(self, page_id: str) -> List[Dict]:
        """
        Get all blocks from a Notion page with pagination.

        Args:
            page_id: Notion page ID

        Returns:
            List of block objects
        """
        try:
            async with AsyncClient(auth=self.token) as notion:
                blocks = []
                next_cursor = None

                while True:
                    resp = await notion.blocks.children.list(
                        block_id=page_id, start_cursor=next_cursor
                    )
                    blocks.extend(resp.get("results", []))
                    if not resp.get("has_more"):
                        break
                    next_cursor = resp.get("next_cursor")

                return blocks
        except Exception as e:
            logger.error(f"Error getting blocks for page {page_id}: {str(e)}")
            raise
