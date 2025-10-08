import json
import logging
from ..config import settings

log = logging.getLogger("sawmill.openai")

SYSTEM_PROMPT = """You are a strict data extractor for a sawmill ERP.
Given a free-form message, output EXACTLY one JSON object describing one of these types:
- STOCK_IN, PRODUCTION, ORDER, DELIVERY, PAYMENT, REPORT
The JSON must use keys expected by the ERP (supplier_name, qty_logs, batch_id, thickness_mm, width_mm, qty, order_id, amount, etc).
If unsure, return a REPORT object: {"type":"REPORT","kind":"daily"}.
Output must be valid JSON only.
"""


def llm_parse_free_text(text: str) -> dict:
    # keep sync to avoid additional async dependency; used in background tasks so it's OK.
    try:
        if not settings.OPENAI_API_KEY:
            return {"type": "REPORT", "kind": "daily"}
        import openai

        openai.api_key = settings.OPENAI_API_KEY
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
            temperature=0.0,
        )
        content = None
        # handle different response shapes
        if "choices" in resp and len(resp["choices"]) > 0:
            # modern response shape
            maybe = resp["choices"][0]
            if isinstance(maybe, dict) and "message" in maybe:
                content = maybe["message"]["content"]
            elif hasattr(maybe, "message"):
                content = maybe.message.content
        if not content:
            content = str(resp)

        try:
            return json.loads(content)
        except Exception:
            import re

            m = re.search(r"\{.*\}", content, re.S)
            if m:
                return json.loads(m.group(0))
    except Exception as e:
        log.exception("OpenAI parse error: %s", e)
    return {"type": "REPORT", "kind": "daily"}
