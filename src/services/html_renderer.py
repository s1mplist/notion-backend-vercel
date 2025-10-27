import logging
import hashlib
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from models.report import Report
from core.config import settings
from utils.html_utils import inline_assets


logger = logging.getLogger(__name__)


class HTMLRenderer:
    """
    HTML renderer using Jinja2 templates.

    This class handles the rendering of HTML content from Report data using
    the templates in the template/ directory. The rendered HTML can then be
    sent to any PDF service (Bannerbear, PDFShift, etc.).
    """

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        self.template_dir = repo_root / "template"

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            enable_async=True,
            auto_reload=False,
            cache_size=100,
        )

        # Load templates
        self.report_template = self.env.get_template("report_template.html")

        # Read and cache CSS
        self._styles = self._read_styles()

        # Audit logging configuration
        self._enable_html_audit = settings.enable_html_audit
        self._html_audit_max_chars = settings.html_audit_max_chars

    def _read_styles(self) -> str:
        """Read the CSS file and return its contents."""
        css_path = self.template_dir / "styles.css"
        try:
            return css_path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("CSS file not found; continuing without styles")
            return ""

    async def render_report_html(self, report_data: Report) -> str:
        """
        Render the complete HTML for the report.

        Args:
            report_data: Report model with data

        Returns:
            Complete HTML string ready for PDF conversion
        """
        # Use report data as-is (no image optimization)
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

        # Use async template rendering
        html = await self.report_template.render_async(**context)
        final_html = inline_assets(html, self.template_dir, self._styles)

        # Log HTML for audit
        if self._enable_html_audit:
            self._log_html_audit(final_html, context, report_data)

        return final_html

    def render_report_html_sync(self, report_data: Report) -> str:
        """
        Synchronous version of render_report_html for compatibility.

        Args:
            report_data: Report model with data

        Returns:
            Complete HTML string ready for PDF conversion
        """
        import asyncio

        return asyncio.run(self.render_report_html(report_data))

    def get_css_content(self) -> str:
        """
        Get the CSS content for external usage.

        Returns:
            CSS content as string
        """
        return self._styles

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
        logger.debug(
            "HTML_AUDIT_CONTENT | Hash: %s | Timestamp: %s | Content:\n%s",
            content_hash,
            datetime.now().isoformat(),
            self._truncate_html_for_log(html_content),
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

    # Note: image optimization intentionally removed per requirements
