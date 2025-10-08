# app/services/openai_parser.py
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

def _extract_text_from_response(resp) -> str:
    """
    Accept multiple response shapes and return the best string content available.
    Handles Responses API and older ChatCompletion-like shapes defensively.
    """
    # 1) new Responses API: resp.output -> list(...) containing 'content' pieces
    try:
        if hasattr(resp, "output") and resp.output:
            pieces = []
            for item in resp.output:
                # item may be a dict-like or object
                content = None
                if isinstance(item, dict):
                    # item['content'] might be a list of dicts with 'type' and 'text'
                    cont = item.get("content")
                    if isinstance(cont, list):
                        for c in cont:
                            if isinstance(c, dict) and ("text" in c or "type" in c and c.get("type") == "output_text"):
                                pieces.append(c.get("text") or c.get("content") or "")
                    elif isinstance(cont, str):
                        pieces.append(cont)
                else:
                    # pydantic/object style
                    try:
                        cont = getattr(item, "content", None)
                        if cont:
                            for c in cont:
                                pieces.append(getattr(c, "text", "") or getattr(c, "content", ""))
                    except Exception:
                        pass
            if pieces:
                return "\n".join(filter(None, pieces))
    except Exception:
        pass

    # 2) older chat completion shape: resp.choices[0].message.content
    try:
        if isinstance(resp, dict) and "choices" in resp and resp["choices"]:
            maybe = resp["choices"][0]
            # choice may have 'message' or 'text'
            if isinstance(maybe, dict):
                if "message" in maybe and isinstance(maybe["message"], dict):
                    return maybe["message"].get("content", "")
                if "text" in maybe:
                    return maybe.get("text", "")
    except Exception:
        pass

    # 3) fallback: stringify the whole response
    try:
        return json.dumps(resp) if not isinstance(resp, str) else resp
    except Exception:
        return str(resp)


def llm_parse_free_text(text: str) -> dict:
    """Call OpenAI (Responses API) and extract JSON object from response text."""
    try:
        if not settings.OPENAI_API_KEY:
            return {"type": "REPORT", "kind": "daily"}

        # import lazily so library not required for other flows
        try:
            # new OpenAI client
            from openai import OpenAI
        except Exception as e:
            log.exception("OpenAI client import failed: %s", e)
            return {"type": "REPORT", "kind": "daily"}

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]

        # 1) Try Chat Completions (some newer clients expose client.chat.completions)
        try:
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                resp = client.chat.completions.create(model="gpt-4o-mini", messages=prompt, temperature=0.0, max_tokens=800)
                content = _extract_text_from_response(resp)
            else:
                # 2) Fallback to Responses API (preferred modern interface)
                resp = client.responses.create(model="gpt-4o-mini", input=prompt, temperature=0.0, max_tokens=800)
                content = _extract_text_from_response(resp)
        except Exception as e:
            log.exception("OpenAI request failed: %s", e)
            return {"type": "REPORT", "kind": "daily"}

        # try parse JSON directly
        try:
            return json.loads(content)
        except Exception:
            # try to extract a JSON substring
            import re
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass

    except Exception as e:
        log.exception("llm_parse_free_text error: %s", e)

    return {"type": "REPORT", "kind": "daily"}
