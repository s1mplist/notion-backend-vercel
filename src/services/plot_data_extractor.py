"""
Service for extracting and processing plot data from Notion pages.
"""

import logging
from typing import Dict, List
from services.notion.notion_service import NotionService
from utils.notion_utils import normalize_prop_name

logger = logging.getLogger(__name__)


class PlotDataExtractor:
    """Service for extracting plot data from Notion pages."""

    def __init__(self):
        self.notion_service = NotionService()

    async def extract_plots_data(self, report_id: str) -> List[Dict]:
        """
        Extract plots data from Notion page properties.

        Args:
            report_id: ID of the main report page

        Returns:
            List of plot data dictionaries
        """
        try:
            logger.info(f"Retrieving plots for report ID: {report_id}")

            # Get page properties
            page = self.notion_service.get_page(report_id)
            properties = page["properties"]

            # Extract plot information from properties
            plots = self._extract_plots_from_properties(properties)

            logger.info(f"Plots data retrieved successfully for report ID: {report_id}")
            logger.debug(f"Plots data: {plots}")

            # If images are missing, try to find them in page blocks
            missing_images = any(len(p.get("images", [])) == 0 for p in plots)
            if missing_images:
                plots = await self._enhance_plots_with_block_images(report_id, plots)

            return plots

        except Exception as e:
            logger.error(f"Error getting plots data for report {report_id}: {str(e)}")
            raise

    def _extract_plots_from_properties(self, properties: Dict) -> List[Dict]:
        """Extract plot data from page properties."""
        plots = []

        # Extract plot information from each talhao property
        for i in range(1, 19):  # Loop through all possible talhao entries (1-18)
            talhao_key = f"Talhão Visitado - {i:02d}"
            estagio_key = f"Estádio Fenológico - {i:02d}"
            avaliacao_key = f"Avaliação - {i:02d}"

            if talhao_key in properties:
                talhao_data = properties[talhao_key].get("multi_select", [])
                if talhao_data:  # If there's data for this talhao
                    # Find the photos property
                    found_key = self._find_photos_property_key(properties, i)
                    fotos_prop = properties.get(found_key) if found_key else {}

                    logger.debug(
                        f"Fotos property for {talhao_key} (found key: {found_key}) -> {fotos_prop}"
                    )

                    # Extract images
                    images = self._extract_images_from_property(fotos_prop)

                    # Build plot data
                    plot_data = {
                        "id": f"talhao_{i}",
                        "name": [t.get("name", "") for t in talhao_data],
                        "growth_stage": self._extract_rich_text_content(
                            properties.get(estagio_key, {})
                        ),
                        "assessment": self._extract_rich_text_content(
                            properties.get(avaliacao_key, {})
                        ),
                        "images": images,
                    }
                    plots.append(plot_data)

        return plots

    def _find_photos_property_key(self, properties: Dict, talhao_number: int) -> str:
        """Find the photos property key for a given talhao number."""
        # Try to find the fotos property in a case-insensitive way and support variations

        target1_norm = normalize_prop_name(f"Upload de fotos - {talhao_number:02d}")
        target2_norm = normalize_prop_name(f"Upload de fotos - {talhao_number}")

        for k in properties.keys():
            kn = normalize_prop_name(k)
            if kn == target1_norm or kn == target2_norm:
                return k

        # Also support keys that start with the prefix (handles small variations)
        for k in properties.keys():
            kn = normalize_prop_name(k)
            if kn.startswith(target1_norm) or kn.startswith(target2_norm):
                return k

        return None

    def _extract_images_from_property(self, fotos_prop: Dict) -> List[Dict]:
        """Extract image URLs and names from a files property."""
        images = []
        files_list = []

        if isinstance(fotos_prop, dict):
            files_list = fotos_prop.get("files") or []

        for file in files_list:
            url = None
            # Support both uploaded files and external links
            if file.get("type") == "file":
                url = file.get("file", {}).get("url")
            elif file.get("type") == "external":
                url = file.get("external", {}).get("url")
            # Some SDK payloads may include the url at top-level keys
            if not url:
                url = file.get("url") or file.get("file_url")

            if url:
                images.append({"url": url, "name": file.get("name", "")})

        return images

    def _extract_rich_text_content(self, property_data: Dict) -> List[str]:
        """Extract content from rich_text property."""
        return [
            text.get("text", {}).get("content", "")
            for text in property_data.get("rich_text", [])
        ]

    async def _enhance_plots_with_block_images(
        self, report_id: str, plots: List[Dict]
    ) -> List[Dict]:
        """Try to find images in page blocks as fallback."""
        logger.info(
            "Some plots have no images in properties — scanning page blocks for image blocks as fallback"
        )

        try:
            blocks = self.notion_service.get_page_blocks(report_id)

            # Helper to get plain text from rich_text lists
            def rt_text(items):
                if not items:
                    return ""
                return " ".join(it.get("text", {}).get("content", "") for it in items)

            # Map of plot name tokens to index for simple matching
            name_index_map = self._build_plot_name_index(plots)

            unmatched = []
            # Iterate blocks, try to match image blocks to plots
            for i, block in enumerate(blocks):
                if block.get("type") != "image":
                    continue

                image_info = self._extract_image_from_block(block, blocks, i, rt_text)
                if not image_info:
                    continue

                # Try to match to a plot
                matched = self._match_image_to_plot(image_info, name_index_map, plots)

                if not matched:
                    unmatched.append(image_info)

            # Assign unmatched images to plots that still have no images
            self._assign_unmatched_images(plots, unmatched)

            logger.debug(f"After block scan, plots data: {plots}")

        except Exception as e:
            logger.exception(f"Error scanning blocks for images: {e}")

        return plots

    def _build_plot_name_index(self, plots: List[Dict]) -> Dict[int, List[str]]:
        """Build an index of plot names for matching."""
        name_index_map = {}
        for idx, p in enumerate(plots):
            # Use all name tokens lowercased
            tokens = [t.lower() for t in (p.get("name") or []) if isinstance(t, str)]
            # Also include id like 'talhao_1' and 'pivô 1' token variants
            tokens.extend([p.get("id", "").lower()])
            name_index_map[idx] = tokens
        return name_index_map

    def _extract_image_from_block(
        self, block: Dict, blocks: List[Dict], block_index: int, rt_text
    ) -> Dict:
        """Extract image information from a block."""
        image_obj = block.get("image", {})

        # Extract URL
        url = None
        if image_obj.get("type") == "file":
            url = image_obj.get("file", {}).get("url")
        elif image_obj.get("type") == "external":
            url = image_obj.get("external", {}).get("url")
        if not url:
            url = image_obj.get("url") or image_obj.get("file_url")

        if not url:
            return None

        # Keep original URL without optimization

        # Extract caption
        caption = ""
        try:
            caption = rt_text(image_obj.get("caption", []))
        except Exception:
            caption = ""

        # Get nearby text context (up to 3 previous blocks)
        nearby_text = caption.lower() if isinstance(caption, str) else ""
        for j in range(max(0, block_index - 3), block_index):
            blk = blocks[j]
            t = ""
            if blk.get("type") in ("paragraph", "heading_1", "heading_2", "heading_3"):
                # Paragraphs and headings have text in 'rich_text' or 'text'
                rich = []
                # Different shapes possible
                if blk.get(blk.get("type")):
                    rich = blk.get(blk.get("type")).get("rich_text", [])
                if not rich and blk.get("paragraph"):
                    rich = blk.get("paragraph").get("rich_text", [])
                t = rt_text(rich).lower()
            nearby_text += " " + t

        return {"url": url, "caption": caption, "nearby_text": nearby_text}

    def _match_image_to_plot(
        self, image_info: Dict, name_index_map: Dict, plots: List[Dict]
    ) -> bool:
        """Try to match an image to a plot based on text context."""
        caption_l = image_info["caption"].lower()
        nearby_text = image_info["nearby_text"]

        # Try to match any plot by token presence
        for idx, tokens in name_index_map.items():
            for tok in tokens:
                if not tok:
                    continue
                if tok in nearby_text or tok in caption_l:
                    plots[idx].setdefault("images", []).append(
                        {"url": image_info["url"], "name": ""}
                    )
                    return True
        return False

    def _assign_unmatched_images(self, plots: List[Dict], unmatched: List[Dict]):
        """Assign unmatched images to plots that still have no images (left-to-right)."""
        uidx = 0
        for p in plots:
            if len(p.get("images", [])) == 0 and uidx < len(unmatched):
                p["images"] = [
                    {
                        "url": unmatched[uidx]["url"],
                        "name": unmatched[uidx].get("caption", ""),
                    }
                ]
                uidx += 1
