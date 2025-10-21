import logging
import json
import sys
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from config import config

# Configure structured logging for Vercel
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Vercel captures stdout
    ],
)

app = FastAPI(title=config.API_TITLE, version=config.API_VERSION)
logger = logging.getLogger(__name__)

# Add CORS middleware for webhook testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Log request details
        logger.info(f"[{request_id}] Webhook request started")
        logger.info(f"[{request_id}] Headers: {dict(request.headers)}")

        # Parse JSON payload
        payload = await request.json()

        # Log structured webhook data
        logger.info(f"[{request_id}] Webhook type: {payload.get('type', 'unknown')}")
        logger.info(
            f"[{request_id}] Workspace ID: {payload.get('workspace_id', 'unknown')}"
        )
        logger.info(f"[{request_id}] Entity: {payload.get('entity', {})}")

        # Log full payload only in development
        if config.should_log_payloads():
            logger.info(f"[{request_id}] Full payload: {json.dumps(payload, indent=2)}")
        else:
            logger.info(
                f"[{request_id}] Payload received (full logging disabled in production)"
            )

        # Process webhook (add your business logic here)
        result = {
            "status": "success",
            "request_id": request_id,
            "processed_at": datetime.now().isoformat(),
        }

        logger.info(f"[{request_id}] Webhook processed successfully")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[{request_id}] JSON decode error: {str(e)}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": "Invalid JSON payload",
        }

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "request_id": request_id, "message": str(e)}
