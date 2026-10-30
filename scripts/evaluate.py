"""Score the pipeline on the benchmark.

    python scripts/evaluate.py                 # dev rows only (safe to look at while building)
    python scripts/evaluate.py --final         # locked test rows: run once, for the reported numbers
    python scripts/evaluate.py --live          # include Muse Spark + second pass (needs keys in .env)

For practice runs on synthetic data, set JUDGE_MODEL=muse-spark-1.3-contributor (cheaper).
Cost is always reported at Standard prices.

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


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for st in self.streams:
            st.write(text)

    def flush(self):
        for st in self.streams:
            st.flush()


def image_for(row: dict) -> tuple[bytes | None, str]:
    """The row's image from data/images (made once by make_benchmark_images.py), checked against its fingerprint."""
    if row.get("kind") != "image":
        return None, ""
    import hashlib
    manifest_path = ROOT / "data" / "images" / "manifest.json"
    entry = json.loads(manifest_path.read_text(encoding="utf-8")).get(row["id"]) if manifest_path.is_file() else None
    if not entry:
        return None, ""  # no image: Valerius can't read it, so it holds (counted as such)
    data = (ROOT / "data" / "images" / entry["file"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise SystemExit(f"{row['id']}: image does not match its fingerprint in data/images/manifest.json")
    return data, ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="score the locked test rows")
    ap.add_argument("--live", action="store_true", help="call Muse Spark and the second pass")
    ap.add_argument("--out", help="also save everything printed to this file (UTF-8)")
    args = ap.parse_args()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = _Tee(sys.stdout, open(args.out, "w", encoding="utf-8"))
    split = "test" if args.final else "dev"
    rows = [json.loads(x) for x in (ROOT / "data" / "benchmark.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if r["split"] == split]

    tp = fn = fp = tn = 0
    cost = 0.0
    secs: list[float] = []
    disagreements = errors = 0
    misses, false_alarms = [], []
    for r in rows:
        media, mime = image_for(r)
        res = pipeline.run(to_message(r), use_models=args.live, media=media, media_mime=mime)
        flagged = res.hold
        if args.live:
            cost += res.standard_cost_usd()
            secs += [v.seconds for v in (res.first, res.second) if v is not None and v.seconds]
            disagreements += res.disagreement
            errors += sum(1 for v in (res.first, res.second) if v is not None and not v.ok)
            print(f"  {r['id']} {r['label'][:3]} -> {res.risk.name}{' HOLD' if flagged else ''}"
                  f"{' (disagree)' if res.disagreement else ''}", flush=True)
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
    stage = "rules + Muse Spark + second pass" if args.live else "rules only"
    print(f"[{split}] stage: {stage} | n={len(rows)} (synthetic, hand-labeled)")
    print(f"  catch rate   {tp}/{tp + fn} = {tp / max(tp + fn, 1):.0%}  (95% CI {lo:.0%} to {hi:.0%})")
    print(f"  false alarms {fp}/{fp + tn} = {fp / max(fp + tn, 1):.0%}  (95% CI {flo:.0%} to {fhi:.0%})")
    print("  missed:      " + (", ".join(misses) or "none"))
    print("  false alarm: " + (", ".join(false_alarms) or "none"))
    if args.live:
        n = max(len(rows), 1)
        print(f"  Muse Spark cost at Standard prices: ${cost:.4f} total, ${cost / n:.5f} per message")
        if secs:
            secs.sort()
            print(f"  model call time: median {secs[len(secs) // 2]:.1f}s, slowest {secs[-1]:.1f}s")
        print(f"  disagreements sent to a human: {disagreements} | model errors: {errors}")


if __name__ == "__main__":
    main()
