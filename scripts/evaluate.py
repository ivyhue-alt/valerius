"""Score the pipeline on the benchmark.

    python scripts/evaluate.py                 # dev rows only (safe to look at while building)
    python scripts/evaluate.py --final         # locked test rows: run once, for the reported numbers

A row counts as flagged when Valerius would hold it (risk HIGH or above, or a
check could not run). Catch rate = flagged positives / positives.
False-alarm rate = flagged negatives / negatives. 95% Wilson intervals.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius import pipeline  # noqa: E402
from valerius.types import Message, OrderRecord  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d), min(1.0, (c + m) / d)


def to_message(row: dict) -> Message:
    order = OrderRecord(**row["order"]) if row.get("order") else None
    return Message(text=row["text"], channel=row["channel"], kind=row.get("kind", "text"),
                   requested_action=row.get("requested_action", ""), amount_usd=row.get("amount_usd"),
                   order=order, conversation_id=row["id"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="score the locked test rows")
    args = ap.parse_args()
    split = "test" if args.final else "dev"
    rows = [json.loads(x) for x in (ROOT / "data" / "benchmark.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if r["split"] == split]

    tp = fn = fp = tn = 0
    misses, false_alarms = [], []
    for r in rows:
        flagged = pipeline.run(to_message(r)).hold
        if r["label"] == "positive":
            tp, fn = (tp + 1, fn) if flagged else (tp, fn + 1)
            if not flagged:
                misses.append(f'{r["id"]} {r["category"]}')
        else:
            fp, tn = (fp + 1, tn) if flagged else (fp, tn + 1)
            if flagged:
                false_alarms.append(f'{r["id"]} {r["category"]}')

    lo, hi = wilson(tp, tp + fn)
    flo, fhi = wilson(fp, fp + tn)
    print(f"[{split}] stage: rules only | n={len(rows)} (synthetic, hand-labeled)")
    print(f"  catch rate   {tp}/{tp + fn} = {tp / max(tp + fn, 1):.0%}  (95% CI {lo:.0%} to {hi:.0%})")
    print(f"  false alarms {fp}/{fp + tn} = {fp / max(fp + tn, 1):.0%}  (95% CI {flo:.0%} to {fhi:.0%})")
    print("  missed:      " + (", ".join(misses) or "none"))
    print("  false alarm: " + (", ".join(false_alarms) or "none"))


if __name__ == "__main__":
    main()
