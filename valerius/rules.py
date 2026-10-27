"""Tier 1: deterministic rules.

Rules set a risk floor. Later stages (Muse Spark, the second pass) may raise
risk above the floor but can never lower it. Every finding carries evidence:
an exact quote from the (redacted) message or a field from the order record,
so the approval page can show why something was held.

If a check needs information that is missing (for example, no order record
for a refund), it is reported as incomplete, and incomplete means hold.
"""

from __future__ import annotations

import re
from datetime import date

from .config import SETTINGS, PolicyCard
from .types import Assessment, Channel, Evidence, Finding, Message, Risk

# ---------------------------------------------------------------- helpers


def _search(patterns: list[str], text: str) -> Evidence | None:
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return Evidence(quote=m.group(0), start=m.start(), end=m.end())
    return None


def _rec(field_name: str, value) -> Evidence:
    return Evidence(field=field_name, value=str(value))


_AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?|\b(\d+(?:,\d{3})*)\s?(?:dollars|usd)\b", re.I)


def amounts(text: str) -> list[float]:
    vals = []
    for m in _AMOUNT.finditer(text):
        raw = (m.group(1) or m.group(2) or "").replace(",", "")
        if raw:
            vals.append(float(raw))
    return vals


def _days_between(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)
    except ValueError:
        return None


# ---------------------------------------------------------------- vocab

MONEY_ASK = [r"\bsend (?:me |us )?(?:the )?(?:money|cash|funds|\$)", r"\bwire\b", r"\bzelle\b", r"\bvenmo\b",
             r"\bcash ?app\b", r"\bpaypal\b", r"\btransfer\b", r"\bpay (?:me|us|the|this|a|your)\b",
             r"\bneed (?:some )?(?:money|cash|\$\s?[\d,]+(?:\.\d{2})?)", r"\blend me\b", r"\bbail\b"]
UNTRACEABLE = [r"\bgift ?cards?\b", r"\b(?:itunes|apple|google play|steam|amazon) cards?\b", r"\bbitcoin\b",
               r"\bcrypto\b", r"\busdt\b", r"\bwestern union\b", r"\bmoneygram\b", r"\bcrypto atm\b",
               r"\bcourier\b.{0,30}\bcash\b", r"\bcash\b.{0,30}\bcourier\b"]
URGENCY = [r"\burgent(?:ly)?\b", r"\bright now\b", r"\bimmediately\b", r"\basap\b", r"\bact now\b",
           r"\bwithin (?:\d+|one|two|an?) (?:hours?|minutes?)\b", r"\bbefore (?:it'?s too late|midnight|tonight)\b",
           r"\bfinal (?:notice|warning)\b", r"\btoday only\b", r"\b(?:will be|has been) (?:suspended|locked|closed|frozen)\b",
           r"\bsuspended\b", r"\blast chance\b"]
IMPERSONATION = [r"\b(?:it'?s|this is) (?:me|your) (?:grandson|granddaughter|son|daughter|nephew|niece|grandchild|mom|dad)\b",
                 r"\b(?:grandma|grandpa|nana|mom|mum|dad|auntie|uncle)\b[ ,!.]*(?:it'?s|this is) me\b",
                 r"\b(?:new|different) (?:phone|number)\b", r"\bphone (?:broke|is broken|got stolen)\b",
                 r"\b(?:irs|social security|medicare|sheriff'?s? (?:office|department)|police department)\b",
                 r"\b(?:bank'?s? )?fraud (?:department|team)\b", r"\btoll (?:authority|services?|notice)\b",
                 r"\b(?:usps|fedex|ups|dhl)\b"]
SECRECY = [r"\bdon'?t tell\b", r"\bkeep (?:this|it) (?:a )?secret\b", r"\bbetween (?:us|you and me)\b",
           r"\bdon'?t (?:call|tell) (?:mom|dad|anyone|anybody)\b", r"\bdo not tell\b"]
CODE_ASK = [r"\[CODE\]", r"\b(?:send|share|give|tell|read) (?:me |us )?(?:the |your |that )?(?:\d-digit )?(?:verification |security |one[- ]time |login )?(?:code|pin|password|passcode)\b",
            r"\bverification code\b", r"\bone[- ]time (?:code|password|passcode)\b"]
REDIRECT = [r"\b(?:bank|account|payment|banking) (?:details|info(?:rmation)?|number) (?:have |has )?(?:changed|been updated)\b",
            r"\bnew (?:bank|account|banking) (?:details|number|info)\b",
            r"\bpay (?:to )?(?:this|the new|our new) account\b", r"\bupdate(?:d)? (?:our|the|my) (?:bank|payment|payout) (?:details|account)\b"]
ADVANCE_FEE = [r"\b(?:processing|release|customs|handling|redelivery|delivery|unlock|activation|clearance) fee\b",
               r"\bsmall fee\b", r"\bpay (?:a|the)(?: \$?[\d.,]+)? fee\b", r"\bto (?:claim|release|unlock) (?:your|the)\b"]
THREAT = [r"\barrest(?:ed)?\b", r"\bwarrant\b", r"\blawsuit\b", r"\bjail\b", r"\blegal action\b", r"\bcourt\b"]
INJECTION = [r"\bignore (?:all |your |the |any )?(?:previous |prior |above )?(?:instructions|rules|policy)\b",
             r"\byou are now\b", r"\bsystem prompt\b", r"\bdeveloper mode\b",
             r"\b(?:mark|approve) (?:this|it) (?:as )?(?:safe|approved|ok)\b", r"\boverride (?:the )?(?:policy|rules|limit)\b",
             r"\bas an ai\b.{0,40}\bmust\b"]
LINK = re.compile(r"\bhttps?://[^\s]+|\b(?:[a-z0-9-]+\.)+(?:xyz|top|click|info|ru|zip|link|live|icu|shop|cc|vip|buzz)\b(?:/\S*)?|\b(?:bit\.ly|tinyurl\.com|t\.co|rb\.gy|cutt\.ly)/\S+", re.I)
OWNER_CLAIM = [r"\b(?:i'?m|i am|this is) the (?:owner|manager|boss|ceo)\b", r"\bon behalf of the owner\b"]
DEFECT_CLAIM = [r"\b(?:defect(?:ive)?|damaged|broken|ripped|torn|stained|faulty|doesn'?t work|stopped working)\b"]
NOT_ARRIVED = [r"\bnever (?:arrived|came|got (?:it|my order|the package))\b", r"\b(?:didn'?t|did not) (?:arrive|receive|get)\b",
               r"\bnot (?:delivered|received)\b"]
GIFT_CARD_DISPUTE = [r"\b(?:gift ?card|gc)\b.{0,60}\b(?:no|zero|empty|missing|never (?:loaded|added)|wasn'?t loaded|not loaded|\$0)\b",
                     r"\b(?:balance|funds)\b.{0,40}\b(?:never|not|wasn'?t)\b.{0,20}\b(?:loaded|added|there)\b"]
PRESSURE_STORY = [r"\b(?:my (?:mom|mother|dad|father|kid|child|son|daughter|wife|husband) (?:is|was) (?:sick|in the hospital|dying))\b",
                  r"\bfuneral\b", r"\blost my job\b", r"\bsingle (?:mom|mother|dad|parent)\b", r"\bi'?m begging\b",
                  r"\bplease,? i really need\b", r"\bhospital\b", r"\bevicted\b"]
EXCEPTION_ASK = [r"\bdiscount\b", r"\bexception\b", r"\bjust this once\b", r"\bwaive\b", r"\bfree replacement\b",
                 r"\bfull refund\b", r"\bkeep (?:it|the item) and\b", r"\bcredit (?:my|the) account\b"]
REFUND_WORDS = [r"\brefund\b", r"\bmoney back\b", r"\breimburse\b", r"\bchargeback\b", r"\breturn\b"]


# ---------------------------------------------------------------- family / shared rules


def _shared_rules(msg: Message) -> list[Finding]:
    t = msg.text
    out: list[Finding] = []
    money = _search(MONEY_ASK, t)
    amts = amounts(t)
    untr = _search(UNTRACEABLE, t)
    urg = _search(URGENCY, t)
    imp = _search(IMPERSONATION, t)

    if (e := _search(INJECTION, t)):
        out.append(Finding("prompt_injection", Risk.HIGH, "tries to give the assistant orders", [e]))
    if (e := _search(CODE_ASK, t)):
        out.append(Finding("code_request", Risk.CRITICAL, "asks for a code, PIN or password", [e]))
    if (e := _search(REDIRECT, t)):
        out.append(Finding("payment_redirect", Risk.CRITICAL, "says payment details changed", [e]))
    if untr and (money or urg or amts):
        risk = Risk.CRITICAL if urg else Risk.HIGH
        ev = [untr] + ([urg] if urg else [])
        out.append(Finding("untraceable_payment", risk, "asks for gift cards, crypto or wire, which can't be reversed", ev))
    if imp and (money or untr or amts):
        out.append(Finding("impersonation_money", Risk.HIGH, "claims to be someone you know or an official, and asks for money",
                           [imp] + ([money] if money else [])))
    elif imp:
        out.append(Finding("impersonation", Risk.MEDIUM, "claims to be someone you know or an official", [imp]))
    if urg and (money or amts) and not untr:
        out.append(Finding("urgent_money", Risk.HIGH, "pressure to pay fast", [urg] + ([money] if money else [])))
    if (e := _search(SECRECY, t)):
        out.append(Finding("secrecy", Risk.HIGH if (money or untr or amts) else Risk.MEDIUM, "asks you to keep it secret", [e]))
    if (e := _search(ADVANCE_FEE, t)):
        out.append(Finding("advance_fee", Risk.HIGH, "asks for a fee before you get something", [e]))
    if (e := _search(THREAT, t)) and (money or untr or amts or urg):
        out.append(Finding("threat", Risk.HIGH, "threatens arrest or legal trouble to get money", [e]))
    if (m := LINK.search(t)):
        e = Evidence(quote=m.group(0), start=m.start(), end=m.end())
        risk = Risk.HIGH if (urg or money or untr) else Risk.MEDIUM
        out.append(Finding("suspicious_link", risk, "contains a link you should not open", [e]))
    return out


# ---------------------------------------------------------------- business rules (Shift Lead)


def _business_rules(msg: Message, policy: PolicyCard) -> tuple[list[Finding], list[str]]:
    t = msg.text
    out: list[Finding] = []
    incomplete: list[str] = []
    o = msg.order
    action = msg.requested_action
    amt = msg.amount_usd if msg.amount_usd is not None else (max(amounts(t)) if amounts(t) else None)

    if action in policy.always_ask:
        out.append(Finding("owner_approval_required", Risk.HIGH,
                           f"the owner's policy says a {action.replace('_', ' ')} always needs approval",
                           [_rec("requested_action", action)]))
    if action == "refund" or _search(REFUND_WORDS, t):
        if amt is None:
            if action == "refund":
                incomplete.append("refund amount unknown")
        elif amt > policy.refund_limit_usd:
            out.append(Finding("refund_over_limit", Risk.HIGH,
                               f"refund of ${amt:,.0f} is over the ${policy.refund_limit_usd:,.0f} the agent may approve alone",
                               [_rec("amount_usd", f"{amt:,.2f}"), _rec("policy.refund_limit_usd", f"{policy.refund_limit_usd:,.2f}")]))
        if action == "refund" and o is None:
            incomplete.append("no order record to check the refund against")

    if (e := _search(OWNER_CLAIM, t)):
        out.append(Finding("owner_impersonation", Risk.HIGH, "a customer claims to be the owner or a manager", [e]))

    defect = _search(DEFECT_CLAIM, t)
    if defect:
        if o is None or o.photo_provided is None:
            incomplete.append("defect claimed but no record of whether a photo was provided")
        elif not o.photo_provided:
            out.append(Finding("claim_without_proof", Risk.HIGH, "claims a defect but no photo or proof was provided",
                               [defect, _rec("photo_provided", False)]))

    not_arrived = _search(NOT_ARRIVED, t)
    if not_arrived:
        if o is None or o.delivered is None:
            incomplete.append("says it never arrived but delivery status is unknown")
        elif o.delivered:
            out.append(Finding("delivery_contradiction", Risk.HIGH, "says it never arrived, but the record shows it was delivered",
                               [not_arrived, _rec("delivered", True)]))

    gc = _search(GIFT_CARD_DISPUTE, t)
    if gc:
        if o is None or (o.receipt_on_file is None and o.gift_card_loaded is None):
            incomplete.append("gift card dispute but no purchase or load record")
        else:
            if o.receipt_on_file is False:
                out.append(Finding("gift_card_no_receipt", Risk.HIGH, "gift card dispute with no proof of purchase",
                                   [gc, _rec("receipt_on_file", False)]))
            if o.gift_card_loaded:
                out.append(Finding("gift_card_contradiction", Risk.HIGH, "says the card was never loaded, but the record shows it was",
                                   [gc, _rec("gift_card_loaded", True)]))

    if o is not None and o.gift_card_redeemed_city and o.purchase_city and \
            o.gift_card_redeemed_city.lower() != o.purchase_city.lower():
        gap = _days_between(o.purchased_at, o.gift_card_redeemed_at) if o.gift_card_redeemed_at else None
        if gap is not None and gap <= 2:
            out.append(Finding("gift_card_drained_elsewhere", Risk.HIGH,
                               "gift card was redeemed in another city right after purchase; the buyer may be a scam victim",
                               [_rec("purchase_city", o.purchase_city), _rec("gift_card_redeemed_city", o.gift_card_redeemed_city),
                                _rec("days_between", gap)]))

    if o is not None and o.return_country and o.purchase_country and o.return_country.lower() != o.purchase_country.lower():
        out.append(Finding("cross_border_return", Risk.HIGH, "item bought in one country is being returned in another",
                           [_rec("purchase_country", o.purchase_country), _rec("return_country", o.return_country)]))

    if o is not None and (o.quantity >= 5 or o.refunds_last_90d >= 3):
        ev = []
        if o.quantity >= 5:
            ev.append(_rec("quantity", o.quantity))
        if o.refunds_last_90d >= 3:
            ev.append(_rec("refunds_last_90d", o.refunds_last_90d))
        out.append(Finding("reseller_pattern", Risk.MEDIUM, "bulk buying or repeated refunds, a reseller pattern", ev))

    story = _search(PRESSURE_STORY, t)
    ask = _search(EXCEPTION_ASK, t)
    if story and ask:
        out.append(Finding("pressure_story", Risk.MEDIUM,
                           "a hardship story used to ask for an exception; be kind, but follow the policy", [story, ask]))
    return out, incomplete


# ---------------------------------------------------------------- entry point


def check(msg: Message, policy: PolicyCard | None = None) -> Assessment:
    """Run every rule. msg.text must already be redacted."""
    policy = policy or SETTINGS.policy
    findings = _shared_rules(msg)
    incomplete: list[str] = []
    if msg.channel == Channel.BUSINESS:
        biz, incomplete = _business_rules(msg, policy)
        findings += biz
    if msg.kind in ("image", "audio", "document"):
        # A caption is not the content. Until SAM or transcription has read the media, it is unverified.
        incomplete.append(f"{msg.kind} not yet read")
    floor = max((f.risk for f in findings), default=Risk.LOW)
    return Assessment(floor=floor, findings=findings, incomplete=incomplete)


def raise_only(floor: Risk, proposed: Risk) -> Risk:
    """The one rule: a later stage can raise risk above the rule floor, never lower it."""
    return max(floor, proposed)
