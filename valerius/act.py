"""Act: hold, signed approval links, decisions, pause switch, and chained receipts.

No privileged action (refund, payment change, account change) happens inside
the chat. A held case can only be approved or blocked through a signed,
expiring, single-use link opened outside the chat.

Every hold, decision, pause and resume writes a receipt. Receipts are chained:
each one stores the fingerprint of the one before, and each is signed. The
model verdicts are recorded separately from the rule results, so anyone can
rerun the rules and check the decision without trusting the model
(see scripts/verify_receipts.py).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .config import SETTINGS, state_dir
from .pipeline import Result
from .rules import implied_actions
from .textnorm import scrub_model_text
from .types import Risk

STATE = state_dir()              # gitignored runtime state
_LOCK = threading.Lock()
_EPHEMERAL_SECRET = secrets.token_hex(32)


def _secret() -> bytes:
    # Without SIGNING_SECRET, links and receipts are signed with a key that only lives
    # for this process. Safe, but links stop working after a restart.
    return (SETTINGS.signing_secret or _EPHEMERAL_SECRET).encode()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


# ------------------------------------------------------------------ store


class Store:
    """Tiny file-backed store: one JSON file per case, one append-only receipts file."""

    def __init__(self, root: Path = STATE):
        self.root = root
        (root / "cases").mkdir(parents=True, exist_ok=True)
        self.receipts_path = root / "receipts.jsonl"
        self.agent_path = root / "agent.json"

    # cases
    def save_case(self, case: dict) -> None:
        (self.root / "cases" / f"{case['id']}.json").write_text(json.dumps(case, indent=2), encoding="utf-8")

    def load_case(self, case_id: str) -> dict | None:
        if not case_id.replace("-", "").isalnum():
            return None
        p = self.root / "cases" / f"{case_id}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    # receipts
    def receipts(self) -> list[dict]:
        if not self.receipts_path.is_file():
            return []
        return [json.loads(x) for x in self.receipts_path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def append_receipt(self, body: dict) -> dict:
        with _LOCK:
            chain = self.receipts()
            prev = chain[-1]["hash"] if chain else "0" * 64
            body = {"seq": len(chain) + 1, "at": int(time.time()), **body, "prev_hash": prev}
            body["hash"] = sha256(_canon(body))
            body["sig"] = hmac.new(_secret(), body["hash"].encode(), hashlib.sha256).hexdigest()
            with self.receipts_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(body, ensure_ascii=False) + "\n")
            return body

    # agent switch
    def agent(self) -> dict:
        if self.agent_path.is_file():
            return json.loads(self.agent_path.read_text(encoding="utf-8"))
        return {"paused": False}

    def set_agent(self, state: dict) -> None:
        self.agent_path.write_text(json.dumps(state), encoding="utf-8")


# ------------------------------------------------------------------ links


def sign(case_id: str, purpose: str, ttl_s: int = 7200, now: int | None = None) -> dict[str, str]:
    exp = (now if now is not None else int(time.time())) + ttl_s
    nonce = secrets.token_hex(8)
    body = f"{case_id}|{purpose}|{exp}|{nonce}"
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return {"c": case_id, "p": purpose, "e": str(exp), "n": nonce, "s": sig}


def link(token: dict[str, str]) -> str:
    return f"{SETTINGS.approval_base_url}/case/{token['c']}?{urlencode(token)}"


def check_token(t: dict[str, str], used: list, now: int | None = None, purpose: str | None = None,
                check_used: bool = True, check_expiry: bool = True) -> str:
    """Return "" if valid, otherwise the reason it is not."""
    try:
        body = f"{t['c']}|{t['p']}|{t['e']}|{t['n']}"
        exp = int(t["e"])
    except (KeyError, ValueError):
        return "link is incomplete"
    good = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good, t.get("s", "")):
        return "link signature is not valid"
    if purpose is not None and t.get("p") != purpose:
        return "link is for a different purpose"
    if check_expiry and (now if now is not None else int(time.time())) > exp:
        return "link has expired"
    used_nonces = {u[0] if isinstance(u, (list, tuple)) else u for u in used}
    if check_used and t["n"] in used_nonces:
        return "link was already used"
    return ""


# ------------------------------------------------------------------ cases


def _rule_record(result: Result) -> dict:
    a = result.assessment
    return {"floor": a.floor.name,
            "fired": sorted(f"{f.rule}:{f.risk.name}" for f in a.findings),
            "incomplete": list(a.incomplete)}


def _model_record(result: Result) -> dict:
    out = {}
    for v in (result.first, result.second):
        if v is not None:
            out[v.source] = v.risk.name if v.ok else f"error: {v.error[:80]}"
    return out


def count_claims(store: Store, customer_id: str, window_days: int, now: int | None = None) -> int:
    """How many refund/reship claims this customer made in the window. Valerius keeps this count
    for the business, since most small businesses don't track it."""
    if not customer_id:
        return 0
    now = now if now is not None else int(time.time())
    since = now - window_days * 86400
    n = 0
    for p in (store.root / "cases").glob("*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if c.get("customer_id") == customer_id and c.get("is_claim") and since <= int(c.get("created_at", 0)) <= now:
            n += 1
    return n


def with_history(msg, store: Store, now: int | None = None):
    """Attach the customer's recent claim count before the rules run (business side only)."""
    from dataclasses import replace as _replace
    if msg.channel != "business" or not msg.customer_id:
        return msg
    return _replace(msg, prior_claims=count_claims(store, msg.customer_id, SETTINGS.policy.claim_window_days, now))


def open_case(result: Result, store: Store, now: int | None = None) -> dict:
    """Record what Valerius saw and decided. Held cases get a signed decision link."""
    msg = result.message
    agent = store.agent()
    paused = bool(agent.get("paused")) and msg.channel == "business"
    # When paused, anything that looks like an action is held, even if the agent left the action field blank.
    asks_for_action = bool(msg.requested_action) or bool(implied_actions(msg.text)) or msg.amount_usd is not None
    hold = result.hold or (paused and asks_for_action)
    case = {
        "id": uuid.uuid4().hex[:12],
        "created_at": now if now is not None else int(time.time()),
        "customer_id": msg.customer_id,
        "items": msg.items,
        "prior_claims": msg.prior_claims,
        "media_read": msg.media_read,
        "image_fields": msg.image_fields,
        "media": result.media,
        "is_claim": msg.channel == "business" and (msg.requested_action in ("refund", "reship")
                                                     or any(a in implied_actions(msg.text) for a in ("refund", "reship"))),
        "channel": msg.channel,
        "kind": msg.kind,
        "text": msg.text,  # redacted
        "requested_action": msg.requested_action,
        "amount_usd": msg.amount_usd,
        "order": asdict(msg.order) if msg.order else None,
        "risk": result.risk.name,
        "rules": _rule_record(result),
        "models": _model_record(result),
        "findings": [{"rule": f.rule, "risk": f.risk.name, "reason": f.reason,
                      "evidence": [asdict(e) for e in f.evidence]} for f in result.assessment.findings],
        "model_reasons": {v.source: {"reasons": [scrub_model_text(r) for r in v.reasons], "quotes": v.quotes,
                                     "advice": scrub_model_text(v.advice)}
                          for v in (result.first, result.second) if v is not None and v.ok},
        "unverified": result.unverified,
        "disagreement": result.disagreement,
        "paused_agent": paused,
        "status": "held" if hold else "allowed",
        "used_nonces": [],
        "decision": None,
    }
    if hold:
        tok = sign(case["id"], "decide")
        case["link"] = link(tok)
    store.save_case(case)
    store.append_receipt({"event": case["status"], "case_id": case["id"],
                          "message_sha256": sha256(case["text"]), "rules": case["rules"],
                          "models": case["models"], "paused_agent": paused, "actor": "valerius"})
    return case


def decide(case_id: str, token: dict[str, str], decision: str, store: Store, actor: str = "owner") -> tuple[bool, str]:
    if decision not in ("approve", "block"):
        return False, "unknown decision"
    with _LOCK:
        case = store.load_case(case_id)
        if case is None or token.get("c") != case_id or token.get("p") != "decide":
            return False, "case not found"
        if case["status"] != "held":
            return False, f"this case is already {case['status']}"
        why = check_token(token, case["used_nonces"], purpose="decide")
        if why:
            return False, why
        case["used_nonces"].append(token["n"])
        case["status"] = "approved" if decision == "approve" else "blocked"
        case["decision"] = {"by": actor, "at": int(time.time())}
        store.save_case(case)
    store.append_receipt({"event": case["status"], "case_id": case_id, "message_sha256": sha256(case["text"]),
                          "rules": case["rules"], "models": case["models"], "actor": actor})
    return True, case["status"]


def set_paused(paused: bool, store: Store, actor: str = "owner") -> None:
    """Pause or resume from the command line (the owner's own machine)."""
    state = store.agent()
    store.set_agent({**state, "paused": paused, "by": actor, "at": int(time.time())})
    store.append_receipt({"event": "paused" if paused else "resumed", "case_id": "", "actor": actor})


def track_record(store: Store) -> dict[str, int]:
    counts = {"held": 0, "approved": 0, "blocked": 0}
    for r in store.receipts():
        if r.get("event") in counts:
            counts[r["event"]] += 1
    return counts


# ------------------------------------------------------------------ messages back to people


def family_reply(result: Result) -> str:
    """Plain-language answer for a person who forwarded something to Valerius Family.

    Built only from fixed wording and the rules' own reasons. Model-written text never goes
    into a reply, so a crafted message can't make Valerius send someone a scammer's link."""
    reasons: list[str] = []
    for f in result.assessment.findings:
        if f.reason not in reasons:
            reasons.append(f.reason)
    why = "; ".join(reasons[:3]) or "it has signs of a scam"
    if result.unverified and result.risk < Risk.HIGH:
        return ("I couldn't fully check this one, so treat it as unsafe for now. Don't send money, codes or "
                "personal details until someone you trust has looked at it.")
    if result.risk >= Risk.HIGH:
        return ("This looks like a scam. Don't send money, gift cards or codes, and don't tap any links. "
                f"Why: {why}. If it claims to be family, call them on the number you already have. "
                "You can report scams at reportfraud.ftc.gov.")
    if result.risk == Risk.MEDIUM:
        return f"Be careful with this one. Why: {why}. Check with someone you trust before you act."
    return "I didn't find common scam signs. Still, never share codes or send money to someone you haven't verified."


def holding_message() -> str:
    """What the business agent tells the customer while the owner decides. Never improvised."""
    return "Thanks for your patience. A team member will confirm this request shortly."


def owner_alert(case: dict) -> str:
    return f"Valerius held a {case['risk']} request for your review: {case.get('link', '')} (link expires in 2 hours)"


def agent_token() -> dict[str, str]:
    return sign("agent", "agent")


def switch_agent(paused: bool, token: dict[str, str], store: Store, actor: str = "owner") -> tuple[bool, str]:
    """Pause or resume the agent with a signed, single-use owner token."""
    with _LOCK:
        state = store.agent()
        if token.get("c") != "agent" or token.get("p") != "agent":
            return False, "link is not an agent control link"
        why = check_token(token, state.get("used_nonces", []), purpose="agent")
        if why:
            return False, why
        now = int(time.time())
        # Keep every nonce until its link would have expired anyway, so no unexpired link can be replayed.
        kept = [u for u in state.get("used_nonces", []) if isinstance(u, list) and int(u[1]) >= now]
        kept.append([token["n"], int(token["e"])])
        store.set_agent({"paused": paused, "by": actor, "at": now, "used_nonces": kept})
    store.append_receipt({"event": "paused" if paused else "resumed", "case_id": "", "actor": actor})
    return True, "paused" if paused else "resumed"
