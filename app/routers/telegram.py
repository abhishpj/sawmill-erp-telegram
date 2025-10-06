from fastapi import APIRouter, Request, HTTPException
from ..config import settings
from ..services.telegram import tg_send

router = APIRouter(prefix="/tg", tags=["telegram"])

@router.post("/webhook")
async def tg_webhook(request: Request):
    # Security: verify Telegram secret token header if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="bad secret")

    update = await request.json()
    # support both message and edited_message payloads
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}

    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    # Simple help response
    if text.lower() in ("/start", "help", "/help"):
        tg_send(
            chat_id,
            "Sawmill ERP (minimal): send natural text and the system will acknowledge.\n"
            "Examples:\n"
            "- Got 50 logs from Kumar today\n"
            "- We cut 200 planks size 2x4 from batch 12\n"
            "- Dispatch order #23 using lorry TN09AB1234"
        )
        return {"ok": True}

    # Acknowledge receipt (placeholder for parsing -> DB -> confirmation)
    try:
        # In the full implementation replace the next line with:
        # payload = parse_text(text)
        # handle payload (insert to DB) and send contextual reply
        tg_send(chat_id, f"✅ Message received and logged: \"{text[:200]}\"")
    except Exception as e:
        # Don't crash on send errors; log server-side
        print("Error sending reply:", e)

    return {"ok": True}
