"""Check every receipt without trusting any model.

    python scripts/verify_receipts.py

1. The chain: each receipt's fingerprint is correct and points at the one before.
   Editing, deleting or reordering any receipt breaks it.
2. The signature: each receipt was signed with SIGNING_SECRET.
3. The rules: for every case, the stored (redacted) message still has the same
   fingerprint, and rerunning the deterministic rules gives the same result.
   Model verdicts are recorded but never needed to check a decision.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius import act, rules  # noqa: E402
from valerius.config import SETTINGS  # noqa: E402
from valerius.types import Message, OrderRecord  # noqa: E402


def verify(store: act.Store, check_sig: bool = True) -> list[str]:
    problems: list[str] = []
    prev = "0" * 64
    for i, r in enumerate(store.receipts(), 1):
        body = {k: v for k, v in r.items() if k not in ("hash", "sig")}
        if r.get("seq") != i:
            problems.append(f"receipt {i}: sequence number is {r.get('seq')}")
        if r.get("prev_hash") != prev:
            problems.append(f"receipt {i}: chain broken (does not point at receipt {i - 1})")
        if act.sha256(act._canon(body)) != r.get("hash"):
            problems.append(f"receipt {i}: contents were changed after it was written")
        if check_sig:
            good = hmac.new(act._secret(), r.get("hash", "").encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(good, r.get("sig", "")):
                problems.append(f"receipt {i}: signature does not match")
        prev = r.get("hash", "")

        if r.get("case_id") and r.get("rules"):
            case = store.load_case(r["case_id"])
            if case is None:
                problems.append(f"receipt {i}: case {r['case_id']} is missing")
                continue
            if act.sha256(case["text"]) != r.get("message_sha256"):
                problems.append(f"receipt {i}: stored message does not match its fingerprint")
            order = OrderRecord(**case["order"]) if case.get("order") else None
            msg = Message(text=case["text"], channel=case["channel"], kind=case.get("kind", "text"),
                          requested_action=case.get("requested_action", ""), amount_usd=case.get("amount_usd"), order=order)
            a = rules.check(msg)
            fired = sorted(f"{f.rule}:{f.risk.name}" for f in a.findings)
            if a.floor.name != r["rules"]["floor"] or fired != r["rules"]["fired"]:
                problems.append(f"receipt {i}: rerunning the rules gives a different result")
    return problems


def main() -> int:
    store = act.Store()
    n = len(store.receipts())
    if not SETTINGS.signing_secret:
        print("Note: SIGNING_SECRET is not set, so signatures can't be checked across restarts. Checking chain and rules only.")
    problems = verify(store, check_sig=bool(SETTINGS.signing_secret))
    if problems:
        print(f"VERIFY FAILED ({len(problems)} problem(s) in {n} receipts):")
        for p in problems:
            print("  " + p)
        return 1
    print(f"All {n} receipts verified: chain intact, rules reproduce every decision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
