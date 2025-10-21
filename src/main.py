import json
import time
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Simple logging setup for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notion Teste")


# Custom middleware to log all requests
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request - using both print and logger for Vercel compatibility
        print(f"🚀 REQUEST: {request.method} {request.url}")
        logger.info(f"Request: {request.method} {request.url}")

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log response
        print(f"✅ RESPONSE: {response.status_code} ({response_time_ms:.2f}ms)")
        logger.info(f"Response: {response.status_code} ({response_time_ms:.2f}ms)")

        return response


# Add middleware
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def root():
    print("🏥 HEALTH CHECK: Root endpoint accessed")
    logger.info("Health check endpoint accessed")
    return {
        "status": "online",
        "message": "API rodando com sucesso!",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_check():
    print("🏥 HEALTH CHECK: Detailed health check requested")
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

        print(f"📨 WEBHOOK: Received {len(body)} bytes")
        logger.info(f"Webhook received: {len(body)} bytes")

        # Parse payload for logging
        payload_keys = []
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
                payload_keys = list(payload.keys()) if isinstance(payload, dict) else []
                print(f"📨 WEBHOOK: Payload keys: {payload_keys}")
                logger.info(f"Webhook payload keys: {payload_keys}")
            except json.JSONDecodeError as e:
                print(f"❌ WEBHOOK: JSON decode error: {str(e)}")
                logger.error(f"JSON decode error: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        # Log headers
        content_type = request.headers.get("content-type", "unknown")
        user_agent = request.headers.get("user-agent", "unknown")
        print(f"📨 WEBHOOK: Content-Type: {content_type}, User-Agent: {user_agent}")
        logger.info(
            f"Webhook headers - Content-Type: {content_type}, User-Agent: {user_agent}"
        )

        # Return success response
        response_data = {
            "status": "success",
            "message": "Webhook received successfully",
            "timestamp": datetime.now().isoformat(),
            "payload_size": len(body) if body else 0,
        }

        print("✅ WEBHOOK: Processed successfully, returning response")
        logger.info("Webhook processed successfully")

        return JSONResponse(status_code=200, content=response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ WEBHOOK: Processing error: {str(e)}")
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
