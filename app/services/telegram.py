# app/services/telegram.py
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
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    API = f"https://api.telegram.org/bot{token}"

    if not token:
        log.error("TELEGRAM_BOT_TOKEN not configured; skipping send. API=%s", API)
        return

    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    log.debug("tg_send -> chat_id=%s reply_to=%s text_preview=%s", chat_id, reply_to_message_id, text[:80])

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{API}/sendMessage", json=payload)
            if r.status_code >= 300:
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                log.error("Telegram send error %s %s", r.status_code, body)
            else:
                try:
                    js = r.json()
                    log.info("Telegram send OK message_id=%s", js.get("result", {}).get("message_id"))
                except Exception:
                    log.info("Telegram send OK (no JSON)")
    except Exception as e:
        log.exception("tg_send exception: %s", e)


def tg_send_sync(chat_id: int, text: str, reply_to_message_id: int | None = None):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(tg_send(chat_id, text, reply_to_message_id))
        return

    asyncio.ensure_future(tg_send(chat_id, text, reply_to_message_id))
