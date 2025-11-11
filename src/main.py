import locale
from datetime import datetime

from fastapi import FastAPI

# FastAPI Routes
from api.health import health_check
from api.notion.webhook import webhook
from api.relatorios import report_by_template

# Configuration
from config import get_settings
from utils.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)


def _try_set_locale():
    preferred_locales = [
        "pt_BR.UTF-8",
        "pt_BR.utf8",
        "pt_BR",
    ]

    logger.debug(f"Attempting to set locale from preferred list: {preferred_locales}")

    for loc in preferred_locales:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            logger.info(f"Locale set successfully: {loc}")
            return loc
        except Exception:
            continue
    logger.warning("No suitable locale found; defaulting to 'C.UTF-8'")
    return "C.UTF-8"


_try_set_locale()


# Load notion client
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/notion/webhook", webhook, methods=["POST"])

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
