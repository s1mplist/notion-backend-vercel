import logging
from fastapi import FastAPI, Request

app = FastAPI(title="Notion Automation API")
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"status": "online", "message": "API rodando com sucesso!"}


@app.post("/api/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"Received webhook payload: {payload}")
        return {"status": "success", "payload": payload}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
