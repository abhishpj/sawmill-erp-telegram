# app/main.py
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db

# basic logging configuration
log = logging.getLogger("sawmill")
level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(level)

# create FastAPI app instance first
app = FastAPI(title="Sawmill Telegram ERP (Prod)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ALLOWED_ORIGINS == "*" else settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# import routers AFTER app is created to avoid circular import issues
from .routers.telegram import router as telegram_router

# optional debug router; import only if file exists
try:
    from .routers.db_debug import router as debug_router
except Exception:
    debug_router = None
from .routers.debug_token import router as debug_token_router
app.include_router(debug_token_router)

# include routers
app.include_router(telegram_router)
if debug_router is not None:
    app.include_router(debug_router)

@app.on_event("startup")
def bootstrap():
    init_db()
    log.info("Bootstrap complete. environment=%s", settings.ENVIRONMENT)
    # try to auto-register webhook (best-effort)
    try:
        from .services.telegram import set_webhook
        set_webhook()
    except Exception as e:
        log.exception("Could not auto-register webhook on startup: %s", e)

@app.get("/")
def health():
    return {"ok": True, "service": "Sawmill Telegram ERP", "env": settings.ENVIRONMENT}
