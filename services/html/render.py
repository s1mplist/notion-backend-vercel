import asyncio
import hashlib
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from api.config import get_settings
from models.report import Report
from utils.html import inline_local_images
from utils.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)


class HTMLRenderer:
    """
    HTML renderer using Jinja2 templates.

    This class handles the rendering of HTML content from Report data using
    the templates in the template/ directory. The rendered HTML can then be
    sent to any PDF service (Bannerbear, PDFShift, etc.).

    Optionally, attempts to load a legacy template ('report_template.html') if present;
    if not found, this is handled gracefully with exception handling.
    """

    def __init__(self) -> None:
        templates_dir = self._locate_templates_dir()
        self.templates_root = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=True,
        )
        # Keep compatibility with current path structure
        self.template_name = "relatorios/terras-gerais/template.html"

        # Load legacy template if present (optional)
        try:
            self.report_template = self.env.get_template("report_template.html")
        except TemplateNotFound:
            self.report_template = None

        # Audit logging configuration
        self._enable_html_audit = settings.enable_html_audit
        self._html_audit_max_chars = settings.html_audit_max_chars

    def _locate_templates_dir(self) -> Path:
        """Locate the templates/ directory robustly (dev and server).

        Resolution order:
        1) Environment variable TEMPLATES_DIR (if set and exists)
        2) Optional settings.templates_dir (if present and exists)
        3) Walk up from this file and pick the first '<parent>/templates' that exists
        4) Current working directory 'templates' (if exists)

        Raises FileNotFoundError if not found.
        """
        # 1) Environment override
        env_dir = os.getenv("TEMPLATES_DIR")
        if env_dir:
            p = Path(env_dir).resolve()
            if p.is_dir():
                return p

        # 2) Settings override (optional attr)
        cfg_dir = getattr(settings, "templates_dir", None)
        if cfg_dir:
            p = Path(str(cfg_dir)).resolve()
            if p.is_dir():
                return p

        # 3) Search parents for a 'templates' directory
        here = Path(__file__).resolve()
        for parent in [here] + list(here.parents):
            candidate = (parent / "templates").resolve()
            if candidate.is_dir():
                return candidate

        # 4) CWD fallback
        cwd_candidate = (Path.cwd() / "templates").resolve()
        if cwd_candidate.is_dir():
            return cwd_candidate

        raise FileNotFoundError(
            f"Templates directory not found. Tried TEMPLATES_DIR, settings.templates_dir,"
            f" parents of {here}, and {cwd_candidate}"
        )

    async def render_report_html(self, report_data: Report) -> str:
        """
        Render the complete HTML for the report.

        Args:
            report_data: Report model with data

        Returns:
            Complete HTML string ready for PDF conversion
        """
        # Usa dados como estão (sem otimização de imagem)
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

        # renderização (antes usava Environment implícito)
        template = self.env.get_template(self.template_name)
        html = await template.render_async(**context)
        return html

    def render_report_html_sync(self, report_data: Report) -> str:
        """
        Synchronous version of render_report_html for compatibility.

        Args:
            report_data: Report model with data

        Returns:
            Complete HTML string ready for PDF conversion
        """
        # If there's no running loop, use asyncio.run (simple path).
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.render_report_html(report_data))

        # If an event loop is already running (e.g., inside an async server),
        # run the async renderer in a separate thread with its own loop to
        # avoid "Event loop is closed" or "This event loop is already running" errors.
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
        """
        Render a report using a dynamic template bundle under templates/relatorios/{template_slug}.

        The bundle must contain:
        - template.html (main template)
        - styles.css (optional)
        - any partials like talhao.html (referenced via {% include 'talhao.html' %})

        Args:
            template_slug: e.g. "terras-gerais"
            report_data: Report model with data

        Returns:
            Rendered HTML string
        """
        base_dir = self.templates_root / "relatorios" / template_slug
        if not base_dir.exists():
            raise FileNotFoundError(
                f"Template '{template_slug}' não encontrado em {base_dir}"
            )

        # Build a dedicated Jinja environment rooted at the template bundle directory
        auto_reload = getattr(settings, "jinja_auto_reload", True)
        env = Environment(
            loader=FileSystemLoader(str(base_dir)),
            enable_async=True,
            auto_reload=auto_reload,
            cache_size=100,
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        template = env.get_template("template.html")

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
            "operations_schedule": getattr(report_data, "operations_schedule", ""),
            "plots": getattr(report_data, "plots", []) or [],
        }

        html = await template.render_async(**context)
        final_html = inline_local_images(html, base_dir)

        if self._enable_html_audit:
            self._log_html_audit(final_html, context, report_data)

        return final_html

    def _log_html_audit(self, html_content: str, context: dict, report_data: Report):
        """
        Log HTML content for audit purposes.

        Args:
            html_content: Generated HTML content
            context: Template context used for rendering
            report_data: Original report data
        """
        # Generate a hash for the content to track uniqueness
        content_hash = hashlib.md5(html_content.encode("utf-8")).hexdigest()[:8]
        content_size = len(html_content)

        # Extract key metadata for audit
        farm_name = getattr(report_data, "farm_name", "Unknown")
        plots_count = len(getattr(report_data, "plots", []))

        # Log audit summary
        logger.info(
            "HTML_AUDIT | Farm: %s | Plots: %d | Size: %d chars | Hash: %s",
            farm_name,
            plots_count,
            content_size,
            content_hash,
        )

        # Log template context (excluding sensitive data)
        safe_context = self._sanitize_context_for_log(context)
        logger.debug(
            "HTML_AUDIT_CONTEXT | Hash: %s | Context: %s", content_hash, safe_context
        )

        # Log full HTML content at debug level (can be disabled in production)
        # Sanitize HTML content for logging on terminals that can't encode emojis
        truncated = self._truncate_html_for_log(html_content)
        try:
            safe_html = truncated.encode("ascii", "backslashreplace").decode("ascii")
        except Exception:
            safe_html = truncated  # best-effort

        logger.debug(
            "HTML_AUDIT_CONTENT | Hash: %s | Timestamp: %s | Content:\n%s",
            content_hash,
            datetime.now().isoformat(),
            safe_html,
        )

        # Log plots data summary
        self._log_plots_audit(
            plots_count, getattr(report_data, "plots", []), content_hash
        )

    def _sanitize_context_for_log(self, context: dict) -> dict:
        """
        Sanitize context data for logging by removing/truncating large values.

        Args:
            context: Template context dictionary

        Returns:
            Sanitized context safe for logging
        """
        safe_context = {}
        for key, value in context.items():
            if key == "plots":
                # Summarize plots instead of logging full data
                safe_context[key] = f"[{len(value)} plots]" if value else "[]"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate long strings
                safe_context[key] = value[:97] + "..."
            else:
                safe_context[key] = value
        return safe_context

    def _truncate_html_for_log(self, html_content: str, max_chars: int = None) -> str:
        """
        Truncate HTML content for logging to avoid huge log entries.

        Args:
            html_content: Full HTML content
            max_chars: Maximum characters to include in log (uses instance default if None)

        Returns:
            Truncated HTML content
        """
        if max_chars is None:
            max_chars = self._html_audit_max_chars

        if len(html_content) <= max_chars:
            return html_content

        # Truncate and add indicator
        truncated = html_content[:max_chars]
        return f"{truncated}\n... [TRUNCATED - Total length: {len(html_content)} chars]"

    def _log_plots_audit(self, plots_count: int, plots_data: list, content_hash: str):
        """
        Log plots data summary for audit.

        Args:
            plots_count: Number of plots
            plots_data: Full plots data
            content_hash: Content hash for correlation
        """
        if not plots_data:
            logger.debug("HTML_AUDIT_PLOTS | Hash: %s | No plots data", content_hash)
            return

        # Count images across all plots
        total_images = sum(len(getattr(plot, "images", [])) for plot in plots_data)

        # Get plot names for audit trail
        plot_names = []
        for plot in plots_data[:5]:  # Limit to first 5 for logging
            # For Plot objects, use the id since name might not exist
            plot_id = getattr(plot, "id", "Unknown")
            crop = getattr(plot, "crop", "")
            variety = getattr(plot, "variety", "")
            if crop and variety:
                plot_names.append(f"{plot_id} ({crop} - {variety})")
            else:
                plot_names.append(plot_id)

        if len(plots_data) > 5:
            plot_names.append(f"... and {len(plots_data) - 5} more")

        logger.debug(
            "HTML_AUDIT_PLOTS | Hash: %s | Count: %d | Images: %d | Names: %s",
            content_hash,
            plots_count,
            total_images,
            "; ".join(plot_names),
        )
