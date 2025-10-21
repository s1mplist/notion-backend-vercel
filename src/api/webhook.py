import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
app = FastAPI()


@app.post("/webhook")
async def notion_webhook(request: Request):
    logger.info("Request: ", request)
    return JSONResponse(content={"teste": "ok"}, status=200)
