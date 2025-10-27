import sys
import asyncio
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from models import WebhookRequest, GenerationMetadata
from get_data import process_webhook_data
from core.config import settings

try:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass


# Load logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Load notion client
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)


def _inject_preview_toolbar(html: str) -> str:
    """Inject a floating 'Baixar PDF' toolbar into the HTML preview.

    The button calls window.print() so the user pode salvar como PDF no navegador.
    The toolbar is hidden when printing via @media print.
    """
    try:
        style = (
            '<style id="preview-toolbar-style">\n'
            ":root{--_btn-green: var(--secondary-color, #0fca62);--_text: var(--primary-color, #0f4c45);--_border: var(--border-color, #e0e0e0);--_bg: #fff;}\n"
            ".preview-toolbar{position:fixed;top:12px;right:12px;z-index:9999;"
            "background:var(--_bg);color:var(--_text);border:1px solid var(--_border);border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.08);"
            "padding:8px 12px;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu;display:flex;gap:10px;align-items:center;}\n"
            ".preview-toolbar .label{font-size:12px;opacity:.85}"
            ".preview-toolbar button{background:var(--_btn-green);color:#fff;border:0;border-radius:6px;padding:8px 12px;cursor:pointer;"
            "font-weight:600; box-shadow:0 2px 6px rgba(0,0,0,.08);}"
            ".preview-toolbar button:hover{filter:brightness(0.92)}"
            "@media screen{html{background:#f3f4f6} body.page-a4{width:210mm;margin:10mm auto;background:#fff;"
            "box-shadow:0 0 0 1px #e5e7eb, 0 10px 30px rgba(0,0,0,.08);overflow-x:hidden}}\n"
            "@media print{.preview-toolbar{display:none!important}}\n"
            "</style>"
        )
        toolbar = (
            '<div class="preview-toolbar">'
            '<span class="label">Pré-visualização</span>'
            '<button type="button" onclick="window.print()">Baixar PDF</button>'
            "</div>"
        )

        # Inject style before </head>
        if "</head>" in html:
            html = html.replace("</head>", style + "\n</head>", 1)
        else:
            html = style + html

        # Inject toolbar right after <body ...> and add 'page-a4' class to body for screen preview
        body_idx = html.lower().find("<body")
        if body_idx != -1:
            # find the closing '>' of the opening body tag
            close_idx = html.find(">", body_idx)
            if close_idx != -1:
                opening = html[body_idx : close_idx + 1]
                lower_opening = opening.lower()
                if "class=" in lower_opening:
                    # inject page-a4 into existing class attribute
                    # find the first occurrence of class="..."
                    cls_start = lower_opening.find("class=")
                    quote_char = (
                        '"' if '"' in opening[cls_start : cls_start + 10] else "'"
                    )
                    # locate the opening quote
                    q1 = opening.find(quote_char, cls_start)
                    q2 = opening.find(quote_char, q1 + 1)
                    if q1 != -1 and q2 != -1:
                        classes = opening[q1 + 1 : q2]
                        if "page-a4" not in classes.split():
                            classes = classes + " page-a4"
                        opening = opening[: q1 + 1] + classes + opening[q2:]
                else:
                    # add a new class attribute
                    opening = opening[:-1] + ' class="page-a4">'
                # rebuild html with modified opening body and injected toolbar
                html = html[:body_idx] + opening + toolbar + html[close_idx + 1 :]
                return html
        # Fallback: prepend toolbar
        return toolbar + html
    except Exception:
        return html


@app.get("/")
async def root():
    logger.info("Health check endpoint accessed")
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_check():
    logger.info("Detailed health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "notion-webhook-api",
        "version": "1.0.0",
    }


@app.post("/api/webhook")
async def webhook(request: Request):
    """Receive Notion webhook, acknowledge immediately and process in background.

    This avoids HTTP timeouts from Notion while we generate the PDF asynchronously.
    """
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))
        webhook_model = WebhookRequest(**payload)
        logger.info(f"Received webhook: {webhook_model.id}")

        # Initialize generation metadata
        gen_meta = GenerationMetadata(
            webhook_id=webhook_model.id,
            webhook_timestamp=webhook_model.timestamp,
            entity_id=webhook_model.entity.get("id"),
            generation_started_at=datetime.now(),
            generation_status="started",
        )

        async def _bg_process(model: WebhookRequest):
            try:
                logger.info(f"Background processing started for webhook: {model.id}")
                result = await process_webhook_data(gen_meta, model)
                logger.info(
                    f"Background processing finished for webhook: {model.id} -> {result.get('pdf_path')}"
                )
            except Exception as e:
                logger.exception(
                    f"Error in background processing for webhook {model.id}: {e}"
                )

        # Schedule background processing and return immediately
        asyncio.create_task(_bg_process(webhook_model))

        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Processing started",
                "generation": gen_meta.model_dump(mode="json"),
            },
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/debug/html")
async def debug_html(page_id: str = None):
    """
    Debug endpoint to test HTML generation.
    Usage: GET /debug/html?page_id=NOTION_PAGE_ID
    """
    try:
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id parameter is required")

        # Import services
        from services.notion_service import NotionService
        from services.plot_data_extractor import PlotDataExtractor
        from services.notion_mapper import NotionDataMapper
        from services.html_renderer import HTMLRenderer

        # Initialize services
        notion_service = NotionService()
        plot_extractor = PlotDataExtractor()
        data_mapper = NotionDataMapper()
        html_renderer = HTMLRenderer()

        logger.info(f"DEBUG HTML: Starting HTML generation for page_id: {page_id}")

        # Get data from Notion
        notion_data = await notion_service.get_page(page_id)
        plots_data = await plot_extractor.extract_plots_data(page_id)

        # Map data to report model
        report_data = data_mapper.map_to_report(notion_data, plots_data)

        # Generate HTML
        html_content = await html_renderer.render_report_html(report_data)

        # Print HTML to terminal (debug output)
        print("\n" + "=" * 80)
        print("DEBUG HTML OUTPUT")
        print("=" * 80)
        print(html_content)
        print("=" * 80)
        print(f"HTML Length: {len(html_content)} characters")
        print("=" * 80 + "\n")

        return {
            "status": "success",
            "message": "HTML generated successfully - check terminal output",
            "html_length": len(html_content),
            "farm_name": getattr(report_data, "farm_name", ""),
            "plots_count": len(getattr(report_data, "plots", [])),
        }

    except Exception as e:
        logger.error(f"Debug HTML error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@app.get("/debug/html-preview")
async def debug_html_preview(page_id: str = None):
    """
    Debug endpoint to preview HTML in browser.
    Usage: GET /debug/html-preview?page_id=NOTION_PAGE_ID
    """
    try:
        if not page_id:
            return "<h1>Error: page_id parameter is required</h1><p>Usage: /debug/html-preview?page_id=YOUR_NOTION_PAGE_ID</p>"

        # Import services
        from services.notion_service import NotionService
        from services.plot_data_extractor import PlotDataExtractor
        from services.notion_mapper import NotionDataMapper
        from services.html_renderer import HTMLRenderer
        from fastapi.responses import HTMLResponse

        # Initialize services
        notion_service = NotionService()
        plot_extractor = PlotDataExtractor()
        data_mapper = NotionDataMapper()
        html_renderer = HTMLRenderer()

        logger.info(
            f"DEBUG HTML PREVIEW: Starting HTML generation for page_id: {page_id}"
        )

        # Get data from Notion
        notion_data = await notion_service.get_page(page_id)
        plots_data = await plot_extractor.extract_plots_data(page_id)

        # Map data to report model
        report_data = data_mapper.map_to_report(notion_data, plots_data)

        # Generate HTML
        html_content = await html_renderer.render_report_html(report_data)

        # Return HTML response that can be viewed in browser
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Debug HTML preview error: {str(e)}", exc_info=True)
        return HTMLResponse(content=f"<h1>Debug Error</h1><pre>{str(e)}</pre>")


@app.get("/report/html-preview")
async def report_html_preview(page_id: str = None):
    """
    Public endpoint to preview report HTML in the browser (shareable link).
    Usage: GET /report/html-preview?page_id=NOTION_PAGE_ID
    """
    try:
        if not page_id:
            from fastapi.responses import PlainTextResponse

            return PlainTextResponse(
                content="Error: page_id parameter is required\nUsage: /report/html-preview?page_id=YOUR_NOTION_PAGE_ID",
                status_code=400,
            )

        # Import services locally to keep cold start lean
        from services.notion_service import NotionService
        from services.plot_data_extractor import PlotDataExtractor
        from services.notion_mapper import NotionDataMapper
        from services.html_renderer import HTMLRenderer
        from fastapi.responses import HTMLResponse

        notion_service = NotionService()
        plot_extractor = PlotDataExtractor()
        data_mapper = NotionDataMapper()
        html_renderer = HTMLRenderer()

        logger.info(f"REPORT HTML PREVIEW: Generating HTML for page_id: {page_id}")

        # Fetch and map data
        notion_data = await notion_service.get_page(page_id)
        plots_data = await plot_extractor.extract_plots_data(page_id)
        report_data = data_mapper.map_to_report(notion_data, plots_data)

        # Render HTML
        html_content = await html_renderer.render_report_html(report_data)

        # Inject toolbar to allow user to print/save as PDF
        html_with_toolbar = _inject_preview_toolbar(html_content)

        return HTMLResponse(content=html_with_toolbar)
    except Exception as e:
        logger.error(f"Report HTML preview error: {str(e)}", exc_info=True)
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{str(e)}</pre>", status_code=500
        )
