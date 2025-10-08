import asyncio
import httpx
import logging
from ..config import settings

log = logging.getLogger("sawmill.telegram")
API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def tg_send(chat_id: int, text: str):
    """Async sendMessage wrapper. Non-blocking."""
    if not settings.TELEGRAM_BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not configured; skipping send")
        return

    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{API}/sendMessage", json=payload)
            if r.status_code >= 300:
                log.error("Telegram send error %s %s", r.status_code, r.text)
    except Exception as e:
        log.exception("tg_send exception: %s", e)


# convenience sync wrapper if some callers are sync - uses asyncio.run_coroutine_threadsafe when loop running
def tg_send_sync(chat_id: int, text: str):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # no loop running; run directly
        asyncio.run(tg_send(chat_id, text))
        return

    # schedule in background
    asyncio.ensure_future(tg_send(chat_id, text))
