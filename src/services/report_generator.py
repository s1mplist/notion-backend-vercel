"""
Service for generating complete reports by combining Notion data sources.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from models.report import Report, Plot, Image
from utils.notion_utils import extract_text
from services.notion.notion_service import NotionService
from services.plot_data_extractor import PlotDataExtractor
from services.notion.mapper import NotionDataMapper
from services.html_renderer import HTMLRenderer

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Service for generating complete reports with enhanced metadata."""

    def __init__(self):
        self.notion_service = NotionService()
        self.plot_extractor = PlotDataExtractor()
        self.data_mapper = NotionDataMapper()
        self.html_renderer = HTMLRenderer()

    async def generate_complete_report(self, page_id: str) -> Dict[str, Any]:
        """
        Generate a complete report combining FACT data and plot information.

        Args:
            page_id: The Notion page ID (FACT entry)

        Returns:
            Dict containing HTML content and metadata
        """
        try:
            logger.info(f"Generating complete report for page_id: {page_id}")

            # 1. Get FACT and Talhões data sources
            fact_ds_id, talhoes_ds_id = await self._get_data_sources()

            # 2. Query FACT data source by page_id
            fact_data = await self._query_fact_data(fact_ds_id, page_id)

            if not fact_data:
                raise ValueError(f"FACT page {page_id} not found")

            fact_item = fact_data[0]

            # 3. Get farm IDs from FACT
            farm_ids = self._extract_farm_ids(fact_item)

            # 4. Query Talhões data for all farms
            talhoes_data = await self._query_talhoes_data(talhoes_ds_id, farm_ids)

            # 5. Resolve farm name
            farm_name = await self._resolve_farm_name(farm_ids)

            # 6. Get original page data (for plots with images)
            page_data = self.notion_service.get_page(page_id)
            plots_with_images = await self.plot_extractor.extract_plots_data(page_id)

            # 7. Merge data: combine talhões metadata with plots images
            enriched_plots = self._merge_plot_data(talhoes_data, plots_with_images)

            # 8. Build complete Report model
            report_data = self._build_report_model(
                fact_item=fact_item,
                page_data=page_data,
                plots=enriched_plots,
                farm_name=farm_name,
                talhoes_data=talhoes_data,
            )

            # 9. Generate HTML
            html_content = await self.html_renderer.render_report_html(report_data)

            return {
                "status": "success",
                "page_id": page_id,
                "farm_name": farm_name,
                "plots_count": len(enriched_plots),
                "html_content": html_content,
                "metadata": {
                    "fact_item": fact_item,
                    "farm_ids": farm_ids,
                    "talhoes_count": len(talhoes_data),
                },
            }

        except Exception as e:
            logger.error(f"Error generating complete report: {e}", exc_info=True)
            raise

    async def generate_report_with_template(
        self, page_id: str, template_slug: str
    ) -> Dict[str, Any]:
        """
        Generate a complete report and render it using a specific template bundle under
        templates/relatorios/{template_slug}.

        Args:
            page_id: FACT page ID
            template_slug: e.g., "terras-gerais"

        Returns:
            Dict with html_content and metadata
        """
        try:
            logger.info(
                f"Generating report for page_id={page_id} with template={template_slug}"
            )

            # 1. Data sources
            fact_ds_id, talhoes_ds_id = await self._get_data_sources()

            # 2. FACT data
            fact_data = await self._query_fact_data(fact_ds_id, page_id)
            if not fact_data:
                raise ValueError(f"FACT page {page_id} not found")
            fact_item = fact_data[0]

            # 3. Farm IDs
            farm_ids = self._extract_farm_ids(fact_item)

            # 4. Talhões data
            talhoes_data = await self._query_talhoes_data(talhoes_ds_id, farm_ids)

            # 5. Farm name
            farm_name = await self._resolve_farm_name(farm_ids)

            # 6. Original page + plots/images
            page_data = self.notion_service.get_page(page_id)
            plots_with_images = await self.plot_extractor.extract_plots_data(page_id)

            # 7. Merge
            enriched_plots = self._merge_plot_data(talhoes_data, plots_with_images)

            # 8. Report model
            report_data = self._build_report_model(
                fact_item=fact_item,
                page_data=page_data,
                plots=enriched_plots,
                farm_name=farm_name,
                talhoes_data=talhoes_data,
            )

            # 9. Render with selected template
            html_content = await self.html_renderer.render_template_slug(
                template_slug, report_data
            )

            return {
                "status": "success",
                "page_id": page_id,
                "farm_name": farm_name,
                "plots_count": len(enriched_plots),
                "html_content": html_content,
                "metadata": {
                    "fact_item": fact_item,
                    "farm_ids": farm_ids,
                    "talhoes_count": len(talhoes_data),
                    "template": template_slug,
                },
            }
        except Exception as e:
            logger.error(f"Error generating report with template: {e}", exc_info=True)
            raise

    async def _get_data_sources(self) -> tuple[str, str]:
        """Get FACT and Talhões data source IDs."""
        # Get database IDs from environment or configuration
        fact_db_id = "29c4eaab90d28015a00fe7e0faaa5c22"
        talhoes_db_id = "29b4eaab90d280d594e9d765abf12e59"

        # Retrieve data source IDs
        from notion_client import AsyncClient
        from core.config import settings

        async with AsyncClient(auth=settings.notion_token) as notion:
            fact_db = await notion.databases.retrieve(database_id=fact_db_id)
            fact_ds_id = fact_db["data_sources"][0]["id"]

            talhoes_db = await notion.databases.retrieve(database_id=talhoes_db_id)
            talhoes_ds_id = talhoes_db["data_sources"][0]["id"]

        return fact_ds_id, talhoes_ds_id

    async def _query_fact_data(self, fact_ds_id: str, page_id: str) -> List[Dict]:
        """Query FACT data source for specific page."""
        from notion_client import AsyncClient
        from core.config import settings

        query = {
            "filter": {
                "property": "title",
                "rich_text": {"contains": page_id.replace("-", "")},
            }
        }

        async with AsyncClient(auth=settings.notion_token) as notion:
            result = await notion.data_sources.query(fact_ds_id, **query)

        return self._parse_data_source_results(result)

    async def _query_talhoes_data(
        self, talhoes_ds_id: str, farm_ids: List[str]
    ) -> List[Dict]:
        """Query Talhões data source for all farms."""
        from notion_client import AsyncClient
        from core.config import settings

        all_talhoes = []

        async with AsyncClient(auth=settings.notion_token) as notion:
            for farm_id in farm_ids:
                query = {
                    "filter": {"property": "farm", "relation": {"contains": farm_id}}
                }
                result = await notion.data_sources.query(talhoes_ds_id, **query)
                talhoes = self._parse_data_source_results(result)
                all_talhoes.extend(talhoes)

        return all_talhoes

    def _parse_data_source_results(self, result: Dict) -> List[Dict]:
        """Parse data source query results."""
        items = []
        for page in result.get("results", []):
            item = {"id": page.get("id")}
            properties = page.get("properties", {})

            logger.debug(
                f"Parsing page {page.get('id')}, properties: {list(properties.keys())}"
            )

            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type")

                if prop_type == "title":
                    texts = prop_data.get("title", [])
                    item[prop_name] = "".join(t.get("plain_text", "") for t in texts)

                elif prop_type == "rich_text":
                    texts = prop_data.get("rich_text", [])
                    item[prop_name] = "".join(t.get("plain_text", "") for t in texts)

                elif prop_type == "number":
                    item[prop_name] = prop_data.get("number")

                elif prop_type == "select":
                    select = prop_data.get("select")
                    item[prop_name] = select.get("name") if select else None

                elif prop_type == "multi_select":
                    multi = prop_data.get("multi_select", [])
                    item[prop_name] = [m.get("name") for m in multi]

                elif prop_type == "relation":
                    relations = prop_data.get("relation", [])
                    item[prop_name] = [r.get("id") for r in relations]

                elif prop_type == "date":
                    date_obj = prop_data.get("date")
                    if date_obj:
                        item[prop_name] = date_obj.get("start")

                elif prop_type == "rollup":
                    # Handle rollup properties (e.g., nome_fazenda, cidade, proprietario, consultor)
                    rollup = prop_data.get("rollup", {})
                    rollup_type = rollup.get("type")

                    if rollup_type == "array":
                        # Extract from array of rich_text or formula objects
                        array = rollup.get("array", [])
                        if array and len(array) > 0:
                            first_item = array[0]
                            item_type = first_item.get("type")

                            if item_type == "rich_text":
                                rich_texts = first_item.get("rich_text", [])
                                item[prop_name] = "".join(
                                    rt.get("plain_text", "") for rt in rich_texts
                                )
                            elif item_type == "formula":
                                # Handle formula rollups (e.g., consultor)
                                formula = first_item.get("formula", {})
                                formula_type = formula.get("type")
                                if formula_type == "string":
                                    # Formula string can be None, treat as empty
                                    formula_value = formula.get("string")
                                    item[prop_name] = (
                                        formula_value
                                        if formula_value is not None
                                        else ""
                                    )
                                elif formula_type == "number":
                                    item[prop_name] = formula.get("number")
                                elif formula_type == "boolean":
                                    item[prop_name] = formula.get("boolean")
                        else:
                            # Empty array, set empty string for consistency
                            item[prop_name] = ""
                    elif rollup_type == "number":
                        item[prop_name] = rollup.get("number")
                    elif rollup_type == "date":
                        date_obj = rollup.get("date")
                        if date_obj:
                            item[prop_name] = date_obj.get("start")

            # Debug log for consultor field specifically
            if "consultor" in item:
                logger.debug(
                    f"Parsed consultor value: '{item.get('consultor')}' (type: {type(item.get('consultor')).__name__})"
                )

            items.append(item)

        logger.debug(f"Parsed {len(items)} items from data source")
        return items

    def _extract_farm_ids(self, fact_item: Dict) -> List[str]:
        """Extract farm IDs from FACT item."""
        farm_ids = fact_item.get("farm", [])
        if not isinstance(farm_ids, list):
            farm_ids = [farm_ids] if farm_ids else []
        return [fid for fid in farm_ids if fid]

    async def _resolve_farm_name(self, farm_ids: List[str]) -> str:
        """Resolve farm name from farm ID."""
        if not farm_ids:
            return ""

        try:
            from notion_client import AsyncClient
            from core.config import settings

            async with AsyncClient(auth=settings.notion_token) as notion:
                page = await notion.pages.retrieve(page_id=farm_ids[0])
                properties = page.get("properties", {})

                # Try to find title property
                for prop_data in properties.values():
                    if prop_data.get("type") == "title":
                        title_array = prop_data.get("title", [])
                        if title_array:
                            return title_array[0].get("plain_text", "")
        except Exception as e:
            logger.warning(f"Could not resolve farm name: {e}")

        return ""

    def _merge_plot_data(
        self, talhoes_data: List[Dict], plots_with_images: List[Dict]
    ) -> List[Plot]:
        """
        Merge talhões metadata with plot images.

        Args:
            talhoes_data: List of talhão metadata (name, area, etc.)
            plots_with_images: List of plots with images from page properties

        Returns:
            List of Plot objects with complete data
        """
        merged_plots = []

        # Create a map of plot names to their image data
        images_map = {}
        for plot in plots_with_images:
            plot_names = plot.get("name", [])
            if plot_names:
                for name in plot_names:
                    images_map[name] = plot

        # Merge talhões data with images
        for talhao in talhoes_data:
            # Extract talhão name from id_talhao (title) or nome_talhao (rich_text)
            talhao_id = talhao.get("id_talhao", "")
            talhao_name = talhao.get("nome_talhao", "") or talhao_id
            area = talhao.get("area", 0.0) or 0.0

            # Normalize area: handle Brazilian decimal format (13,02 -> 13.02)
            if isinstance(area, str):
                area = area.replace(",", ".")

            try:
                area_float = float(area)
            except (ValueError, TypeError):
                area_float = 0.0

            # Find matching plot with images
            image_data = images_map.get(talhao_name, {})

            # Extract images
            images = []
            for img in image_data.get("images", []):
                images.append(
                    Image(
                        url=img.get("url", ""), description=img.get("description", "")
                    )
                )

            # Create Plot object
            plot = Plot(
                id=talhao_name,
                area=area_float,
                growth_stage=image_data.get("growth_stage", [""])[0]
                if image_data.get("growth_stage")
                else "",
                crop=talhao.get("cultura", "") or "",
                variety=talhao.get("variedade", "") or "",
                images=images,
                additional_images="",
                assessment=image_data.get("assessment", [""])[0]
                if image_data.get("assessment")
                else "",
            )
            merged_plots.append(plot)

        return merged_plots

    def _build_report_model(
        self,
        fact_item: Dict,
        page_data: Dict,
        plots: List[Plot],
        farm_name: str,
        talhoes_data: List[Dict] = None,
    ) -> Report:
        """Build complete Report model from all data sources."""

        # Extract properties from page_data
        props = page_data.get("properties", {})

        # Extract text fields
        general_info = extract_text(
            props.get("Informações Gerais", {}).get("rich_text", [])
        )
        operations_schedule = extract_text(
            props.get("Cronograma de Operações da Fazenda", {}).get("rich_text", [])
        )

        # Extract dates
        visit_date_str = extract_text(
            props.get("Data da Visita", {}).get("rich_text", [])
        )
        return_date_str = extract_text(
            props.get("Data de Retorno (Prevista)", {}).get("rich_text", [])
        )

        # Parse dates
        try:
            current_visit_date = datetime.strptime(visit_date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            current_visit_date = datetime.now()

        try:
            next_visit_date = datetime.strptime(return_date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            next_visit_date = datetime.now()

        # Get metadata from talhões (preferred) or fallback to fact_item
        # Talhões have rollup data that's more reliable
        if talhoes_data and len(talhoes_data) > 0:
            first_talhao = talhoes_data[0]

            # Debug: Show what's in the first talhao
            logger.debug(f"First talhão keys: {list(first_talhao.keys())}")
            logger.debug(
                f"First talhão consultor raw value: '{first_talhao.get('consultor')}' (type: {type(first_talhao.get('consultor')).__name__})"
            )
            logger.debug(
                f"FACT item consultor raw value: '{fact_item.get('consultor')}' (type: {type(fact_item.get('consultor')).__name__})"
            )

            owner_name = first_talhao.get("proprietario", "") or fact_item.get(
                "proprietario", ""
            )
            consultant_name = first_talhao.get("consultor", "") or fact_item.get(
                "consultor", ""
            )
            farm_city = first_talhao.get("cidade", "") or fact_item.get("cidade", "")
            farm_name = (
                first_talhao.get("nome_fazenda", "")
                or farm_name
                or fact_item.get("fazenda_nome", "")
            )

            logger.debug(
                f"Using talhão metadata: consultor='{consultant_name}', "
                f"proprietario='{owner_name}', cidade='{farm_city}', fazenda='{farm_name}'"
            )
        else:
            owner_name = fact_item.get("proprietario", "")
            consultant_name = fact_item.get("consultor", "")
            farm_city = fact_item.get("cidade", "")
            farm_name = farm_name or fact_item.get("fazenda_nome", "")

            logger.debug(
                f"Using FACT metadata: consultor='{consultant_name}', "
                f"proprietario='{owner_name}', cidade='{farm_city}', fazenda='{farm_name}'"
            )

        # Build Report
        return Report(
            farm_name=farm_name,
            consultant_name=consultant_name,
            report_month=datetime.now().strftime("%B %Y"),
            owner_name=owner_name,
            farm_city=farm_city,
            harvest_period=fact_item.get("safra", "2025/2026") or "2025/2026",
            general_info=general_info,
            next_visit_date=next_visit_date,
            current_visit_date=current_visit_date,
            operations_schedule=operations_schedule,
            plots=plots,
        )
