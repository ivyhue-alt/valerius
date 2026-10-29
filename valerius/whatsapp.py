"""WhatsApp Cloud API: parse incoming webhooks, and build fake ones for testing.

The fake payloads follow the documented webhook shape (Graph API v26.0), so the
same parser handles the fake webhook today and the real one once the test
number is unlocked. Status updates (sent, delivered, failed) are ignored here.
"""

from __future__ import annotations

import itertools
import time
from typing import Any

from .types import Channel, Message

_counter = itertools.count(1)


def parse_webhook(payload: dict[str, Any], channel: str = Channel.FAMILY) -> list[Message]:
    """Turn one webhook POST body into zero or more Messages."""
    out: list[Message] = []
    if payload.get("object") != "whatsapp_business_account":
        return out
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {})
            for m in value.get("messages", []) or []:
                if not isinstance(m, dict):
                    continue
                kind = str(m.get("type", "text"))
                body = m.get(kind) if isinstance(m.get(kind), dict) else {}
                text, media_id = "", ""
                if kind == "text":
                    text = body.get("body", "")
                elif kind in ("image", "document", "video", "sticker"):
                    text = body.get("caption", "")
                    media_id = body.get("id", "")
                elif kind == "audio":
                    media_id = body.get("id", "")
                if kind == "text" and not isinstance(m.get("text"), dict):
                    kind = "other"  # malformed: treat as unread, which holds
                text = text if isinstance(text, str) else ""
                media_id = media_id if isinstance(media_id, str) else ""
                ctx = m.get("context") if isinstance(m.get("context"), dict) else {}
                out.append(Message(
                    text=text,
                    channel=channel,
                    sender=str(m.get("from", "")),
                    conversation_id=str(m.get("id", "")),
                    kind=kind if kind in ("text", "audio", "image", "document", "video") else "other",
                    forwarded=bool(ctx.get("forwarded") or ctx.get("frequently_forwarded")),
                    media_id=media_id,
                ))
    return out


def fake_webhook(text: str = "", *, kind: str = "text", sender: str = "15550001111", forwarded: bool = True,
                 caption: str = "", name: str = "Test User") -> dict[str, Any]:
    """Build a webhook body shaped like a real WhatsApp Cloud API message event. Test numbers only."""
    n = next(_counter)
    msg: dict[str, Any] = {"from": sender, "id": f"wamid.FAKE{n:06d}", "timestamp": str(int(time.time())), "type": kind}
    if kind == "text":
        msg["text"] = {"body": text}
    elif kind in ("image", "document"):
        msg[kind] = {"id": f"MEDIA{n:06d}", "mime_type": "image/jpeg" if kind == "image" else "application/pdf",
                     "sha256": "fake", "caption": caption}
    elif kind == "audio":
        msg["audio"] = {"id": f"MEDIA{n:06d}", "mime_type": "audio/ogg; codecs=opus", "voice": True}
    if forwarded:
        msg["context"] = {"forwarded": True}
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_FAKE",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550000000", "phone_number_id": "PHONE_ID_FAKE"},
                    "contacts": [{"profile": {"name": name}, "wa_id": sender}],
                    "messages": [msg],
                },
            }],
        }],
    }


def download_media(media_id: str, max_bytes: int = 16_000_000) -> tuple[bytes, str, str]:
    """Fetch a WhatsApp image or voice note by its media id. Returns (data, mime, error)."""
    import json
    import re
    import urllib.error
    import urllib.request

    from .config import SETTINGS

    if not (SETTINGS.whatsapp_token and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", media_id or "")):
        return b"", "", "no token or bad media id"
    auth = {"Authorization": f"Bearer {SETTINGS.whatsapp_token}"}
    try:
        meta_req = urllib.request.Request(f"https://graph.facebook.com/{SETTINGS.graph_api_version}/{media_id}", headers=auth)
        with urllib.request.urlopen(meta_req, timeout=20) as r:
            meta = json.loads(r.read().decode())
        url = meta.get("url", "")
        if not url.startswith("https://"):
            return b"", "", "media url missing"
        with urllib.request.urlopen(urllib.request.Request(url, headers=auth), timeout=30) as r:
            data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            return b"", "", "media too large"
        return data, str(meta.get("mime_type", "")), ""
    except urllib.error.HTTPError as e:
        return b"", "", f"HTTP {e.code}"
    except Exception as e:
        return b"", "", type(e).__name__


def send_text(to: str, body: str) -> dict[str, Any]:
    """Send a free-form reply inside the 24-hour window. Without a token, writes to state/outbox.jsonl instead."""
    import json
    import urllib.error
    import urllib.request

    from .config import SETTINGS, state_dir

    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"preview_url": False, "body": body[:4000]}}
    if not (SETTINGS.whatsapp_token and SETTINGS.whatsapp_phone_number_id):
        out = state_dir() / "outbox.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"to": to, "body": body}) + "\n")
        return {"dry_run": True}
    url = f"https://graph.facebook.com/{SETTINGS.graph_api_version}/{SETTINGS.whatsapp_phone_number_id}/messages"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {SETTINGS.whatsapp_token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"error": type(e).__name__}
