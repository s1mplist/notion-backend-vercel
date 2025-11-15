import json
from datetime import datetime

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from models.generation import GenerationMetadata
from models.webhook import WebhookRequest
from utils.logging import get_logger


logger = get_logger(__name__)


async def webhook(request: Request):
    """Receive Notion webhook, acknowledge immediately and process in background.

    This avoids HTTP timeouts from Notion while we generate the PDF asynchronously.
    """
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))
        webhook_model = WebhookRequest(**payload)
        logger.info(f"Received webhook: {webhook_model.id}")

        # Initialize generation metadata
        gen_meta = GenerationMetadata(
            webhook_id=webhook_model.id,
            webhook_timestamp=webhook_model.timestamp,
            entity_id=webhook_model.entity.get("id"),
            generation_started_at=datetime.now(),
            generation_status="started",
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Processing started",
                "generation": gen_meta.model_dump(mode="json"),
            },
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
