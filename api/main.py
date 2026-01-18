from datetime import datetime

from fastapi import FastAPI

from api.config import get_settings
from api.health import health_check
from api.relatorios import report_by_template
from utils.logging import get_logger, setup_logging


settings = get_settings()

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)

logger.info("Initializing FastAPI application")

# Load notion client
app = FastAPI(
    debug=True,
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/report/{template}", report_by_template, methods=["GET"])
app.add_api_route("/reports/{template}", report_by_template, methods=["GET"])
app.add_api_route("/relatorios/{template}", report_by_template, methods=["GET"])

logger.info(
    f"FastAPI routes registered | title={settings.api_title} | version={settings.api_version}"
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }
