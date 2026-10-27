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
                kind = m.get("type", "text")
                text, media_id = "", ""
                if kind == "text":
                    text = m.get("text", {}).get("body", "")
                elif kind in ("image", "document", "video"):
                    media = m.get(kind, {})
                    text = media.get("caption", "")
                    media_id = media.get("id", "")
                elif kind == "audio":
                    media_id = m.get("audio", {}).get("id", "")
                ctx = m.get("context", {}) or {}
                out.append(Message(
                    text=text,
                    channel=channel,
                    sender=m.get("from", ""),
                    conversation_id=m.get("id", ""),
                    kind="audio" if kind == "audio" else ("image" if kind == "image" else ("document" if kind == "document" else "text")),
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
