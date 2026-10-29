"""Run the repeat-claims scenarios (data/scenarios_repeat_claims.jsonl).

    python scripts/run_scenarios.py

Each scenario is a sequence of requests from customers over time. Valerius keeps
each customer's claim count itself. Reported separately from the locked benchmark,
because these scenarios were written by the same team as the rules (written first,
committed before the rules that handle them).
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius import act, config, pipeline  # noqa: E402
from valerius.types import Channel, Message, OrderRecord  # noqa: E402


def run(path: Path = ROOT / "data" / "scenarios_repeat_claims.jsonl", verbose: bool = True) -> tuple[int, int]:
    scenarios = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    passed = total = 0
    base_policy = config.SETTINGS.policy
    now = int(time.time())
    for sc in scenarios:
        policy = dataclasses.replace(base_policy, **sc.get("policy", {}))
        object.__setattr__(config.SETTINGS, "policy", policy)
        with tempfile.TemporaryDirectory() as tmp:
            store = act.Store(Path(tmp))
            lines = []
            for step in sorted(sc["steps"], key=lambda s: -s["days_ago"]):
                t = now - step["days_ago"] * 86400
                msg = Message(text=step["text"], channel=Channel.BUSINESS, customer_id=step["customer_id"],
                              requested_action=step.get("requested_action", ""), amount_usd=step.get("amount_usd"),
                              items=step.get("items"), order=OrderRecord(**step["order"]) if step.get("order") else None)
                msg = act.with_history(msg, store, now=t)
                result = pipeline.run(msg)
                case = act.open_case(result, store, now=t)
                got = "hold" if case["status"] == "held" else "allow"
                ok = got == step["expect"]
                passed += ok
                total += 1
                why = ", ".join(f.rule for f in result.assessment.findings) or "-"
                lines.append(f"    {'ok ' if ok else 'XX '} day -{step['days_ago']:>3}  {step['customer_id']:<4} expect {step['expect']:<5} got {got:<5} [{why}]")
        if verbose:
            print(f"{sc['id']}: {sc['description']}")
            print("\n".join(lines))
    object.__setattr__(config.SETTINGS, "policy", base_policy)
    print(f"\nRepeat-claims scenarios: {passed}/{total} steps behave as expected.")
    return passed, total


if __name__ == "__main__":
    p, t = run()
    sys.exit(0 if p == t else 1)
