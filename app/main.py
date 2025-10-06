from fastapi import FastAPI
from .db import init_db
from .services.telegram import set_webhook
from .routers.telegram import router as telegram_router
from .config import settings

app = FastAPI(title="Sawmill Telegram ERP")

@app.on_event("startup")
def bootstrap():
    init_db()
    set_webhook()
    print(f"[BOOT] environment={settings.ENVIRONMENT}")

@app.get("/")
def health():
    return {"ok": True, "service": "Sawmill Telegram ERP", "env": settings.ENVIRONMENT}

app.include_router(telegram_router)