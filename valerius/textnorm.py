"""Clean incoming text before redaction and rules, so tricks can't hide from them.

- Unicode NFKC: full-width and styled letters become plain letters.
- Common look-alike letters (Cyrillic and Greek that look Latin) become Latin.
- Invisible characters (zero-width spaces, joiners, direction marks) are removed.
- Control characters are removed (newlines and tabs are kept).
- Very long messages are cut to a fixed length; a cut message is marked so it holds.
"""

from __future__ import annotations

import re
import unicodedata

MAX_CHARS = 4000

_INVISIBLE = re.compile("[­͏؜ᅟᅠ឴឵᠎​-‏‪-‮⁠-⁯ㅤ︀-️﻿]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Letters that look Latin but are not. Enough to stop the common tricks ("gіft cаrds").
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "ԁ": "d", "һ": "h", "ӏ": "l", "ԛ": "q", "ԝ": "w", "ɡ": "g",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S",
    "α": "a", "ο": "o", "ρ": "p", "ν": "v", "τ": "t", "ι": "i", "κ": "k",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})


def normalize(text: str) -> tuple[str, bool]:
    """Return (clean_text, was_truncated)."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _INVISIBLE.sub("", t)
    t = _CONTROL.sub("", t)
    t = t.translate(_CONFUSABLES)
    truncated = len(t) > MAX_CHARS
    if truncated:
        t = t[:MAX_CHARS]
    return t, truncated


_URL = re.compile(r"(?i)\b(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|xyz|top|click|info|ru|zip|link|live|icu|shop|cc|vip|buzz|io|co|me|app)\b\S*")
_LONG_NUMBER = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def scrub_model_text(text: str) -> str:
    """Model-written text is shown to people only after links and long numbers are removed,
    so a crafted message can't make Valerius repeat a scammer's link or phone number."""
    t = _URL.sub("[link removed]", text or "")
    return _LONG_NUMBER.sub("[number removed]", t)
