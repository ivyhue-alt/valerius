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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class PolicyCard:
    """What the business owner lets the agent do alone. Shown on every approval page."""
    business_name: str = "Rosewood Bakery"   # fictional demo business
    refund_limit_usd: float = 50.0
    always_ask: tuple[str, ...] = ("cancel", "payment_change", "account_change")

    def lines(self) -> list[str]:
        return [
            f"Refunds up to ${self.refund_limit_usd:,.0f}: agent may approve alone.",
            "Anything over that, cancellations, payment changes and account changes: owner approves.",
        ]


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

    signing_secret: str = field(default_factory=lambda: _env("SIGNING_SECRET"))
    approval_base_url: str = field(default_factory=lambda: _env("APPROVAL_BASE_URL", "http://localhost:8080"))

    policy: PolicyCard = field(default_factory=PolicyCard)


SETTINGS = Settings()
