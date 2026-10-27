"""Redaction: strip personal data before anything is stored or sent to a model.

Rules and models only ever see the redacted text, so evidence shown on the
approval page is redacted too. Amounts of money are kept: they are evidence.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_ACCOUNT = re.compile(
    r"(?i)\b(account|acct|routing|iban|sort code|account number)(\s*(?:number|no\.?|#)?\s*[:#]?\s*)([A-Z]{0,4}\d[\d -]{4,30}\d)")
_CODE = re.compile(r"(?i)\b(code|otp|pin|passcode)(\s*(?:is|:|=)?\s*)(\d{4,8})\b")
_PHONE = re.compile(r"(?<![\w$])\+?\d{0,3}[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _last4(s: str) -> str:
    digits = re.sub(r"\D", "", s)
    return digits[-4:]


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Return (redacted_text, counts by kind)."""
    counts: dict[str, int] = {}

    def bump(kind: str) -> None:
        counts[kind] = counts.get(kind, 0) + 1

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            bump("card")
            return f"[CARD ending {digits[-4:]}]"
        return m.group(0)

    def account(m: re.Match) -> str:
        bump("account")
        return f"{m.group(1)}{m.group(2)}[ACCOUNT ending {_last4(m.group(3))}]"

    def code(m: re.Match) -> str:
        bump("code")
        return f"{m.group(1)}{m.group(2)}[CODE]"

    def simple(kind: str, token: str):
        def f(m: re.Match) -> str:
            bump(kind)
            return token
        return f

    text = _EMAIL.sub(simple("email", "[EMAIL]"), text)
    text = _SSN.sub(simple("ssn", "[SSN]"), text)
    text = _CARD.sub(card, text)
    text = _ACCOUNT.sub(account, text)
    text = _CODE.sub(code, text)
    text = _PHONE.sub(simple("phone", "[PHONE]"), text)
    return text, counts
