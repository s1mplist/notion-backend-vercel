from datetime import datetime
from typing import Any

from api.config import get_settings
from models.report import Plot, Report
from services.data.plot_data import PlotDataExtractor
from services.html.image import optimize_html_images
from services.html.render import HTMLRenderer
from services.notion.mapper import NotionDataMapper
from services.notion.notion_service import NotionService
from utils.logging import (
    get_logger,
    log_operation_end,
    log_operation_error,
    log_operation_start,
)
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
        logger.info("[INIT] ReportGenerator initialized")

    async def _get_data_sources(self) -> tuple[str, str]:
        return await self.notion_service.get_data_source_ids()

    async def generate_report_with_template(
        self, page_id: str, template_slug: str
    ) -> dict[str, Any]:
        """Generate a complete report with specific template."""
        log_operation_start(
            logger,
            "generate_report_with_template",
            page_id=page_id[:8],
            template=template_slug,
        )

        try:
            # 1. Get data sources
            logger.debug("[STEP:1] Fetching data sources")
            fact_ds_id, talhoes_ds_id = (
                self.notion_service.get_fact_and_talhoes_data_sources()
            )
            logger.debug(
                f"[STEP:1] Data sources obtained: fact={fact_ds_id[:8]}, talhoes={talhoes_ds_id[:8]}"
            )

            # 2. Query FACT data
            logger.debug("[STEP:2] Querying FACT data")
            fact_data = await self.notion_service.async_query_fact_by_page_id(
                fact_ds_id, page_id
            )

            if not fact_data:
                error_msg = f"FACT page {page_id} not found"
                logger.error(f"[STEP:2] {error_msg}")
                raise ValueError(error_msg)

            fact_item = fact_data[0]
            logger.debug("[STEP:2] FACT data retrieved")
            logger.debug(f"[STEP:2] FACT item keys: {list(fact_item.keys())}")
            logger.debug(f"[STEP:2] FACT item preview: {fact_item}")

            # 3. Query talhões data
            logger.debug("[STEP:3] Querying talhões data")
            talhoes_data = self.notion_service.query_talhoes_by_farm_ids(
                talhoes_ds_id, fact_item.get("farm")
            )
            logger.debug(
                f"[STEP:3] Talhões data retrieved: {len(talhoes_data)} talhões"
            )

            # 4. Farm name
            logger.debug("[STEP:4] Resolving farm name")
            farm_name = fact_item.get("nome_fazenda")
            logger.debug(f"[STEP:4] Farm name: {farm_name}")

            # 5. Get page and extract plots
            logger.debug("[STEP:5] Extracting plots data")
            page_data = await self.notion_service.async_get_page(page_id)
            plots_with_images = await self.plot_extractor.extract_plots_data(page_id)
            logger.debug(f"[STEP:5] Plots extracted: {len(plots_with_images)} plots")

            # 6. Merge data
            logger.debug("[STEP:6] Merging plot and talhões data")
            enriched_plots = self.notion_service.merge_plot_data(
                talhoes_data, plots_with_images
            )
            logger.debug(f"[STEP:6] Enriched plots: {len(enriched_plots)} plots")

            # 7. Build report model
            logger.debug("[STEP:7] Building report model")
            report_data = self._build_report_model(
                fact_item=fact_item,
                page_data=page_data,
                plots=enriched_plots,
                farm_name=farm_name,
                talhoes_data=talhoes_data,
            )
            logger.debug(
                "[STEP:7] Report model built",
                extra={"farm": report_data.farm_name, "plots": len(report_data.plots)},
            )

            # 8. Render HTML
            logger.debug(f"[STEP:8] Rendering HTML with template: {template_slug}")
            html_content = await self.html_renderer.render_template_slug(
                template_slug, report_data
            )
            logger.debug(f"[STEP:8] HTML rendered: {len(html_content)} bytes")

            # 9. Optimize images
            logger.debug("[STEP:9] Optimizing images")
            html_content = optimize_html_images(html_content, quality=70)
            logger.debug(f"[STEP:9] Images optimized: {len(html_content)} bytes")

            # 10. Get farm code
            farm_code = fact_item.get("cod_fazenda")

            logger.debug(f"[STEP:10] Farm code: {farm_code}")

            result = {
                "status": "success",
                "page_id": page_id,
                "farm_name": farm_name,
                "plots_count": len(enriched_plots),
                "html_content": html_content,
                "metadata": {
                    "fact_item": fact_item,
                    "talhoes_count": len(talhoes_data),
                    "template": template_slug,
                    "farm_code": farm_code,
                },
            }

            log_operation_end(
                logger,
                "generate_report_with_template",
                farm=farm_name,
                plots=len(enriched_plots),
                template=template_slug,
            )

            return result

        except Exception as e:
            log_operation_error(
                logger,
                "generate_report_with_template",
                e,
                page_id=page_id[:8],
                template=template_slug,
            )
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
            if visit_date_str and visit_date_str.strip():
                current_visit_date = datetime.strptime(visit_date_str, "%d/%m/%Y")
            else:
                current_visit_date = datetime.now()
        except (ValueError, TypeError):
            logger.debug(
                f"[STEP:6] Failed to parse visit date | date='{visit_date_str}'"
            )
            current_visit_date = datetime.now()

        try:
            if return_date_str and return_date_str.strip():
                next_visit_date = datetime.strptime(return_date_str, "%d/%m/%Y")
            else:
                next_visit_date = datetime.now()
        except (ValueError, TypeError):
            logger.debug(
                f"[STEP:6] Failed to parse return date | date='{return_date_str}'"
            )
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
