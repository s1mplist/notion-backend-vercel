import logging
from fastapi import FastAPI

app = FastAPI(title="Notion Automation API")
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"status": "online", "message": "API rodando com sucesso!"}


async def webhook(payload):
    logger.info(payload)
    return {"payload": payload}
