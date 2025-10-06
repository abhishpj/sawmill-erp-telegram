import requests
from ..config import settings

API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

def tg_send(chat_id: int, text: str):
    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
    if r.status_code >= 300:
        print("Telegram send error:", r.status_code, r.text)

def set_webhook():
    if not (settings.TELEGRAM_BOT_TOKEN and settings.PUBLIC_BASE_URL):
        print("[WARN] BOT_TOKEN or PUBLIC_BASE_URL missing; webhook not set.")
        return
    url = f"{settings.PUBLIC_BASE_URL}/tg/webhook"
    resp = requests.post(f"{API}/setWebhook",
                         json={"url": url,
                               "secret_token": settings.TELEGRAM_WEBHOOK_SECRET},
                         timeout=15)
    print("SetWebhook:", resp.status_code, resp.text)