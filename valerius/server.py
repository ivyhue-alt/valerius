"""Web server: WhatsApp webhook, approval pages, and the pause switch. Standard library only.

    python -m valerius.server            # http://localhost:8080
    PORT=9000 python -m valerius.server

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import act, page, pipeline, whatsapp
from .config import SETTINGS
from .types import Risk

STORE = act.Store()


def _flat(qs: dict[str, list[str]]) -> dict[str, str]:
    return {k: v[0] for k, v in qs.items() if v}


def handle_incoming(payload: dict, store: act.Store = STORE, use_models: bool | None = None) -> list[dict]:
    """Run each incoming message through the loop. Returns what was done, for logs and tests."""
    live = SETTINGS.server_live if use_models is None else use_models
    done = []
    for msg in whatsapp.parse_webhook(payload):
        result = pipeline.run(msg, use_models=live)
        case = act.open_case(result, store)
        reply = act.family_reply(result)
        sent = [whatsapp.send_text(msg.sender, reply)]
        contact = SETTINGS.trusted_contact
        if contact and contact != msg.sender and result.risk >= Risk.HIGH:
            alert = ("Valerius: a message sent to your family member looks like a scam "
                     f"({result.risk.name}). Details: {case.get('link', '')}")
            sent.append(whatsapp.send_text(contact, alert))
        done.append({"case": case["id"], "status": case["status"], "risk": case["risk"], "sent": sent})
    return done


class Handler(BaseHTTPRequestHandler):
    server_version = "Valerius"

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:  # keep tokens out of logs
        sys.stderr.write(f"{self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}\n")

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length", "0") or 0)
        return self.rfile.read(min(n, 1_000_000))

    # ---------------------------------------------------------------- GET
    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = _flat(parse_qs(u.query))
        if u.path == "/health":
            return self._send(200, "ok", "text/plain")
        if u.path == "/webhook":
            if q.get("hub.mode") == "subscribe" and SETTINGS.whatsapp_verify_token and \
                    hmac.compare_digest(q.get("hub.verify_token", ""), SETTINGS.whatsapp_verify_token):
                return self._send(200, q.get("hub.challenge", ""), "text/plain")
            return self._send(403, "forbidden", "text/plain")
        m = re.fullmatch(r"/case/([a-f0-9]{12})", u.path)
        if m:
            case = STORE.load_case(m.group(1))
            if case is None:
                return self._send(404, page.result_page("Not found", "This review does not exist."))
            if case["status"] == "held":
                why = act.check_token(q, case["used_nonces"])
                if why or q.get("c") != case["id"]:
                    return self._send(403, page.result_page("Link not valid", why or "This link is for a different review."))
            else:
                return self._send(200, page.result_page(f"Already {case['status']}",
                                                        "This review has been decided. A signed receipt was recorded."))
            agent = STORE.agent()
            return self._send(200, page.approval_page(case, q, act.track_record(STORE),
                                                      act.agent_token(), bool(agent.get("paused"))))
        return self._send(404, "not found", "text/plain")

    # ---------------------------------------------------------------- POST
    def do_POST(self) -> None:
        u = urlparse(self.path)
        raw = self._body()
        if u.path == "/webhook":
            if SETTINGS.whatsapp_app_secret:
                sig = self.headers.get("X-Hub-Signature-256", "")
                good = "sha256=" + hmac.new(SETTINGS.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig, good):
                    return self._send(403, "bad signature", "text/plain")
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._send(400, "bad json", "text/plain")
            handle_incoming(payload)
            return self._send(200, "ok", "text/plain")  # always 200 so Meta does not retry storms
        form = _flat(parse_qs(raw.decode("utf-8", "replace")))
        m = re.fullmatch(r"/case/([a-f0-9]{12})/decide", u.path)
        if m:
            ok, info = act.decide(m.group(1), form, form.get("decision", ""), STORE)
            title = {"approved": "Approved", "blocked": "Blocked"}.get(info, "Could not record that")
            detail = "Done. A signed receipt was recorded." if ok else info
            return self._send(200 if ok else 403, page.result_page(title, detail))
        m = re.fullmatch(r"/agent/(pause|resume)", u.path)
        if m:
            ok, info = act.switch_agent(m.group(1) == "pause", form, STORE)
            title = {"paused": "Agent paused", "resumed": "Agent resumed"}.get(info, "Could not change the agent")
            detail = ("Every action the agent asks for will be held until you resume it." if info == "paused"
                      else "The agent is running again under your normal rules." if info == "resumed" else info)
            return self._send(200 if ok else 403, page.result_page(title, detail))
        return self._send(404, "not found", "text/plain")


def serve(port: int | None = None) -> ThreadingHTTPServer:
    port = port if port is not None else int(os.environ.get("PORT", "8080"))
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


if __name__ == "__main__":
    srv = serve()
    print(f"Valerius listening on http://localhost:{srv.server_address[1]}  (models {'on' if SETTINGS.server_live else 'off'})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
