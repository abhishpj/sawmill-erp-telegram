# app/routers/debug_token.py
import httpx
from fastapi import APIRouter, Request, HTTPException
from ..config import settings
import logging

log = logging.getLogger("sawmill.debug_token")
router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/getme")
async def debug_getme(request: Request):
    secret = request.headers.get("X-Debug-Secret")
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        return {"ok": False, "error": "token-empty"}
    api = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{api}/getMe")
        try:
            body = r.json()
        except Exception:
            body = r.text
    return {"status_code": r.status_code, "body": body, "masked_token": (token[:6] + "..." + token[-4:]) if len(token) > 8 else token, "token_len": len(token)}

@router.post("/test_send")
async def debug_test_send(request: Request):
    secret = request.headers.get("X-Debug-Secret")
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = await request.json()
    chat_id = payload.get("chat_id")
    text = payload.get("text", "debug send")
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        return {"ok": False, "error": "token-empty"}
    api = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{api}/sendMessage", json={"chat_id": chat_id, "text": text})
        try:
            body = r.json()
        except Exception:
            body = r.text
    return {"status_code": r.status_code, "body": body, "masked_token": (token[:6] + "..." + token[-4:]) if len(token) > 8 else token, "token_len": len(token)}
