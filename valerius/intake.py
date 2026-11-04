"""Web intake: forward a message, screenshot or voice note from a browser.

The same loop as WhatsApp (normalize, redact, rules, two model reviews, hold, signed link,
receipt). Only the way in is different. It exists because live WhatsApp delivery needs Meta
business verification and Live mode; the WhatsApp webhook stays built and tested.

Guards: an access code (INTAKE_CODE), rate limits, a size cap, and file types checked by
their first bytes, never by the name or the type the browser claims.
"""

from __future__ import annotations

import hmac
from email.parser import BytesParser
from email.policy import HTTP

from .config import SETTINGS

MAX_UPLOAD = 12_000_000
MAX_TEXT = 4000


def sniff(data: bytes) -> tuple[str, str]:
    """(kind, mime) from the file's first bytes, or ("", "") if it isn't an allowed type."""
    if data[:3] == b"\xff\xd8\xff":
        return "image", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", "image/webp"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio", "audio/wav"
    if data[:4] == b"OggS":
        return "audio", "audio/ogg"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio", "audio/mpeg"
    if data[4:8] == b"ftyp" and data[8:11] in (b"M4A", b"mp4", b"iso"):
        return "audio", "audio/mp4"
    return "", ""


def parse_form(body: bytes, content_type: str,
               fields: tuple[str, ...] = ("code", "text", "file")) -> dict[str, bytes]:
    """Parse a multipart/form-data body into {field: bytes}. Unknown fields are dropped."""
    if not content_type.lower().startswith("multipart/form-data"):
        return {}
    head = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin-1", "replace")
    try:
        msg = BytesParser(policy=HTTP).parsebytes(head + body)
    except Exception:
        return {}
    out: dict[str, bytes] = {}
    if not msg.is_multipart():
        return out
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name in fields and name not in out:
            out[name] = part.get_payload(decode=True) or b""
    return out


def code_ok(given: str) -> bool:
    expected = SETTINGS.intake_code
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


SHOP_FIELDS = ("code", "name", "order", "amount", "text", "file")


def money(raw: str) -> float | None:
    """'$1,200.50' -> 1200.5. Anything that isn't a sensible amount -> None."""
    t = raw.replace("$", "").replace(",", "").strip()
    try:
        v = round(float(t), 2)
    except ValueError:
        return None
    return v if 0 < v <= 100_000 else None
