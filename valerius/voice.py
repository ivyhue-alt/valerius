"""How Valerius talks to people: short, plain, like a trusted shift lead texting the owner.

Built only from fixed phrases and facts already on record. Model-written text never goes in here,
so a crafted message can't put words in Valerius's mouth.
"""

from __future__ import annotations

from .config import SETTINGS


def _ev(f: dict, field: str) -> str:
    for e in f.get("evidence", []):
        if e.get("field") == field:
            return str(e.get("value", ""))
    return ""


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def reason(f: dict) -> str:
    """One finding, said the way a person would say it."""
    p = SETTINGS.policy
    r = f.get("rule", "")
    if r == "reseller_pattern":
        qty, refunds = _ev(f, "quantity"), _ev(f, "refunds_last_90d")
        if qty:
            return "big returns are your call"
        return f"they've had {refunds} refunds in the last 90 days" if refunds else "big returns are your call"
    if r == "repeat_claims":
        prior = _ev(f, "prior_claims")
        return (f"it would be their {_ordinal(int(prior) + 1)} claim in {p.claim_window_days} days"
                if prior.isdigit() else f"they've already made {p.max_claims} claims recently")
    words = {
        "order_over_limit": f"it's over your ${p.order_limit_usd:,.0f} limit",
        "item_over_limit": f"it's more than your ${p.refund_limit_usd:,.0f} per item",
        "refund_over_limit": f"it's more than your ${p.refund_limit_usd:,.0f} limit",
        "claim_without_proof": "there's no photo of the damage",
        "owner_impersonation": "someone in the chat says they're the owner or a manager",
        "amount_mismatch": "the chat asks for more than your agent wrote down",
        "unknown_action": "your agent tried something that isn't on your list",
        "delivery_contradiction": "they say it never came, but it shows as delivered",
        "gift_card_contradiction": "they say the card was empty, but it shows as loaded",
        "gift_card_no_receipt": "there's no receipt for the gift card",
        "gift_card_drained_elsewhere": "the card was spent in another city right after it was bought, so they may have been scammed",
        "cross_border_return": "it was bought in one country and is coming back from another",
        "pressure_story": "it's a hard-luck story asking you to bend the rules",
        "untraceable_payment": "they want gift cards, crypto or a wire, and that money can't come back",
        "impersonation_money": "they say they're family or someone official, and they want money",
        "impersonation": "they say they're someone you know",
        "secrecy": "they ask you to keep it secret",
        "urgent_money": "they're rushing you to pay",
        "threat": "they threaten arrest or legal trouble",
        "code_request": "they want a code or a password",
        "payment_redirect": "they say the payment details changed",
        "advance_fee": "they want a fee up front",
        "suspicious_link": "there's a link that doesn't look right",
        "prompt_injection": "the message tries to give your assistant orders",
        "image_qr_payment": "it wants you to pay by scanning a QR code",
        "image_untraceable_payment": "the picture asks for gift cards or crypto",
        "image_urgent_payment": "the picture rushes you to pay",
        "image_amount_mismatch": "the amount in the picture doesn't match",
    }
    if r == "owner_approval_required":
        act = _ev(f, "requested_action").replace("_", " ")
        return f"you asked to OK every {act} yourself" if act else "you asked to OK this kind of thing yourself"
    if r == "image_payment_redirect":
        last4 = _ev(f, "image.account_last4")
        return "the invoice says the bank details changed" + (f" (new account ending {last4})" if last4 else "")
    if r == "image_suspicious_link":
        link = _ev(f, "image.link")
        return "the picture has a link that doesn't look right" + (f": {link}" if link else "")
    return words.get(r, f.get("reason", ""))


def join(parts: list[str]) -> str:
    parts = [x for x in parts if x]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def reasons(case: dict, limit: int = 3) -> list[str]:
    strong = [f for f in case.get("findings", []) if f.get("risk") in ("HIGH", "CRITICAL")] or case.get("findings", [])
    rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    first = {"owner_impersonation": 0}            # someone posing as the owner matters more than the amount
    strong = sorted(strong, key=lambda f: (rank.get(f.get("risk", "LOW"), 3), first.get(f.get("rule", ""), 1)))
    out = []
    for f in strong:
        line = reason(f)
        if line and line not in out:
            out.append(line)
    if case.get("unverified") and len(out) < limit:
        out.append("I couldn't read everything that was sent")
    return out[:limit]


def who(case: dict) -> str:
    return case.get("customer_name") or "A customer"


def ask(case: dict) -> str:
    """What the customer wants, in one short sentence."""
    act, amt = case.get("requested_action", ""), case.get("amount_usd")
    order = (case.get("order") or {}).get("order_id", "")
    qty = int((case.get("order") or {}).get("quantity") or 1)
    on = f" on order {order}" if order else ""
    items = f" for {qty} items" if qty > 1 else ""
    money = f"${float(amt):,.2f}".replace(".00", "") if amt is not None else ""
    if act == "refund":
        return f"{who(case)} wants {money} back{items}{on}." if money else f"{who(case)} wants a refund{on}."
    if act == "reship":
        return f"{who(case)} wants a replacement sent{on}" + (f", worth {money}." if money else ".")
    if act == "cancel":
        return f"{who(case)} wants to cancel{on or ' their order'}."
    if act == "payment_change":
        return f"{who(case)} wants to change the card on their account."
    if act == "account_change":
        return f"{who(case)} wants to change their account details."
    return f"{who(case)} asked your agent for something you wanted to see first."


def opener(case: dict) -> str:
    if case.get("risk") == "CRITICAL":
        return "This one needs you now."
    return "Quick one." if case.get("channel") == "business" else "Heads up."


def sentences(parts: list[str]) -> str:
    """Each reason as its own short sentence, so nothing runs on."""
    return " ".join(x[:1].upper() + x[1:] + "." for x in parts if x)


def because(case: dict) -> str:
    r = reasons(case)
    if not r:
        return "I held it because your rules say you decide this one."
    extra = [f"{'Also' if i == 0 else 'And'}, {x}" for i, x in enumerate(r[1:])]
    return f"I held it because {r[0]}." + ("" if not extra else " " + sentences(extra))


def if_yes(case: dict, fee: float | None) -> str:
    act, amt = case.get("requested_action", ""), case.get("amount_usd")
    money = f"${float(amt):,.2f}".replace(".00", "") if amt is not None else ""
    fee_txt = f"${fee:,.2f}" if fee is not None else ""
    if case.get("channel") == "family":
        return "you've checked it yourself and it's fine. Nothing else happens."
    if act == "refund" and money:
        to = case.get("customer_name") or "them"
        return f"{money} goes back to {to}, and you're out about {fee_txt} in card fees." if fee_txt else f"{money} goes back to {to}."
    if act == "reship":
        return "a replacement goes out" + (f" ({money})" if money else "") + ", plus your shipping."
    if act == "cancel":
        return "the order is canceled" + (f", and if the payment already went through you're out about {fee_txt} in fees." if fee_txt else ".")
    if act == "payment_change":
        return "their card changes. If this is someone else, the next charge goes to them."
    if act == "account_change":
        return "their account details change, including where receipts and codes go."
    return "your agent goes ahead."


def if_no(case: dict) -> str:
    if case.get("channel") == "family":
        return "it stays marked as a scam. Nothing gets sent."
    name = who(case).lower() if who(case) == "A customer" else who(case)
    denied = {"refund": "the refund is denied. No money moves",
              "reship": "no replacement is sent",
              "cancel": "the order stays as it is",
              "payment_change": "the card on file stays the same",
              "account_change": "the account stays the same"}.get(case.get("requested_action", ""), "nothing happens")
    return f"{denied}, and {name} gets a note right away."


def bar_button(case: dict) -> str:
    return f"Deny and block {who(case)}" if case.get("customer_name") else "Deny and block this person"


def if_bar(case: dict) -> str:
    name = who(case)
    return (f"the request is denied, and {name} can't get refunds, replacements or account changes through your agent "
            "until you unblock them. They're told why, in the chat, and how to contest it.")


def barred_note(case: dict) -> str:
    """What a blocked person hears, in the chat: the decision, the reason, what it means, and how to contest it."""
    from .config import SETTINGS
    p = SETTINGS.policy
    name = case.get("customer_name") or "there"
    return (f"Hi {name}, we're not able to issue this refund. This request broke our store policy because it claimed to "
            f"come from our owner or staff, so this account can no longer request refunds or order changes through "
            f"this chat. If you think this is a mistake, email us at {p.contact_email}.\n\n{p.business_name}")


def customer_note(case: dict) -> str:
    """What the customer hears the moment the owner decides. Plain, no thank-yous, no filler."""
    if case.get("channel") != "business":
        return ""
    name = case.get("customer_name") or "there"
    act, amt = case.get("requested_action", ""), case.get("amount_usd")
    money = f"${float(amt):,.2f}".replace(".00", "") if amt is not None else ""
    approved = case.get("status") == "approved"
    # Held by the owner's rules means a yes is an exception, and the customer should know it's a one-time thing.
    exception = bool(case.get("findings"))
    if act == "refund":
        if approved and exception:
            return (f"Hi {name}, I've approved your {money + ' ' if money else ''}refund as a one-time courtesy, since it's "
                    "outside our usual return policy. It can take 5 to 10 business days to show up, depending on your bank.")
        if approved:
            return (f"Hi {name}, your {money + ' ' if money else ''}refund is on its way. "
                    "It can take 5 to 10 business days to show up, depending on your bank.")
        return (f"Hi {name}, I wish I could take care of this one, but a {money + ' ' if money else ''}refund isn't "
                "something we can do this time. If you have questions about it, just reply here and we'll talk it through.")
    if act == "reship":
        if approved and exception:
            return (f"Hi {name}, I'm sending a replacement as a one-time courtesy, since it's outside our usual policy. "
                    "You'll get tracking as soon as it ships.")
        return (f"Hi {name}, a replacement is on its way. You'll get tracking as soon as it ships." if approved else
                f"Hi {name}, we're not able to send a replacement for this order. Reply here if you'd like to talk it through.")
    if act == "cancel":
        if approved and exception:
            return f"Hi {name}, I've canceled your order as a one-time courtesy, since it's past our usual cancel window."
        return (f"Hi {name}, your order is canceled." if approved else
                f"Hi {name}, this order can't be canceled at this point. Reply here and we'll figure out the next step together.")
    if act in ("payment_change", "account_change"):
        return (f"Hi {name}, your account is updated." if approved else
                f"Hi {name}, we couldn't make that change to your account. If it was you, reply here and we'll help.")
    return (f"Hi {name}, you're all set." if approved else
            f"Hi {name}, we can't do that one. Reply here if you have questions.")


def buttons(case: dict) -> tuple[str, str]:
    act = case.get("requested_action", "")
    if case.get("channel") == "family":
        return "It's fine", "It's a scam"
    return {"refund": ("Send the refund", "Don't refund"), "reship": ("Send a replacement", "Don't send it"),
            "cancel": ("Cancel the order", "Keep the order"), "payment_change": ("Change the card", "Leave it"),
            "account_change": ("Change the details", "Leave it")}.get(act, ("Go ahead", "Stop it"))


def done(case: dict) -> str:
    """The receipt line, in the same words as the button that was pressed."""
    yes, no = buttons(case)
    said = yes if case.get("status") == "approved" else bar_button(case) if case.get("barred_person") else no
    return f"You chose: {said}."



def refused_note(case: dict) -> str:
    """Later requests from someone the owner blocked: same answer every time, with the way to contest it."""
    from .config import SETTINGS
    p = SETTINGS.policy
    name = case.get("customer_name") or "there"
    return (f"Hi {name}, refunds and order changes for this account can't be handled through this chat. If you think "
            f"this is a mistake, email us at {p.contact_email}.\n\n{p.business_name}")
