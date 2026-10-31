"""Web server: WhatsApp webhook, approval pages, and the pause switch. Standard library only.

    python -m valerius.server            # http://localhost:8080, this computer only
    PORT=9000 python -m valerius.server
    HOST=0.0.0.0 python -m valerius.server   # reachable from outside; needs WHATSAPP_APP_SECRET

Routes
    GET  /health
    GET  /webhook                Meta's verification handshake
    POST /webhook                incoming WhatsApp messages -> pipeline -> reply, case, alert
    GET  /case/<id>?<token>      approval page (signed link)
    POST /case/<id>/decide       approve or block (signed, single use)
    POST /agent/pause|resume     owner pause switch (signed, single use)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import act, intake, page, pipeline, whatsapp
from .config import SETTINGS
from .types import Channel, Message, Risk

STORE = act.Store()
MAX_BODY = 1_000_000
_SENDER = re.compile(r"\d{8,15}")

# Rate limits so nobody can run up model costs: per sender and overall, per minute.
PER_SENDER_PER_MIN = 10
GLOBAL_PER_MIN = 120
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def _allowed(sender: str, now: float | None = None) -> bool:
    now = time.monotonic() if now is None else now
    with _hits_lock:
        for key, cap in ((f"s:{sender}", PER_SENDER_PER_MIN), ("all", GLOBAL_PER_MIN)):
            q = _hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= cap:
                return False
        _hits[f"s:{sender}"].append(now)
        _hits["all"].append(now)
        return True


def _flat(qs: dict[str, list[str]]) -> dict[str, str]:
    return {k: v[0] for k, v in qs.items() if v}


_SEEN: deque = deque(maxlen=2000)   # message ids already handled (Meta re-sends if it doesn't hear back)
_SEEN_LOCK = threading.Lock()


def _first_time(message_id: str) -> bool:
    if not message_id:
        return True
    with _SEEN_LOCK:
        if message_id in _SEEN:
            return False
        _SEEN.append(message_id)
        return True


def handle_incoming(payload: dict, store: act.Store = STORE, use_models: bool | None = None) -> list[dict]:
    """Run each incoming message through the loop. Returns what was done, for logs and tests."""
    live = SETTINGS.server_live if use_models is None else use_models
    done = []
    for msg in whatsapp.parse_webhook(payload):
        if not _first_time(msg.conversation_id):
            done.append({"skipped": "already handled"})
            continue
        try:
            done.append(_handle_one(msg, store, live))
        except Exception as e:  # one bad message must not break the rest or make Meta retry
            sys.stderr.write(f"error handling message: {type(e).__name__}\n")
            done.append({"error": type(e).__name__})
    return done


def _handle_one(msg, store: act.Store, live: bool) -> dict:
    if not _SENDER.fullmatch(msg.sender or ""):
        return {"skipped": "sender is not a valid phone number"}
    if not _allowed(msg.sender):
        return {"skipped": "rate limited"}
    data, mime = None, ""
    if live and msg.kind in ("image", "audio") and msg.media_id:
        data, mime, err = whatsapp.download_media(msg.media_id)
        data = data or None  # failed download: the media stays unread, which holds
    result = pipeline.run(msg, use_models=live, media=data, media_mime=mime)
    case = act.open_case(result, store)
    reply = act.family_reply(result)
    sent = [whatsapp.send_text(msg.sender, reply)]
    contact = SETTINGS.trusted_contact
    if contact and contact != msg.sender and result.risk >= Risk.HIGH:
        alert = ("Valerius: a message sent to your family member looks like a scam "
                 f"({result.risk.name}). Details: {case.get('link', '')}")
        sent.append(whatsapp.send_text(contact, alert))
    failed = [x for x in sent if isinstance(x, dict) and x.get("error")]
    # Logs only (private to the operator). Never the message text or the sender's number.
    sys.stderr.write(f"case {case['id']}: {case['risk']} {case['status']} kind={msg.kind} "
                     f"reply={'FAILED ' + str(failed[0].get('error')) if failed else 'sent'}\n")
    if failed and case.get("link"):
        sys.stderr.write(f"  case page (reply could not be sent): {case['link']}\n")
    return {"case": case["id"], "status": case["status"], "risk": case["risk"], "sent": sent}


def act_keys() -> tuple[str, ...]:
    return page.TOKEN_KEYS


def handle_check(text: str, data: bytes, store: act.Store = STORE, live: bool | None = None) -> tuple[int, str]:
    """Run one web-forwarded message through the loop. Returns (status, html)."""
    live = SETTINGS.server_live if live is None else live
    kind, mime = ("text", "")
    if data:
        kind, mime = intake.sniff(data)
        if not kind:
            return 400, page.intake_form("That file type isn't supported. Use a JPEG, PNG or WEBP image, or a voice note.")
    if not text.strip() and not data:
        return 400, page.intake_form("Paste a message or add a file.")
    msg = Message(text=text[:intake.MAX_TEXT], channel=Channel.FAMILY, kind=kind, sender="web", forwarded=True)
    result = pipeline.run(msg, use_models=live, media=data or None, media_mime=mime)
    case = act.open_case(result, store)
    sys.stderr.write(f"case {case['id']}: {case['risk']} {case['status']} kind={kind} via=web\n")
    return 200, page.intake_result(result.risk.name, case["status"] == "held", act.family_reply(result), case.get("link", ""))


class Handler(BaseHTTPRequestHandler):
    server_version = "Valerius"

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:  # keep tokens out of logs
        sys.stderr.write(f"{self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}\n")

    def _body(self, limit: int = MAX_BODY) -> bytes | None:
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > limit:
            self.close_connection = True
            return None
        return self.rfile.read(n)

    # ---------------------------------------------------------------- GET
    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = _flat(parse_qs(u.query))
        if u.path == "/health":
            return self._send(200, "ok", "text/plain")
        if u.path == "/check" and SETTINGS.intake_code:
            return self._send(200, page.intake_form())
        if u.path == "/owner":
            if not act.dashboard_ok(q):
                return self._send(403, page.result_page("Link not valid", "This dashboard link is not valid or has expired."))
            cases = act.recent_cases(STORE)
            links = {c["id"]: act.link(act.sign(c["id"], "decide")) for c in cases if c.get("status") == "held"}
            agent = STORE.agent()
            from urllib.parse import urlencode
            counts = {c["customer_id"]: sum(1 for h in act.customer_history(STORE, c["customer_id"], exclude=c["id"])
                                            if h["is_claim"])
                      for c in cases if c.get("status") == "held" and c.get("customer_id")}
            tab_q = urlencode({k: q.get(k, "") for k in act_keys()})
            return self._send(200, page.owner_dashboard(cases, act.track_record(STORE), links, act.agent_token(),
                                                        bool(agent.get("paused")), q.get("view", "waiting"), tab_q, counts))
        if u.path == "/webhook":
            if q.get("hub.mode") == "subscribe" and SETTINGS.whatsapp_verify_token and \
                    hmac.compare_digest(q.get("hub.verify_token", ""), SETTINGS.whatsapp_verify_token):
                return self._send(200, q.get("hub.challenge", ""), "text/plain")
            return self._send(403, "forbidden", "text/plain")
        m = re.fullmatch(r"/case/([a-f0-9]{12})", u.path)
        if m:
            case = STORE.load_case(m.group(1))
            not_found = page.result_page("Link not valid", "This link is not valid or has expired.")
            if case is None or q.get("c") != case.get("id"):
                return self._send(404, not_found)
            if case.get("status") != "held":
                # Only someone holding a genuine link learns that a case was decided.
                if act.check_token(q, [], purpose="decide", check_used=False, check_expiry=False):
                    return self._send(404, not_found)
                return self._send(200, page.result_page(f"Already {case['status']}",
                                                        "This review has been decided. A signed receipt was recorded."))
            why = act.check_token(q, case.get("used_nonces", []), purpose="decide")
            if why:
                return self._send(403, page.result_page("Link not valid", why))
            agent = STORE.agent()
            history = act.customer_history(STORE, case.get("customer_id", ""), exclude=case.get("id", ""))
            return self._send(200, page.approval_page(case, q, act.track_record(STORE),
                                                      act.agent_token(), bool(agent.get("paused")), history))
        return self._send(404, "not found", "text/plain")

    def _check(self) -> None:
        raw = self._body(intake.MAX_UPLOAD)
        if raw is None:
            return self._send(413, page.intake_form("That file is too large (12 MB at most)."))
        if not _allowed("web"):  # counts wrong codes too, so the code can't be guessed quickly
            return self._send(429, page.intake_form("Too many checks right now. Try again in a minute."))
        form = intake.parse_form(raw, self.headers.get("Content-Type", ""))
        if not intake.code_ok(form.get("code", b"").decode("utf-8", "replace")):
            return self._send(403, page.intake_form("That access code isn't right."))
        status, html = handle_check(form.get("text", b"").decode("utf-8", "replace"), form.get("file", b""), STORE)
        return self._send(status, html)

    # ---------------------------------------------------------------- POST
    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path == "/check" and SETTINGS.intake_code:
            return self._check()
        raw = self._body()
        if raw is None:
            return self._send(413, "too large", "text/plain")
        if u.path == "/webhook":
            if not SETTINGS.whatsapp_app_secret and not _loopback(self.server.server_address[0]):
                return self._send(403, "webhook signature required", "text/plain")
            if SETTINGS.whatsapp_app_secret:
                sig = self.headers.get("X-Hub-Signature-256", "")
                good = "sha256=" + hmac.new(SETTINGS.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig, good):
                    return self._send(403, "bad signature", "text/plain")
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._send(400, "bad json", "text/plain")
            if isinstance(payload, dict):
                # Answer Meta right away; reading images and asking the models can take 15s+.
                threading.Thread(target=handle_incoming, args=(payload,), daemon=True).start()
            return self._send(200, "ok", "text/plain")  # always 200 so Meta does not retry storms
        form = _flat(parse_qs(raw.decode("utf-8", "replace")))
        m = re.fullmatch(r"/case/([a-f0-9]{12})/decide", u.path)
        if m:
            ok, info = act.decide(m.group(1), form, form.get("decision", ""), STORE)
            if ok:
                case = STORE.load_case(m.group(1))
                return self._send(200, page.receipt_page(case, act.last_receipt(STORE, m.group(1))))
            return self._send(403, page.result_page("Could not record that", info))
        m = re.fullmatch(r"/agent/(pause|resume)", u.path)
        if m:
            ok, info = act.switch_agent(m.group(1) == "pause", form, STORE)
            title = {"paused": "Agent paused", "resumed": "Agent resumed"}.get(info, "Could not change the agent")
            detail = ("Every action the agent asks for will be held until you resume it." if info == "paused"
                      else "The agent is running again under your normal rules." if info == "resumed" else info)
            return self._send(200 if ok else 403, page.result_page(title, detail))
        return self._send(404, "not found", "text/plain")


def _loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost")


def serve(port: int | None = None, host: str | None = None) -> ThreadingHTTPServer:
    """Listens on this computer only unless HOST says otherwise. Going online requires the app secret,
    so webhooks that don't come from Meta are refused."""
    port = port if port is not None else int(os.environ.get("PORT", "8080"))
    host = host or os.environ.get("HOST", "127.0.0.1")
    if not _loopback(host) and not SETTINGS.whatsapp_app_secret:
        raise SystemExit("Refusing to listen on a public address without WHATSAPP_APP_SECRET set in .env.")
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    srv = serve()
    print(f"Valerius listening on http://localhost:{srv.server_address[1]}  (models {'on' if SETTINGS.server_live else 'off'})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
