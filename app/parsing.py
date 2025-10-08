import re
from typing import Optional, Dict, Any
from .schemas import StockIn, Production, Order, Delivery, Payment, ReportReq

INCH_MM, FOOT_MM = 25.4, 304.8

def _to_mm(v: float, u: Optional[str]) -> float:
    if not u:
        return v
    u = u.lower()
    if u == "mm": return v
    if u == "cm": return v * 10
    if u == "m": return v * 1000
    if u in ("in", "inch", "inches", '"'): return v * INCH_MM
    if u in ("ft", "foot", "feet", "'"): return v * FOOT_MM
    raise ValueError(f"unknown unit: {u}")

def parse_size_to_mm(s: str):
    token = re.compile(r'(?P<n>\d+(?:\.\d+)?)(?P<u>mm|cm|m|in|inch|inches|ft|foot|feet|["\']?)', re.I)
    parts = re.split(r'[x×*]', s.replace(" ", ""))
    if len(parts) not in (2, 3):
        raise ValueError("size must be 2 or 3 dimensions")
    vals, units = [], []
    for p in parts:
        m = token.fullmatch(p)
        if not m:
            raise ValueError(f"bad token: {p}")
        vals.append(float(m.group('n')))
        units.append(m.group('u'))
    if len(vals) == 2:
        tmm = _to_mm(vals[0], units[0] or "in")
        wmm = _to_mm(vals[1], units[1] or "in")
        return tmm, wmm, None
    tmm = _to_mm(vals[0], units[0] or "in")
    wmm = _to_mm(vals[1], units[1] or "in")
    lmm = _to_mm(vals[2], units[2] or "ft")
    return tmm, wmm, lmm

KV = re.compile(r'([a-z_]+)\s*=\s*("(?:[^"]+)"|\'(?:[^\']+)\'|\S+)', re.I)

def kv(text: str) -> Dict[str, str]:
    out = {}
    for k, v in KV.findall(text):
        out[k.lower()] = v.strip('"\'')
    return out

def rule_parse(text: str) -> Optional[Dict[str, Any]]:
    raw = text.strip()
    if not raw:
        return None

    tokens = raw.split()
    head = tokens[0].lower()
    m = kv(raw)

    try:
        if head in ("stockin", "stock-in"):
            vol = None
            if "volume" in m:
                mv = re.fullmatch(r"(\d+(?:\.\d+)?)(?:cft)?", m["volume"].lower())
                if not mv:
                    return None
                vol = float(mv.group(1))

            return StockIn(
                supplier_name=m.get("supplier") or m.get("from") or "Unknown",
                qty_logs=int(m.get("qty") or m.get("logs") or 0),
                volume_cft=vol,
                date_str=m.get("date")
            ).dict()

        if head in ("produce", "production"):
            if "size" in m:
                tmm, wmm, lmm = parse_size_to_mm(m["size"])
            else:
                tmm = _to_mm(float(m["thickness"]), m.get("t_unit"))
                wmm = _to_mm(float(m["width"]), m.get("w_unit"))
                lmm = _to_mm(float(m["length"]), m.get("l_unit")) if "length" in m else None

            return Production(
                batch_id=int(m.get("batch") or 0),
                thickness_mm=tmm,
                width_mm=wmm,
                length_mm=lmm,
                qty=int(m.get("output") or m.get("qty") or 0),
                date_str=m.get("date")
            ).dict()

        if head == "order":
            size_text = m.get("size") or m.get("item")
            tmm = wmm = lmm = None
            if size_text:
                try:
                    tmm, wmm, lmm = parse_size_to_mm(size_text)
                except Exception:
                    pass
            return Order(
                customer_name=m.get("customer") or "",
                qty=int(m.get("qty") or 0),
                size_label=size_text,
                thickness_mm=tmm,
                width_mm=wmm,
                length_mm=lmm,
                date_str=m.get("date")
            ).dict()

        if head in ("deliver", "dispatch"):
            return Delivery(
                order_id=int(m.get("order") or 0),
                lorry_number=m.get("lorry") or "",
                date_str=m.get("date")
            ).dict()

        if head == "payment":
            return Payment(
                order_id=int(m.get("order") or 0),
                amount=float(m.get("amount") or 0),
                method=m.get("method"),
                date_str=m.get("date")
            ).dict()

        if head == "report":
            kind = m.get("kind") or (tokens[1] if len(tokens) > 1 else "daily")
            return ReportReq(kind=kind).dict()

    except Exception as e:
        print("rule_parse error:", e)
        return None

    return None
