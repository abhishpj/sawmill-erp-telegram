import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from ..config import settings
from ..parsing import rule_parse
from ..services.openai_parser import llm_parse_free_text
from ..services.telegram import tg_send, tg_send_sync
from ..db import (
    insert_stockin, insert_production, insert_order,
    insert_delivery, insert_payment, is_update_processed, mark_update_processed, db_conn
)

log = logging.getLogger("sawmill.router")

router = APIRouter(prefix="/tg", tags=["telegram"])


def parse_text_sync(text: str) -> dict:
    parsed = rule_parse(text)
    if not parsed:
        parsed = llm_parse_free_text(text)
    t = parsed.get("type")
    if t not in {"STOCK_IN", "PRODUCTION", "ORDER", "DELIVERY", "PAYMENT", "REPORT"}:
        raise ValueError("unrecognized type")
    return parsed


async def process_update(update: dict):
    """Background processing of a Telegram update. Called async."""
    try:
        update_id = update.get("update_id")
        if update_id and is_update_processed(update_id):
            log.info("Skipping duplicate update %s", update_id)
            return

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        if not text:
            await tg_send(chat_id, "Empty message received.")
            if update_id:
                mark_update_processed(update_id)
            return

        # try fast rule-based parse; fallback to LLM if needed
        try:
            payload = parse_text_sync(text)
        except Exception as e:
            log.exception("parse failed, will fallback to LLM: %s", e)
            payload = llm_parse_free_text(text)

        t = payload.get("type")
        if t == "STOCK_IN":
            batch_id = insert_stockin(payload)
            await tg_send(chat_id, f"✅ Stock recorded. Batch #{batch_id} | Supplier: {payload.get('supplier_name')} | Logs: {payload.get('qty_logs')}")
        elif t == "PRODUCTION":
            rec_id = insert_production(payload)
            await tg_send(chat_id, f"✅ Production logged. Batch {payload.get('batch_id')} | Qty {payload.get('qty')}")
        elif t == "ORDER":
            order_id = insert_order(payload)
            await tg_send(chat_id, f"✅ Order #{order_id} created for {payload.get('customer_name')} | Qty {payload.get('qty')}")
        elif t == "DELIVERY":
            did = insert_delivery(payload)
            await tg_send(chat_id, f"✅ Delivery #{did} created for Order #{payload.get('order_id')} | Lorry {payload.get('lorry_number')}")
        elif t == "PAYMENT":
            pid = insert_payment(payload)
            await tg_send(chat_id, f"✅ Payment #{pid} recorded for Order #{payload.get('order_id')} | Amount {payload.get('amount')}")
        elif t == "REPORT":
            with db_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT IFNULL(SUM(qty_logs),0) FROM stock_in")
                logs = c.fetchone()[0]
                c.execute("SELECT IFNULL(SUM(qty),0) FROM stock_out")
                cut = c.fetchone()[0]
                c.execute("SELECT COUNT(1) FROM orders WHERE status='pending'")
                pending = c.fetchone()[0]
            await tg_send(chat_id, f"Daily report\nLogs in (all time): {logs}\nPlanks cut (all time): {cut}\nOrders pending: {pending}")

        if update.get("update_id"):
            mark_update_processed(update.get("update_id"))

    except Exception as e:
        log.exception("Error processing update: %s", e)
        try:
            # try to notify user briefly (best-effort)
            chat = update.get("message", {}).get("chat", {})
            chat_id = chat.get("id")
            if chat_id:
                # use async send
                await tg_send(chat_id, "Could not process your message. Try a short structured message like:\nstockin supplier=Kumar qty=50 volume=500cft")
        except Exception:
            log.exception("Failed to notify user of processing error")


@router.post("/webhook")
async def tg_webhook(request: Request, background_tasks: BackgroundTasks):
    # verify secret header quickly
    if settings.TELEGRAM_WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="bad secret")

    update = await request.json()
    # schedule background processing and return 200 fast
    background_tasks.add_task(process_update, update)
    return {"ok": True}
