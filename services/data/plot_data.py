from typing import Any, Dict, List

from services.notion.notion_service import NotionService
from utils.logging import get_logger
from utils.notion import NotionUtils


logger = get_logger(__name__)


class PlotDataExtractor:
    """Extrai dados de talhões (plots) das propriedades e blocos de uma página do Notion."""

    def __init__(self):
        self.notion_service = NotionService()
        self.notion_utils = NotionUtils()
        logger.info("[INIT] PlotDataExtractor initialized")

    async def extract_plots_data(self, page_id: str) -> list[dict]:
        """Extrai dados de talhões de uma página, incluindo imagens."""
        logger.info(f"[EXTRACT] Starting plot extraction | page_id={page_id[:8]}")

        try:
            page = await self.notion_service.async_get_page(page_id)
            blocks = await self.notion_service.async_get_page_blocks(page_id)

            properties = page.get("properties", {})
            logger.debug(
                f"[EXTRACT] Page loaded | properties={len(properties)} | blocks={len(blocks)}"
            )

            # Extract plot data from properties
            plots = self._extract_plots_from_properties_flexible(properties)
            logger.info(
                f"[EXTRACT] Plots extracted from properties | count={len(plots)}"
            )

            # Extract images from property files
            plots = self._extract_images_from_properties(plots, properties)
            logger.debug("[EXTRACT] Images extracted from properties")

            # Associate images from blocks (fallback)
            plots_with_images = self._associate_images_with_plots(plots, blocks)
            logger.info(
                f"[EXTRACT] Plot extraction completed | total_plots={len(plots_with_images)}"
            )

            return plots_with_images
        except Exception as e:
            logger.error(
                f"[EXTRACT] Failed to extract plots | page_id={page_id[:8]}",
                extra={"error": e},
                exc_info=True,
            )
            raise

    def _extract_images_from_properties(
        self, plots: list[dict], properties: dict
    ) -> list[dict]:
        """Extrai imagens das propriedades 'Upload de Fotos - XX'."""
        logger.debug(
            f"[IMAGES-PROPS] Extracting images from properties | properties_count={len(properties)}"
        )

        for plot in plots:
            plot_index = plot["index"]

            upload_key = self._find_related_property(
                properties,
                plot_index,
                "upload de fotos",
                ["Upload de Fotos", "Upload Fotos", "Fotos"],
            )

            if upload_key:
                files_data = properties[upload_key].get("files", [])
                logger.debug(
                    f"[IMAGES-PROPS] Plot {plot_index:02d} | images_found={len(files_data)}"
                )

                for file_item in files_data:
                    if file_item.get("type") == "file":
                        file_url = file_item.get("file", {}).get("url")
                        if file_url:
                            plot["images"].append(
                                {"url": file_url, "name": file_item.get("name", "")}
                            )

        logger.debug("[IMAGES-PROPS] Property images extraction completed")
        return plots

    def _extract_plots_from_properties_flexible(self, properties: dict) -> list[dict]:
        """Extrai dados de talhões usando busca flexível de propriedades."""
        logger.debug("[EXTRACT-PROPS] Starting flexible property extraction")

        plots = []

        talhao_map = self.notion_utils.find_all_talhao_properties(
            properties, "talhao visitado"
        )

        logger.debug(
            f"[EXTRACT-PROPS] Talhão properties found | count={len(talhao_map)}"
        )

        for index in sorted(talhao_map.keys()):
            talhao_key = talhao_map[index]

            estagio_key = self._find_related_property(
                properties,
                index,
                "estadio fenologico",
                ["Estádio Fenológico", "Estadio Fenologico", "Estagio Fenologico"],
            )

            avaliacao_key = self._find_related_property(
                properties, index, "avaliacao", ["Avaliação", "Avaliacao"]
            )

            talhao_data = properties[talhao_key].get("multi_select", [])

            if not talhao_data:
                logger.debug(f"[EXTRACT-PROPS] Talhão {index:02d} | no data")
                continue

            growth_stage = []
            if estagio_key:
                estagio_data = properties[estagio_key].get("multi_select", [])
                if not estagio_data:
                    estagio_rich = properties[estagio_key].get("rich_text", [])
                    growth_stage = [
                        item.get("plain_text", "")
                        for item in estagio_rich
                        if item.get("plain_text")
                    ]
                else:
                    growth_stage = [
                        item["name"] for item in estagio_data if item.get("name")
                    ]

            assessment = ""
            if avaliacao_key:
                avaliacao_data = properties[avaliacao_key].get("rich_text", [])
                assessment = "".join(
                    item.get("plain_text", "") for item in avaliacao_data
                )

            talhao_names = [item["name"] for item in talhao_data if item.get("name")]

            logger.debug(
                f"[EXTRACT-PROPS] Talhão {index:02d} | plots={len(talhao_names)} | "
                f"growth_stage={len(growth_stage)} | assessment={len(assessment)}"
            )

            plot_data = {
                "index": index,
                "name": talhao_names,
                "growth_stage": growth_stage,
                "assessment": assessment,
                "images": [],  # To be filled by property/block extraction
            }

            plots.append(plot_data)

        logger.debug(f"[EXTRACT-PROPS] Total plots extracted | count={len(plots)}")
        return plots

    def _find_related_property(
        self,
        properties: Dict[str, Any],
        index: int,
        base_pattern: str,
        name_variants: List[str],
    ) -> str | None:
        """Busca uma propriedade relacionada a um talhão específico."""
        # Gerar todas as variações possíveis de busca
        search_patterns = []

        for variant in name_variants:
            # Com zero à esquerda
            search_patterns.append(f"{variant} - {index:02d}")
            # Sem zero à esquerda
            search_patterns.append(f"{variant} - {index}")
            # Com possíveis sufixos comuns
            search_patterns.append(f"{variant} - {index:02d} (1)")
            search_patterns.append(f"{variant} - {index:02d}_ok")
            search_patterns.append(f"{variant} - {index} (1)")

        # Buscar usando o método flexível
        found_key = self.notion_utils.find_property_key_flexible(
            properties, *search_patterns
        )

        if found_key:
            logger.debug(
                f"[EXTRACT-PROPS] Property found for {base_pattern} - {index:02d}"
            )
        else:
            logger.debug(
                f"[EXTRACT-PROPS] Property NOT found for {base_pattern} - {index:02d}"
            )

        return found_key

    def _associate_images_with_plots(
        self, plots: list[dict], blocks: list[dict]
    ) -> list[dict]:
        """Associa imagens dos blocos aos talhões (usado como fallback se não houver imagens nas properties)."""
        # Collect all images from blocks
        all_images = self._extract_images_from_blocks(blocks)
        logger.debug(
            f"[IMAGES-BLOCKS] Total images in blocks | count={len(all_images)}"
        )

        # Associate images with plots based on heading context (only if no images yet)
        associated_count = 0
        for plot in plots:
            if not plot[
                "images"
            ]:  # Só busca em blocos se não tiver imagens de properties
                plot_index = plot["index"]
                block_images = self._find_images_for_plot(
                    plot_index, all_images, blocks
                )
                plot["images"].extend(block_images)
                associated_count += len(block_images)
                logger.debug(
                    f"[IMAGES-BLOCKS] Plot {plot_index:02d} | associated={len(block_images)}"
                )

        logger.debug(
            f"[IMAGES-BLOCKS] Total associations completed | count={associated_count}"
        )
        return plots

    def _extract_images_from_blocks(self, blocks: list[dict]) -> list[dict]:
        """Extrai todas as imagens dos blocos."""
        images = []
        logger.debug("[IMAGES-BLOCKS] Starting image extraction from blocks")

        for block in blocks:
            block_type = block.get("type")
            if block_type == "image":
                image_data = block.get("image", {})
                image_url = None

                if image_data.get("type") == "file":
                    image_url = image_data.get("file", {}).get("url")
                elif image_data.get("type") == "external":
                    image_url = image_data.get("external", {}).get("url")

                if image_url:
                    caption = ""
                    caption_data = image_data.get("caption", [])
                    if caption_data:
                        caption = self.notion_utils.extract_text(caption_data)

                    images.append(
                        {
                            "block_id": block.get("id"),
                            "url": image_url,
                            "caption": caption,
                        }
                    )
                    logger.debug(
                        f"[IMAGES-BLOCKS] Image found | block_id={block.get('id')[:8]} | has_caption={bool(caption)}"
                    )

        logger.debug(f"[IMAGES-BLOCKS] Extraction complete | total={len(images)}")
        return images

    def _find_images_for_plot(
        self, plot_index: int, all_images: list[dict], blocks: list[dict]
    ) -> list[str]:
        """
        Encontra imagens associadas a um talhão específico baseado em headings.
        """
        plot_images = []
        current_plot_index = None

        for block in blocks:
            block_type = block.get("type")

            # Check if it's a heading that defines a talhão section
            if block_type in ["heading_1", "heading_2", "heading_3"]:
                heading_text = self.notion_utils.extract_text(
                    block.get(block_type, {}).get("rich_text", [])
                )

                # Extract plot index from heading (flexible)
                match = self.notion_utils.extract_talhao_index_from_property(
                    heading_text
                )
                if match:
                    current_plot_index = match
                    logger.debug(
                        f"Found heading for plot {current_plot_index}: '{heading_text}'"
                    )

            # If we're in the right plot section and find an image, add it
            elif block_type == "image" and current_plot_index == plot_index:
                for img in all_images:
                    if img["block_id"] == block.get("id"):
                        plot_images.append(img["url"])
                        break

        return plot_images
