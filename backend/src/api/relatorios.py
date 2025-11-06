from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse

from services.report.generate_report import ReportGenerator
from utils.logging import get_logger


logger = get_logger(__name__)
generator = ReportGenerator()

def _get_injection_html() -> str:
    """
    Retorna o HTML de injeção comum para todos os relatórios.
    """
    with open(Path(__file__).resolve().parent / "script.html") as f:
        injection = f.read()
    return injection


async def report_by_template(
    template: str,
    page_id: str = Query(..., description="Notion page ID (FACT)"),
) -> HTMLResponse:
    logger.info(f"Gerando relatório para página {page_id} com o template '{template}'")
    bundle_dir = (
        Path(__file__).resolve().parents[2] / "templates" / "relatorios" / template
    )
    template_file = bundle_dir / "template.html"
    if not template_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template}' não encontrado em {bundle_dir}",
        )

    try:
        logger.info("Getting fact data and generating report...")
        result = await generator.generate_report_with_template(page_id, template)

        html_content = result["html_content"]
        injection = _get_injection_html()
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", injection + "</body>")
        else:
            html_content += injection

        return HTMLResponse(content=html_content, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Falha ao gerar relatório: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
