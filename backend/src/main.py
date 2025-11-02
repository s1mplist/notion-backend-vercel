import asyncio
import locale
import logging
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException

# FastAPI Routes
from api.health import health_check
from api.notion.webhook import webhook
from api.relatorios import generate_report_pdf, report_by_template

# Configuration
from core.config import settings
from services.report.generator import ReportGenerator


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")


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

app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/notion/webhook", webhook, methods=["POST"])
app.add_api_route("/report/{template}", report_by_template, methods=["GET"])
app.add_api_route("/report/{template_slug}/pdf", generate_report_pdf, methods=["GET"])


@app.get("/")
async def root():
    logger.info("Health check endpoint accessed")
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/report/complete")
async def generate_complete_report(page_id: str = None):
    """
    Generate complete report with enhanced metadata from data sources.
    Usage: GET /report/complete?page_id=NOTION_PAGE_ID
    """
    try:
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id parameter is required")

        generator = ReportGenerator()
        result = await generator.generate_complete_report(page_id)

        return {
            "status": result["status"],
            "farm_name": result["farm_name"],
            "plots_count": result["plots_count"],
            "page_id": result["page_id"],
            "preview_url": f"/report/complete-preview?page_id={page_id}",
            "metadata": result["metadata"],
        }

    except Exception as e:
        logger.error(f"Complete report generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
