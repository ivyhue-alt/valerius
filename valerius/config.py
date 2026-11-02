"""Settings from environment variables or a local .env file. No secrets live in code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    """Read KEY=value lines into os.environ without overriding variables already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]  # only a matching pair of quotes is removed
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()  # inline comment
        os.environ.setdefault(key.strip(), value)


load_env()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class PolicyCard:
    """What the business owner lets the agent do alone. Shown on every approval page."""
    business_name: str = "Rosewood Bakery"   # fictional demo business
    refund_limit_usd: float = 50.0           # per item, for refunds and reships
    order_limit_usd: float = 150.0           # total per request
    max_claims: int = 2                      # refund/reship claims per customer before the owner decides
    claim_window_days: int = 90
    always_ask: tuple[str, ...] = ("cancel", "payment_change", "account_change")
    processor_fee_pct: float = 2.9           # the owner's card processor fee, kept by the processor on a refund (estimate)
    processor_fee_usd: float = 0.30
    history_days: int = 730                  # how far back Valerius shows a customer's claims (limits use claim_window_days)
    free_cancel_minutes: int = 30            # payment usually settles within this; after it, a cancel costs the business fees
    timezone: str = "America/New_York"
    open_hour: int = 9                       # business hours, local time; holds outside them wait for opening
    close_hour: int = 21
    after_hours: str = "queue"               # "queue": one summary at opening; "notify": ping the owner anyway

    def lines(self) -> list[str]:
        return [
            f"Refunds and reships up to ${self.refund_limit_usd:,.0f} per item and ${self.order_limit_usd:,.0f} per request: agent may approve alone.",
            f"A customer's claim number {self.max_claims + 1} or more within {self.claim_window_days} days: owner decides.",
            f"Cancel before the payment is taken (or within {self.free_cancel_minutes} minutes if that's unknown) and before shipping: agent may do it, any time of day.",
            "Damage claims without a photo, later cancellations, payment changes and account changes: owner approves.",
            (f"Outside {self._hour(self.open_hour)} to {self._hour(self.close_hour)}, holds wait quietly and you get one "
             f"summary when you open." if self.after_hours == "queue" else
             f"Outside {self._hour(self.open_hour)} to {self._hour(self.close_hour)}, you still get a message right away."),
        ]

    @staticmethod
    def _hour(h: int) -> str:
        return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"


def state_dir() -> Path:
    """Where cases and receipts live. VALERIUS_STATE moves it (Modal mounts a volume there)."""
    return Path(os.environ.get("VALERIUS_STATE") or ROOT / "state")


@dataclass(frozen=True)
class Settings:
    model_api_key: str = field(default_factory=lambda: _env("MODEL_API_KEY"))
    model_base_url: str = field(default_factory=lambda: _env("MODEL_BASE_URL", "https://api.meta.ai/v1"))
    judge_model: str = field(default_factory=lambda: _env("JUDGE_MODEL", "muse-spark-1.3"))

    baseten_api_key: str = field(default_factory=lambda: _env("BASETEN_API_KEY"))
    baseten_base_url: str = field(default_factory=lambda: _env("BASETEN_BASE_URL", "https://inference.baseten.co/v1"))
    second_pass_model: str = field(default_factory=lambda: _env("SECOND_PASS_MODEL", "meta-models/muse-spark-open-1026"))

    whatsapp_token: str = field(default_factory=lambda: _env("WHATSAPP_TOKEN"))
    whatsapp_phone_number_id: str = field(default_factory=lambda: _env("WHATSAPP_PHONE_NUMBER_ID"))
    whatsapp_verify_token: str = field(default_factory=lambda: _env("WHATSAPP_VERIFY_TOKEN"))
    graph_api_version: str = field(default_factory=lambda: _env("GRAPH_API_VERSION", "v26.0"))
    whatsapp_app_secret: str = field(default_factory=lambda: _env("WHATSAPP_APP_SECRET"))
    trusted_contact: str = field(default_factory=lambda: _env("TRUSTED_CONTACT"))  # opted-in family number
    intake_code: str = field(default_factory=lambda: _env("INTAKE_CODE"))  # access code for the web intake page
    # Dashboard links made before this Unix time stop working (to cancel a link that leaked)
    dashboard_not_before: int = field(default_factory=lambda: int(_env("DASHBOARD_NOT_BEFORE", "0") or 0))
    server_live: bool = field(default_factory=lambda: _env("SERVER_LIVE", "1") == "1")  # call models from the server

    signing_secret: str = field(default_factory=lambda: _env("SIGNING_SECRET"))
    approval_base_url: str = field(default_factory=lambda: _env("APPROVAL_BASE_URL", "http://localhost:8080"))

    policy: PolicyCard = field(default_factory=PolicyCard)


SETTINGS = Settings()
