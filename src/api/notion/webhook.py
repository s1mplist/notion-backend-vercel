import asyncio
import json
import logging
from datetime import datetime

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from get_data import process_webhook_data
from models import GenerationMetadata, WebhookRequest


logger = logging.getLogger(__name__)


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

        async def _bg_process(model: WebhookRequest):
            try:
                logger.info(f"Background processing started for webhook: {model.id}")
                result = await process_webhook_data(gen_meta, model)
                logger.info(
                    f"Background processing finished for webhook: {model.id} -> {result.get('pdf_path')}"
                )
            except Exception as e:
                logger.exception(
                    f"Error in background processing for webhook {model.id}: {e}"
                )

        # Schedule background processing and return immediately
        asyncio.create_task(_bg_process(webhook_model))

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
