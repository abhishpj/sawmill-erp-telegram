import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import init_db
from .services.telegram import tg_send_sync, API as TG_API, tg_send
from .routers.telegram import router as telegram_router

# basic logging configuration
log = logging.getLogger("sawmill")
level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(level)

app = FastAPI(title="Sawmill Telegram ERP (Prod)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ALLOWED_ORIGINS == "*" else settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def bootstrap():
    init_db()
    log.info("Bootstrap complete. environment=%s", settings.ENVIRONMENT)
    # do not block startup; try to register webhook but ignore failures
    try:
        # deferred import to avoid circular import at startup if needed
        from .services.telegram import set_webhook

        set_webhook()
    except Exception as e:
        log.exception("Could not auto-register webhook on startup: %s", e)


@app.get("/")
def health():
    return {"ok": True, "service": "Sawmill Telegram ERP", "env": settings.ENVIRONMENT}


app.include_router(telegram_router)
