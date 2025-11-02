import logging
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse

from services.report.generator import ReportGenerator


logger = logging.getLogger(__name__)


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
    """
    Renderiza um relatório HTML usando o template escolhido em
    templates/relatorios/{template}/template.html.
    """
    # Validar existência do bundle do template
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
        generator = ReportGenerator()
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
