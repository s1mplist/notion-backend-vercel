import sys
import asyncio
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .models import WebhookRequest, GenerationMetadata
from .get_data import process_webhook_data

try:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass


# Load logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load notion client
app = FastAPI(title="Notion Teste")


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
        from .services.notion_service import NotionService
        from .services.plot_data_extractor import PlotDataExtractor
        from .services.notion_mapper import NotionDataMapper
        from .services.html_renderer import HTMLRenderer

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
        from .services.notion_service import NotionService
        from .services.plot_data_extractor import PlotDataExtractor
        from .services.notion_mapper import NotionDataMapper
        from .services.html_renderer import HTMLRenderer
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
