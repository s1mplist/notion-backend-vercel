import logging
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from httpx import HTTPError

from services.pdf.generator import get_pdf_client
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


async def generate_report_pdf(
    template_slug: str,
    page_id: str = Query(..., description="FACT page ID"),
    format: str = Query("A3", description="Page format (A3, A4, Letter)"),
    landscape: bool = Query(False, description="Landscape orientation"),
):
    """
    Generate report PDF using Vercel PDF service.

    Args:
        template_slug: Template name (e.g., 'terras-gerais')
        page_id: FACT page ID from Notion
        format: PDF page format (A3, A4, Letter, Legal)
        landscape: Use landscape orientation

    Returns:
        PDF file as attachment

    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(
            f"Generating PDF report: template={template_slug}, page_id={page_id}"
        )

        # 1. Generate HTML
        generator = ReportGenerator()
        report_result = await generator.generate_report_with_template(
            page_id=page_id,
            template_slug=template_slug,
        )

        html_content = report_result["html_content"]

        # 2. Generate PDF using Vercel service
        pdf_client = get_pdf_client()
        pdf_bytes = await pdf_client.generate_pdf(
            html_content=html_content,
            format=format,
            landscape=landscape,
            print_background=True,
            # otimização agressiva
            optimize_images=True,
            max_image_width=900,
            jpeg_quality=0.45,
        )

        # 3. Return PDF
        filename = f"relatorio-{template_slug}-{page_id[:8]}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except HTTPError as e:
        logger.error(f"HTTP error calling PDF service: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail="PDF generation service unavailable"
        )

    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
