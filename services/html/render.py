import asyncio
import os
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.config import get_settings
from models.report import Report
from utils.html import inline_local_images
from utils.logging import get_logger, log_operation_end, log_operation_start


settings = get_settings()
logger = get_logger(__name__)


class HTMLRenderer:
    """HTML renderer with environment caching and async optimizations."""

    def __init__(self) -> None:
        templates_dir = self._locate_templates_dir()
        self.templates_root = templates_dir

        # Cache de Environments por template slug
        self._env_cache: dict[str, Environment] = {}

        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=True,
            cache_size=500,  # Aumentado de 100
        )
        self.template_name = "relatorios/terras-gerais/template.html"

        logger.info(
            f"[INIT] HTMLRenderer initialized with templates_dir: {templates_dir}"
        )

    def _get_or_create_env(self, template_slug: str) -> Environment:
        """Get cached environment or create and cache new one."""
        if template_slug in self._env_cache:
            logger.debug(
                f"[RENDER] Using cached environment | template={template_slug}"
            )
            return self._env_cache[template_slug]

        base_dir = self.templates_root / "relatorios" / template_slug

        # auto_reload apenas em desenvolvimento local, não em DEBUG
        is_dev = os.getenv("ENV") == "development"
        env = Environment(
            loader=FileSystemLoader(str(base_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=is_dev,
            cache_size=500,  # Aumentado
            enable_async=True,
        )

        self._env_cache[template_slug] = env
        logger.debug(f"[RENDER] Created new environment | template={template_slug}")
        return env

    def _locate_templates_dir(self) -> Path:
        """Locate the templates/ directory robustly."""
        logger.debug("[LOCATE] Searching for templates directory")

        env_dir = os.getenv("TEMPLATES_DIR")
        if env_dir:
            p = Path(env_dir).resolve()
            if p.is_dir():
                logger.debug(f"[LOCATE] Found in env: {p}")
                return p

        cfg_dir = getattr(settings, "templates_dir", None)
        if cfg_dir:
            p = Path(str(cfg_dir)).resolve()
            if p.is_dir():
                logger.debug(f"[LOCATE] Found in settings: {p}")
                return p

        here = Path(__file__).resolve()
        for parent in [here] + list(here.parents):
            potential = parent / "templates"
            if potential.is_dir():
                logger.debug(f"[LOCATE] Found in parents: {potential}")
                return potential

        cwd = Path.cwd() / "templates"
        if cwd.is_dir():
            logger.debug(f"[LOCATE] Found in cwd: {cwd}")
            return cwd

        error_msg = "Templates directory not found"
        logger.error(f"[LOCATE] {error_msg}")
        raise FileNotFoundError(error_msg)

    async def render_report_html(self, report_data: Report) -> str:
        """Render the complete HTML for the report."""
        next_visit = getattr(report_data, "next_visit_date", None)
        current_visit = getattr(report_data, "current_visit_date", None)

        context = {
            "farm_name": getattr(report_data, "farm_name", ""),
            "consultant_name": getattr(report_data, "consultant_name", ""),
            "report_month": getattr(report_data, "report_month", ""),
            "owner_name": getattr(report_data, "owner_name", ""),
            "farm_city": getattr(report_data, "farm_city", ""),
            "harvest_period": getattr(report_data, "harvest_period", ""),
            "general_info": getattr(report_data, "general_info", ""),
            "next_visit_date": next_visit.strftime("%d/%m/%Y") if next_visit else "",
            "current_visit_date": current_visit.strftime("%d/%m/%Y")
            if current_visit
            else "",
            "plots": getattr(report_data, "plots", []),
        }

        template = self.env.get_template(self.template_name)
        html = await template.render_async(**context)
        return html

    def render_report_html_sync(self, report_data: Report) -> str:
        """Synchronous version of render_report_html for compatibility."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.render_report_html(report_data))

        import concurrent.futures

        def _run_in_thread(data: Report) -> str:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.render_report_html(data))
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_run_in_thread, report_data)
            return fut.result()

    async def render_template_slug(
        self, template_slug: str, report_data: Report
    ) -> str:
        """Render template with report data."""
        start_time = time.perf_counter()
        log_operation_start(logger, "render_template_slug", template=template_slug)

        try:
            base_dir = self.templates_root / "relatorios" / template_slug
            logger.debug(f"[RENDER] Template base dir: {base_dir}")

            # Usar ambiente cacheado
            env = self._get_or_create_env(template_slug)
            template = env.get_template("template.html")
            logger.debug("[RENDER] Template loaded: template.html")

            next_visit = getattr(report_data, "next_visit_date", None)
            current_visit = getattr(report_data, "current_visit_date", None)

            context = {
                "farm_name": getattr(report_data, "farm_name", ""),
                "farm_code": getattr(report_data, "farm_code", ""),
                "consultant_name": getattr(report_data, "consultant_name", ""),
                "report_month": getattr(report_data, "report_month", ""),
                "owner_name": getattr(report_data, "owner_name", ""),
                "farm_city": getattr(report_data, "farm_city", ""),
                "harvest_period": getattr(report_data, "harvest_period", ""),
                "general_info": getattr(report_data, "general_info", ""),
                "next_visit_date": next_visit.strftime("%d/%m/%Y")
                if next_visit
                else "",
                "current_visit_date": (
                    current_visit.strftime("%d/%m/%Y") if current_visit else ""
                ),
                "operations_schedule": getattr(report_data, "operations_schedule", ""),
                "plots": getattr(report_data, "plots", []) or [],
            }

            logger.debug(f"[RENDER] Context prepared | plots={len(context['plots'])}")

            # Renderizar template
            render_start = time.perf_counter()
            html = await template.render_async(**context)
            render_time = time.perf_counter() - render_start
            logger.debug(
                f"[RENDER] Template rendered | size={len(html)} bytes | time={render_time:.3f}s"
            )

            # Inline images (considere mover para async em utils/html.py)
            inline_start = time.perf_counter()
            final_html = inline_local_images(html, base_dir)
            inline_time = time.perf_counter() - inline_start
            logger.debug(
                f"[RENDER] Images inlined | final_size={len(final_html)} bytes | time={inline_time:.3f}s"
            )

            total_time = time.perf_counter() - start_time
            log_operation_end(
                logger,
                "render_template",
                template=template_slug,
                size_bytes=len(final_html),
                elapsed_ms=int(total_time * 1000),
            )

            return final_html

        except Exception:
            logger.error(
                f"[RENDER] Failed to render template | template={template_slug}",
                exc_info=True,
            )
            raise
