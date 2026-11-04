"""What the owner learns from everything their agent handled: money in and out, why things come back,
which products and which customers. Built only from recorded cases. Nothing is estimated except the
card fee on refunds, which is labelled as an estimate wherever it's shown.
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict

from .config import SETTINGS

REASONS = [
    ("Wrong size or fit", r"\b(?:size|fit|fits|too (?:small|big|large|tight|loose))\b"),
    ("Arrived damaged", r"\b(?:broke|broken|crack(?:ed)?|damaged|dent(?:ed)?|squished|smashed|leak(?:ed|ing)?|stain(?:ed)?|torn)\b"),
    ("Never arrived or late", r"\b(?:never (?:arrived|came|got)|didn'?t (?:arrive|come|get)|not (?:arrived|delivered)|late|lost|missing|stolen)\b"),
    ("Quality or not as described", r"\b(?:fell apart|quality|cheap|not as (?:described|pictured)|stopped working|doesn'?t work|defect(?:ive)?|smell|taste[sd]?)\b"),
    ("Ordered too many or changed mind", r"\b(?:too many|changed my mind|don'?t (?:need|want)|no longer|by mistake|ordered (?:twice|two))\b"),
]
RETURN_ACTIONS = ("refund", "reship")
# Attempts to trick the agent are fraud, not returns, so they don't skew "why things come back".
FRAUD_RULES = {"owner_impersonation", "prompt_injection", "amount_mismatch", "unknown_action", "payment_redirect",
               "code_request", "image_payment_redirect"}


def reason_of(text: str) -> str:
    for label, pat in REASONS:
        if re.search(pat, text or "", re.I):
            return label
    return "Other or not said"


def _fee(amount: float) -> float:
    p = SETTINGS.policy
    return amount * p.processor_fee_pct / 100 + p.processor_fee_usd


def build(cases: list[dict], days: int = 30, now: int | None = None) -> dict:
    now = now or int(time.time())
    since = now - days * 86400
    biz = [c for c in cases if c.get("channel") == "business" and int(c.get("created_at", 0)) >= since]
    out = {"days": days, "requests": len(biz), "handled_alone": 0, "waited_for_you": 0, "approved": 0, "declined": 0,
           "refunded_usd": 0.0, "kept_usd": 0.0, "fees_usd": 0.0, "returns": 0, "fraud": 0,
           "reasons": [], "products": [], "repeat": []}
    reason_count: Counter = Counter()
    reason_quote: dict[str, str] = {}
    products: Counter = Counter()
    claims: dict[str, list[dict]] = defaultdict(list)
    for c in biz:
        status, act, amt = c.get("status"), c.get("requested_action", ""), c.get("amount_usd")
        if status == "refused":            # someone the owner blocked: refused without asking the owner again
            out["handled_alone"] += 1
            out["declined"] += 1
            if act == "refund" and amt is not None:
                out["kept_usd"] += float(amt)
            out["fraud"] += 1
            continue
        if status == "allowed":
            out["handled_alone"] += 1
        else:
            out["waited_for_you"] += 1
        out["approved"] += status == "approved"
        out["declined"] += status == "blocked"
        if act == "refund" and amt is not None:
            if status in ("allowed", "approved"):
                out["refunded_usd"] += float(amt)
                out["fees_usd"] += _fee(float(amt))
            elif status == "blocked":
                out["kept_usd"] += float(amt)
        if any(f.get("rule") in FRAUD_RULES for f in c.get("findings") or []):
            out["fraud"] += 1
            continue
        if act in RETURN_ACTIONS:
            out["returns"] += 1
            r = reason_of(c.get("text", ""))
            reason_count[r] += 1
            reason_quote.setdefault(r, (c.get("text", "") or "").strip()[:140])
            for it in c.get("items") or []:
                if isinstance(it, dict) and it.get("name"):
                    products[str(it["name"])[:60]] += int(it.get("qty") or 1)
            who = c.get("customer_name") or c.get("customer_id")
            if who:
                claims[str(who)].append(c)
    total = sum(reason_count.values()) or 1
    out["reasons"] = [{"reason": r, "count": n, "share": round(100 * n / total), "quote": reason_quote.get(r, "")}
                      for r, n in reason_count.most_common()]
    out["products"] = [{"name": k, "count": v} for k, v in products.most_common(5)]
    out["repeat"] = sorted(({"who": k, "count": len(v), "usd": sum(float(x.get("amount_usd") or 0) for x in v)}
                            for k, v in claims.items() if len(v) >= 2), key=lambda x: -x["count"])[:5]
    for k in ("refunded_usd", "kept_usd", "fees_usd"):
        out[k] = round(out[k], 2)
    return out
