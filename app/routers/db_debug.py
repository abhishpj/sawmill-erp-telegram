# app/routers/debug_db.py
import sqlite3
from fastapi import APIRouter, Request, HTTPException
from ..config import settings
import logging

log = logging.getLogger("sawmill.debug")

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/db")
def debug_db(request: Request):
    # protect with the same secret as the webhook
    secret = request.headers.get("X-Debug-Secret")
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Use the DB path from settings
    db_path = getattr(settings, "DB_PATH", "sawmill_mvp.db")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # show latest 10 stock_in entries and basic table list
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        cur.execute("PRAGMA table_info(stock_in)")
        schema = cur.fetchall()
        cur.execute("SELECT batch_id, supplier_id, qty_logs, volume_cft, date FROM stock_in ORDER BY batch_id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        log.exception("debug_db read error: %s", e)
        raise HTTPException(status_code=500, detail="DB read error")

    return {"db_path": db_path, "tables": tables, "stock_in_schema": schema, "stock_in_rows": rows}
