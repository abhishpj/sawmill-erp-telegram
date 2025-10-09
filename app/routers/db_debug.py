from fastapi import APIRouter, Request, HTTPException
import sqlite3
from ..config import settings

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/db")
def debug_db(request: Request):
    secret = request.headers.get("X-Debug-Secret")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = sqlite3.connect("sawmill_mvp.db")
    cur = conn.cursor()
    cur.execute("SELECT batch_id, supplier, quantity, volume, timestamp FROM stock_in ORDER BY batch_id DESC LIMIT 5;")
    rows = cur.fetchall()
    conn.close()
    return {"rows": rows}
