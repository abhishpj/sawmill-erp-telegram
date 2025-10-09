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
    # normalize type key safety
    t = parsed.get("type") if isinstance(parsed, dict) else None
    if t not in {"STOCK_IN", "PRODUCTION", "ORDER", "DELIVERY", "PAYMENT", "REPORT"}:
        # return a safe REPORT fallback instead of raising
        log.warning("parse_text_sync: unrecognized or missing type in parser output (%r). Falling back to REPORT.", parsed)
        return {"type": "REPORT", "kind": "daily"}
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
            log.debug("No message found in update: %s", update)
            if update_id:
                mark_update_processed(update_id)
            return

        # source ids
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        incoming_msg_id = msg.get("message_id")
        from_user = msg.get("from", {}).get("id")

        log.info("Processing update_id=%s chat_id=%s from=%s msg_id=%s text_preview=%s",
                 update_id, chat_id, from_user, incoming_msg_id,
                 (msg.get("text") or "")[:80])

        text = (msg.get("text") or "").strip()
        if not text:
            await tg_send(chat_id, "Empty message received.", reply_to_message_id=incoming_msg_id)
            if update_id:
                mark_update_processed(update_id)
            return

        # try fast rule-based parse; fallback to LLM if needed
        payload = None
        try:
            payload = parse_text_sync(text)
        except Exception as e:
            log.exception("parse_text_sync raised exception; falling back to LLM: %s", e)
            payload = llm_parse_free_text(text)

        if not isinstance(payload, dict):
            log.warning("Parser returned non-dict payload: %r. Using REPORT fallback.", payload)
            payload = {"type": "REPORT", "kind": "daily"}

        t = payload.get("type")
        # perform action per type (all DB writes are synchronous but quick)
        try:
            if t == "STOCK_IN":
                batch_id = insert_stockin(payload)
                reply = f"✅ Stock recorded. Batch #{batch_id} | Supplier: {payload.get('supplier_name')} | Logs: {payload.get('qty_logs')}"
                await tg_send(chat_id, reply, reply_to_message_id=incoming_msg_id)

            elif t == "PRODUCTION":
                rec_id = insert_production(payload)
                reply = f"✅ Production logged. Batch {payload.get('batch_id')} | Qty {payload.get('qty')}"
                await tg_send(chat_id, reply, reply_to_message_id=incoming_msg_id)

            elif t == "ORDER":
                order_id = insert_order(payload)
                reply = f"✅ Order #{order_id} created for {payload.get('customer_name')} | Qty {payload.get('qty')}"
                await tg_send(chat_id, reply, reply_to_message_id=incoming_msg_id)

            elif t == "DELIVERY":
                did = insert_delivery(payload)
                reply = f"✅ Delivery #{did} created for Order #{payload.get('order_id')} | Lorry {payload.get('lorry_number')}"
                await tg_send(chat_id, reply, reply_to_message_id=incoming_msg_id)

            elif t == "PAYMENT":
                pid = insert_payment(payload)
                reply = f"✅ Payment #{pid} recorded for Order #{payload.get('order_id')} | Amount {payload.get('amount')}"
                await tg_send(chat_id, reply, reply_to_message_id=incoming_msg_id)

            elif t == "REPORT":
                with db_conn() as conn:
                    c = conn.cursor()
                    # use COALESCE for SQLite compatibility
                    c.execute("SELECT COALESCE(SUM(qty_logs),0) FROM stock_in")
                    logs = c.fetchone()[0]
                    c.execute("SELECT COALESCE(SUM(qty),0) FROM stock_out")
                    cut = c.fetchone()[0]
                    c.execute("SELECT COUNT(1) FROM orders WHERE status='pending'")
                    pending = c.fetchone()[0]
                report = f"Daily report\nLogs in (all time): {logs}\nPlanks cut (all time): {cut}\nOrders pending: {pending}"
                await tg_send(chat_id, report, reply_to_message_id=incoming_msg_id)

            else:
                # catch any unexpected type
                log.warning("Unhandled payload type=%r payload=%r", t, payload)
                await tg_send(chat_id, "I understood your message but couldn't classify it precisely. Please send a structured line like:\nstockin supplier=Kumar qty=50", reply_to_message_id=incoming_msg_id)

            # mark processed only after successfully reaching this point
            if update_id:
                mark_update_processed(update_id)
                log.info("Marked update %s processed", update_id)

        except Exception as e:
            log.exception("Error applying payload type=%s: %s", t, e)
            # attempt best-effort notification to user
            try:
                await tg_send(chat_id, "Could not apply the action due to an internal error.", reply_to_message_id=incoming_msg_id)
            except Exception:
                log.exception("Failed to notify user about apply error")

    except Exception as e:
        log.exception("Error processing update: %s", e)
        try:
            chat = update.get("message", {}).get("chat", {})
            chat_id = chat.get("id")
            if chat_id:
                await tg_send(chat_id, "Could not process your message. Try: stockin supplier=Kumar qty=50", reply_to_message_id=update.get("message", {}).get("message_id"))
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
