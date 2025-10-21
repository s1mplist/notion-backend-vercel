import logging
from datetime import datetime
from fastapi import FastAPI, Request

# Configure structured logging for Vercel
logging.basicConfig(level=logging.DEBUG)

app = FastAPI(title="Notion Teste")
logger = logging.getLogger(__name__)


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
    logger.INFO(request)
    return {"status": "OK"}
