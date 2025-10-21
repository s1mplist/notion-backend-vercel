import logging
import json
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

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
    try:
        # Get the raw body
        body = await request.body()

        # Log the incoming request
        logger.info(f"Webhook received: {len(body)} bytes")
        logger.info(f"Headers: {dict(request.headers)}")
        print(request)

        payload = json.loads(body.decode("utf-8"))
        logger.info(f"Webhook payload: {payload}")

        # Return success response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Webhook received successfully",
                "timestamp": datetime.now().isoformat(),
                "payload_size": len(body) if body else 0,
                "body": payload,
            },
        )

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
