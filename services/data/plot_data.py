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
        logger.info("PlotDataExtractor initialized")

    async def extract_plots_data(self, page_id: str) -> list[dict]:
        """
        Extrai dados de talhões de uma página, incluindo imagens das propriedades e blocos.
        Usa busca flexível para lidar com variações nos nomes das propriedades.
        """
        logger.info(f"Extracting plots data from page {page_id}")

        # Get page properties and blocks
        page = await self.notion_service.async_get_page(page_id)
        blocks = await self.notion_service.async_get_page_blocks(page_id)

        properties = page.get("properties", {})

        # Extract plot data from properties (flexible matching)
        plots = self._extract_plots_from_properties_flexible(properties)
        logger.info(f"Extracted {len(plots)} plots from properties")

        # Extract images from property files first (preferred source)
        plots = self._extract_images_from_properties(plots, properties)

        # Then try to extract images from blocks (fallback)
        plots_with_images = self._associate_images_with_plots(plots, blocks)
        logger.info(
            f"Associated images with plots: {len(plots_with_images)} plots total"
        )

        return plots_with_images

    def _extract_images_from_properties(
        self, plots: list[dict], properties: dict
    ) -> list[dict]:
        """
        Extrai imagens das propriedades 'Upload de Fotos - XX'.
        Estas propriedades contêm arquivos diretamente associados a cada talhão.
        Retorna imagens no formato: {"url": str, "name": str}
        """
        for plot in plots:
            plot_index = plot["index"]

            # Buscar propriedade de upload de fotos para este talhão
            upload_key = self._find_related_property(
                properties,
                plot_index,
                "upload de fotos",
                ["Upload de Fotos", "Upload Fotos", "Fotos"],
            )

            if upload_key:
                files_data = properties[upload_key].get("files", [])

                # Extrair URLs dos arquivos no formato esperado
                for file_item in files_data:
                    if file_item.get("type") == "file":
                        file_url = file_item.get("file", {}).get("url")
                        if file_url:
                            # Formato compatível com merge_plot_data
                            plot["images"].append(
                                {"url": file_url, "name": file_item.get("name", "")}
                            )
                            logger.debug(
                                f"Plot {plot_index:02d}: added image from property '{upload_key}'"
                            )

                logger.debug(
                    f"Plot {plot_index:02d}: found {len(files_data)} images in properties"
                )

        return plots

    def _extract_plots_from_properties_flexible(self, properties: dict) -> list[dict]:
        """
        Extrai dados de talhões usando busca flexível de propriedades.
        Lida com variações como espaços extras, sufixos (1), _ok, etc.
        """
        plots = []

        # Encontrar todas as propriedades de talhão
        talhao_map = self.notion_utils.find_all_talhao_properties(
            properties, "talhao visitado"
        )

        logger.debug(
            f"Found {len(talhao_map)} talhão properties: {list(talhao_map.keys())}"
        )

        # Processar cada talhão encontrado
        for index in sorted(talhao_map.keys()):
            talhao_key = talhao_map[index]

            # Buscar propriedades relacionadas com variações
            estagio_key = self._find_related_property(
                properties,
                index,
                "estadio fenologico",
                ["Estádio Fenológico", "Estadio Fenologico", "Estagio Fenologico"],
            )

            avaliacao_key = self._find_related_property(
                properties, index, "avaliacao", ["Avaliação", "Avaliacao"]
            )

            # Extrair dados do talhão
            talhao_data = properties[talhao_key].get("multi_select", [])

            if not talhao_data:
                logger.debug(f"Talhão {index:02d}: no data in multi_select")
                continue

            # Extrair estádio fenológico
            growth_stage = []
            if estagio_key:
                estagio_data = properties[estagio_key].get("multi_select", [])
                if not estagio_data:
                    # Tentar rich_text como fallback
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
            else:
                logger.debug(f"Talhão {index:02d}: Estádio property not found")

            # Extrair avaliação
            assessment = []
            if avaliacao_key:
                avaliacao_data = properties[avaliacao_key].get("rich_text", [])
                assessment = [item.get("plain_text", "") for item in avaliacao_data]
            else:
                logger.debug(f"Talhão {index:02d}: Avaliação property not found")

            # Extrair nomes dos talhões
            talhao_names = [item["name"] for item in talhao_data if item.get("name")]

            logger.debug(
                f"Talhão {index:02d}: found {len(talhao_names)} names, "
                f"growth_stage={growth_stage}, assessment={'Yes' if assessment else 'No'}"
            )

            plot_data = {
                "index": index,
                "name": talhao_names,
                "growth_stage": growth_stage,
                "assessment": assessment,
                "images": [],  # To be filled by property/block extraction
            }

            plots.append(plot_data)

        return plots

    def _find_related_property(
        self,
        properties: Dict[str, Any],
        index: int,
        base_pattern: str,
        name_variants: List[str],
    ) -> str | None:
        """
        Busca uma propriedade relacionada a um talhão específico.

        Args:
            properties: Dicionário de propriedades
            index: Índice do talhão (1-18)
            base_pattern: Padrão base normalizado (ex: "estadio fenologico")
            name_variants: Variações do nome (ex: ["Estádio Fenológico", "Estadio Fenologico"])

        Returns:
            Chave da propriedade encontrada ou None
        """
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
            logger.debug(f"Found related property for index {index}: {found_key}")

        return found_key

    def _associate_images_with_plots(
        self, plots: list[dict], blocks: list[dict]
    ) -> list[dict]:
        """
        Associa imagens dos blocos aos talhões (usado como fallback se não houver imagens nas properties).
        """
        # Collect all images from blocks
        all_images = self._extract_images_from_blocks(blocks)
        logger.debug(f"Found {len(all_images)} images in blocks")

        # Associate images with plots based on heading context (only if no images yet)
        for plot in plots:
            if not plot[
                "images"
            ]:  # Só busca em blocos se não tiver imagens de properties
                plot_index = plot["index"]
                block_images = self._find_images_for_plot(
                    plot_index, all_images, blocks
                )
                plot["images"].extend(block_images)
                logger.debug(
                    f"Plot {plot_index:02d}: added {len(block_images)} images from blocks"
                )

        return plots

    def _extract_images_from_blocks(self, blocks: list[dict]) -> list[dict]:
        """Extrai todas as imagens dos blocos."""
        images = []
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
