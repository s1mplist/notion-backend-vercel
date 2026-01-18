from datetime import datetime

from fastapi import FastAPI

# Configuration
from api.config import get_settings

# FastAPI Routes
from api.health import health_check
from api.relatorios import report_by_template
from utils.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)

# Load notion client
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/report/{template}", report_by_template, methods=["GET"])
app.add_api_route("/reports/{template}", report_by_template, methods=["GET"])
app.add_api_route("/relatorios/{template}", report_by_template, methods=["GET"])
app.add_api_route("/relatorio/{template}", report_by_template, methods=["GET"])


@app.get("/")
async def root():
    logger.info("Health check endpoint accessed")
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }
