"""Core data types shared by every stage of the supervision loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class Channel:
    FAMILY = "family"      # a person forwards something to Valerius Family
    BUSINESS = "business"  # Shift Lead watches a business agent's conversation


@dataclass
class OrderRecord:
    """Synthetic order context a business agent would see. Never real customer data."""
    order_id: str = ""
    purchased_at: str = ""            # ISO date
    purchase_city: str = ""
    purchase_country: str = ""
    ship_country: str = ""
    return_country: str = ""
    delivered: bool | None = None
    receipt_on_file: bool | None = None
    photo_provided: bool | None = None
    quantity: int = 1
    refunds_last_90d: int = 0
    gift_card_loaded: bool | None = None
    gift_card_redeemed_city: str = ""
    gift_card_redeemed_at: str = ""  # ISO date
    minutes_since_purchase: int | None = None  # from the store's system when the request came in
    shipped: bool | None = None


@dataclass
class Message:
    text: str
    channel: str = Channel.FAMILY
    sender: str = ""
    conversation_id: str = ""
    kind: str = "text"                 # text | image | audio | document
    forwarded: bool = False
    media_id: str = ""
    requested_action: str = ""         # business side: refund | cancel | payment_change | account_change | ""
    amount_usd: float | None = None    # business side: amount of the requested action
    order: OrderRecord | None = None
    customer_id: str = ""              # business side: who is asking (a phone number or account id)
    items: list[dict] | None = None    # business side: [{"name", "price_usd", "qty"}] the request covers
    prior_claims: int | None = None    # business side: this customer's refund/reship claims in the window
    media_read: bool = False           # the image or voice note was actually read
    image_fields: dict | None = None   # what Muse Spark read off an image (fixed fields, untrusted)


@dataclass
class Evidence:
    """One piece of evidence: an exact quote from the message, or a record field."""
    quote: str = ""
    start: int = -1
    end: int = -1
    field: str = ""
    value: str = ""

    def label(self) -> str:
        if self.quote:
            return f'"{self.quote}"'
        return f"{self.field} = {self.value}"


@dataclass
class Finding:
    rule: str
    risk: Risk
    reason: str                        # plain language, shown to people
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Assessment:
    floor: Risk
    findings: list[Finding]
    incomplete: list[str] = field(default_factory=list)  # checks that could not run

    @property
    def needs_hold(self) -> bool:
        return self.floor >= Risk.HIGH or bool(self.incomplete)
