import asyncio
import locale
import logging
import sys
from datetime import datetime

from fastapi import FastAPI

# FastAPI Routes
from api.health import health_check
from api.notion.webhook import webhook
from api.relatorios import report_by_template

# Configuration
from core.config import settings


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


@app.get("/")
async def root():
    logger.info("Health check endpoint accessed")
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }
