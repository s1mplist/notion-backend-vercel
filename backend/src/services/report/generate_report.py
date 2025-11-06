from datetime import datetime
from typing import Any

from config import get_settings
from models.report import Plot, Report
from services.data.plot_data import PlotDataExtractor
from services.html.image import optimize_html_images
from services.html.render import HTMLRenderer
from services.notion.mapper import NotionDataMapper
from services.notion.notion_service import NotionService
from utils.logging import get_logger
from utils.notion import NotionUtils


settings = get_settings()
logger = get_logger(__name__)

DEFAULT_HARVEST_PERIOD = getattr(settings, "default_harvest_period", "2025/2026")
OPS_PATTERN = r"cronogram.*oper.*fazend"
MONTHS_PT = {
    "January": "Janeiro",
    "February": "Fevereiro",
    "March": "Março",
    "April": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro",
}

class ReportGenerator:
    """Service for generating complete reports with enhanced metadata."""

    def __init__(self):
        self.notion_service = NotionService()
        self.plot_extractor = PlotDataExtractor()
        self.data_mapper = NotionDataMapper()
        self.html_renderer = HTMLRenderer()
        self.notion_utils = NotionUtils()

    async def _get_data_sources(self) -> tuple[str, str]:
        return await self.notion_service.get_data_source_ids()

    async def generate_report_with_template(
        self, page_id: str, template_slug: str
    ) -> dict[str, Any]:
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
            fact_ds_id, talhoes_ds_id = self.notion_service.get_fact_and_talhoes_data_sources()

            # 2. FACT data
            fact_data = await self.notion_service.async_query_fact_by_page_id(fact_ds_id, page_id)

            if not fact_data:
                raise ValueError(f"FACT page {page_id} not found")
            fact_item = fact_data[0]

            # 4. Talhões data
            talhoes_data = self.notion_service.query_talhoes_by_farm_ids(talhoes_ds_id, fact_item.get("farm"))

            # 5. Farm name
            farm_name = fact_item.get("nome_fazenda")

            # 6. Original page + plots/images (use NotionService async wrapper)
            page_data = await self.notion_service.async_get_page(page_id)
            plots_with_images = await self.plot_extractor.extract_plots_data(page_id)

            # 7. Merge
            enriched_plots = self.notion_service.merge_plot_data(talhoes_data, plots_with_images)

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

            # 10. OTIMIZAR IMAGENS ANTES DE GERAR PDF
            logger.info("Optimizing images in HTML...")
            html_content = optimize_html_images(
                html_content,
                quality=70,  # Ajuste conforme necessário (40-80)
            )

            return {
                "status": "success",
                "page_id": page_id,
                "farm_name": farm_name,
                "plots_count": len(enriched_plots),
                "html_content": html_content,
                "metadata": {
                    "fact_item": fact_item,
                    "talhoes_count": len(talhoes_data),
                    "template": template_slug,
                },
            }
        except Exception as e:
            logger.error(f"Error generating report with template: {e}", exc_info=True)
            raise

    async def _query_fact_data(self, fact_ds_id: str, page_id: str) -> list[dict]:
        """Query FACT data source for specific page via NotionService async wrapper."""
        # Delegate to NotionService which centralizes AsyncClient usage
        return await self.notion_service.async_query_fact_by_page_id(
            fact_ds_id, page_id.replace("-", "")
        )

    async def _resolve_farm_name(self, farm_ids: list[str]) -> str:
        """Resolve farm name from farm ID."""
        if not farm_ids:
            return ""
        # Use NotionService async helper to centralize retrieval
        try:
            title = await self.notion_service.async_resolve_page_title(farm_ids[0])
            return title or ""
        except Exception as e:
            logger.warning(f"Could not resolve farm name: {e}")
            return ""

    def _build_report_model(
        self,
        fact_item: dict,
        page_data: dict,
        plots: list[Plot],
        farm_name: str,
        talhoes_data: list[dict[str, Any]] | None = None,
    ) -> Report:
        """Build complete Report model from all data sources."""

        # Extract properties from page_data
        props = page_data.get("properties", {})

        # Extract text fields
        general_info = self.notion_utils.extract_rich_text(
            props.get("Informações Gerais", {})
        )

        # Extract operations schedule using regex
        ops_prop = self.notion_utils.find_property_by_regex(props, OPS_PATTERN)
        operations_schedule = self.notion_utils.extract_rich_text(ops_prop or {})

        # Extract dates
        visit_date_str = self.notion_utils.extract_rich_text(
            props.get("Data da Visita", {})
        )
        return_date_str = self.notion_utils.extract_rich_text(
            props.get("Data de Retorno (Prevista)", {})
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

            # PRIORIDADE: Talhões contêm os metadados corretos
            owner_name = first_talhao.get("proprietario", "") or fact_item.get(
                "proprietario", ""
            )
            consultant_name = first_talhao.get("consultor", "") or fact_item.get(
                "consultor", ""
            )
            farm_city = first_talhao.get("cidade", "") or fact_item.get("cidade", "")
            farm_name = (
                first_talhao.get("fazenda_nome", "")
                or first_talhao.get("nome_fazenda", "")
                or farm_name
                or fact_item.get("fazenda_nome", "")
            )

            logger.debug(
                f"Using talhão metadata: consultor='{consultant_name}' (from FACT), "
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

        month_en = current_visit_date.strftime("%B")
        month_pt = MONTHS_PT.get(month_en, month_en)
        report_month = f"{month_pt} {current_visit_date.year}"

        # Build Report
        return Report(
            farm_name=farm_name,
            consultant_name=consultant_name,
            report_month=report_month,
            owner_name=owner_name,
            farm_city=farm_city,
            harvest_period=fact_item.get("safra", DEFAULT_HARVEST_PERIOD)
            or DEFAULT_HARVEST_PERIOD,
            general_info=general_info,
            next_visit_date=next_visit_date,
            current_visit_date=current_visit_date,
            operations_schedule=operations_schedule,
            plots=plots,
        )
