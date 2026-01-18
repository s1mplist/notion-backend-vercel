from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse

from api.config import get_settings
from services.report.generate_report import ReportGenerator
from utils.logging import (
    get_logger,
    log_context,
    log_operation_end,
    log_operation_error,
    log_operation_start,
)


logger = get_logger(__name__)
settings = get_settings()
generator = ReportGenerator()


def _get_injection_html(farm_code: str = "", today_date: str = "") -> str:
    """Retorna o HTML de injeção comum para todos os relatórios com dados do template."""
    try:
        with open(Path(__file__).resolve().parent / "script.html") as f:
            injection = f.read()

        injection = injection.replace("{{ pdf_service_url }}", settings.pdf_service_url)

        if not farm_code:
            farm_code = "relatorio"

        if not today_date:
            today_date = datetime.now().strftime("%Y-%m-%d")

        injection = injection.replace("{{ farm_code }}", farm_code)
        injection = injection.replace("{{ today_date }}", today_date)

        return injection
    except Exception:
        logger.error("[INJECTION] Failed to load injection HTML", exc_info=True)
        return ""


async def report_by_template(
    template: str,
    page_id: str = Query(..., description="Notion page ID (FACT)"),
) -> HTMLResponse:
    """Generate report using specified template."""
    request_id = None

    try:
        with log_context() as req_id:
            request_id = req_id
            log_operation_start(
                logger,
                "report_generation",
                template=template,
                page_id=page_id[:8],
            )

            # Validar template
            bundle_dir = (
                Path(__file__).resolve().parents[1]
                / "templates"
                / "relatorios"
                / template
            )
            template_file = bundle_dir / "template.html"

            if not template_file.exists():
                logger.warning(
                    f"[VALIDATION] Template not found: {template}",
                    extra={"path": str(bundle_dir)},
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Template '{template}' não encontrado",
                )

            logger.debug(f"[VALIDATION] Template exists: {template}")

            # Gerar relatório
            logger.debug("[GENERATION] Starting report generation")
            result = await generator.generate_report_with_template(page_id, template)

            html_content = result["html_content"]
            metadata = result.get("metadata", {})
            farm_code = metadata.get("farm_code", "")
            today_date = datetime.now().strftime("%Y-%m-%d")

            logger.debug(
                "[GENERATION] Report generated",
                extra={
                    "template": template,
                    "farm_code": farm_code,
                    "plots_count": metadata.get("plots_count", 0),
                },
            )

            # Injetar scripts
            injection_html = _get_injection_html(farm_code, today_date)
            if injection_html:
                html_content = html_content.replace(
                    "</body>", injection_html + "</body>"
                )
                logger.debug("[INJECTION] Download script injected")

            log_operation_end(
                logger,
                "report_generation",
                template=template,
                farm_code=farm_code,
            )

            return HTMLResponse(
                content=html_content,
                status_code=200,
                headers={"X-Request-Id": request_id},
            )

    except HTTPException as e:
        log_operation_error(
            logger,
            "report_generation",
            e,
            template=template,
            page_id=page_id[:8],
        )
        raise

    except Exception as e:
        log_operation_error(
            logger,
            "report_generation",
            e,
            template=template,
            page_id=page_id[:8],
        )
        raise HTTPException(status_code=500, detail="Erro ao gerar relatório")
