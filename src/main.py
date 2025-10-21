import json
import time
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import setup_vercel_logging, log_request, log_response, log_webhook

# Setup Vercel-optimized logging
logger = setup_vercel_logging("INFO")

app = FastAPI(title="Notion Teste")


# Custom middleware to log all requests
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        log_request(logger, request.method, request.url, request.headers)

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log response
        log_response(logger, response.status_code, response_time_ms)

        return response


# Add middleware
app.add_middleware(LoggingMiddleware)


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

        # Parse payload for logging
        payload_keys = []
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
                payload_keys = list(payload.keys()) if isinstance(payload, dict) else []
            except json.JSONDecodeError:
                payload_keys = ["invalid_json"]

        # Log webhook with structured data
        log_webhook(
            logger,
            len(body),
            request.headers.get("content-type", "unknown"),
            request.headers.get("user-agent", "unknown"),
            payload_keys,
        )

        # Return success response
        response_data = {
            "status": "success",
            "message": "Webhook received successfully",
            "timestamp": datetime.now().isoformat(),
            "payload_size": len(body) if body else 0,
        }

        logger.info(
            "Webhook processed successfully",
            extra={"event_type": "webhook_success", "response_status": 200},
        )

        return JSONResponse(status_code=200, content=response_data)

    except json.JSONDecodeError as e:
        logger.error(
            "JSON decode error",
            extra={
                "event_type": "webhook_error",
                "error_type": "json_decode",
                "error_message": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        logger.error(
            "Webhook processing error",
            extra={
                "event_type": "webhook_error",
                "error_type": "general",
                "error_message": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
