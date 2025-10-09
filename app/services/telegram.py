# app/services/telegram.py  (DEBUG - remove after fix)
import asyncio
import httpx
import logging
from ..config import settings

log = logging.getLogger("sawmill.telegram")

def _masked_token(t: str) -> str:
    if not t:
        return "<EMPTY>"
    t = t.strip()
    if len(t) <= 8:
        return t
    return t[:6] + "..." + t[-4:]

async def tg_send(chat_id: int, text: str, reply_to_message_id: int | None = None):
    # Read token at runtime (avoid stale import-time value)
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    API = f"https://api.telegram.org/bot{token}"

    if not token:
        log.error("TELEGRAM_BOT_TOKEN is empty in runtime settings. API=%s", API)
        return

    # Safe debug: show masked token so we can verify which token the process has
    log.info("tg_send using token (masked): %s", _masked_token(token))
    log.debug("tg_send API url: %s/sendMessage", "https://api.telegram.org/bot<masked>")

    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{API}/sendMessage", json=payload)
            # try parse JSON body for helpful debug info
            try:
                body = r.json()
            except Exception:
                body = r.text

            if r.status_code >= 300:
                log.error("Telegram send error %s %s", r.status_code, body)
            else:
                log.info("Telegram send OK message_id=%s", body.get("result", {}).get("message_id") if isinstance(body, dict) else None)
    except Exception as e:
        log.exception("tg_send exception: %s", e)

def tg_send_sync(chat_id: int, text: str, reply_to_message_id: int | None = None):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(tg_send(chat_id, text, reply_to_message_id))
        return
    asyncio.ensure_future(tg_send(chat_id, text, reply_to_message_id))
