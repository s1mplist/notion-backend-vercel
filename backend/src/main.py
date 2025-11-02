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


def _try_set_locale(preferred_locales):
    """Try to set the first available locale from preferred_locales.

    Returns the locale string that was successfully set, or None if none worked.
    """
    for loc in preferred_locales:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return loc
        except Exception:
            # ignore and try next
            continue
    return None


# Attempt to set a Portuguese (Brazil) locale but don't crash if the
# environment doesn't support it (some serverless/container images don't).
_preferred_locales = [
    "pt_BR.UTF-8",
    "pt_BR.utf8",
    "pt_BR",
    # Windows variant (if someone runs locally on Windows)
    "Portuguese_Brazil.1252",
]
_selected_locale = _try_set_locale(_preferred_locales)
if _selected_locale is None:
    # Logging isn't configured yet — use print to avoid raising during import.
    # It's expected on some hosts (e.g. minimal containers) that pt_BR isn't available.
    try:
        print("Warning: could not set pt_BR locale; continuing with default locale.")
    except Exception:
        pass


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
