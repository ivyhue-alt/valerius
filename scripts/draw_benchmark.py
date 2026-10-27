"""Draw the benchmark from the candidate pool, at random, so nobody picks easy cases.

    python scripts/draw_benchmark.py

- The seed comes from the SHA-256 of data/pool.jsonl, so nobody chooses it and
  anyone can reproduce the draw.
- Stratified: 50 positive and 50 negative rows, spread across categories in
  proportion to the pool (at least one per category).
- Split before any run: 30 dev rows (15 + 15) for fixing, 70 test rows locked.
  Never tune rules or prompts on the test rows.

Writes data/benchmark.jsonl, data/manifest.json and data/label_check.csv.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "data" / "pool.jsonl"
PER_LABEL = 50
DEV_PER_LABEL = 15


def allocate(counts: dict[str, int], total: int) -> dict[str, int]:
    """Proportional allocation, at least 1 per category, never more than available."""
    n = sum(counts.values())
    alloc = {c: max(1, int(total * k / n)) for c, k in counts.items()}
    alloc = {c: min(a, counts[c]) for c, a in alloc.items()}
    remainders = sorted(counts, key=lambda c: (total * counts[c] / n) % 1, reverse=True)
    i = 0
    while sum(alloc.values()) < total:
        c = remainders[i % len(remainders)]
        if alloc[c] < counts[c]:
            alloc[c] += 1
        i += 1
    while sum(alloc.values()) > total:
        c = max(alloc, key=lambda k: alloc[k])
        alloc[c] -= 1
    return alloc


def main() -> None:
    raw = POOL.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    seed = int(digest[:12], 16)
    rng = random.Random(seed)
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]

    drawn = []
    for label in ("positive", "negative"):
        by_cat: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            if r["label"] == label:
                by_cat[r["category"]].append(r)
        alloc = allocate({c: len(v) for c, v in sorted(by_cat.items())}, PER_LABEL)
        picked = []
        for cat in sorted(alloc):
            picked += rng.sample(by_cat[cat], alloc[cat])
        rng.shuffle(picked)
        for i, r in enumerate(picked):
            r = dict(r)
            r["split"] = "dev" if i < DEV_PER_LABEL else "test"
            drawn.append(r)

    drawn.sort(key=lambda r: r["id"])
    out = ROOT / "data" / "benchmark.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in drawn), encoding="utf-8")

    manifest = {
        "pool_sha256": digest,
        "seed": seed,
        "pool_rows": len(rows),
        "drawn": len(drawn),
        "positive": sum(r["label"] == "positive" for r in drawn),
        "negative": sum(r["label"] == "negative" for r in drawn),
        "dev": sum(r["split"] == "dev" for r in drawn),
        "test": sum(r["split"] == "test" for r in drawn),
        "rule": "Never tune rules or prompts on rows with split=test.",
    }
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with (ROOT / "data" / "label_check.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "channel", "category", "label", "kind", "text", "order_or_image", "agree (Y/N)", "note"])
        for r in drawn:
            extra = r.get("image_spec") or (json.dumps({k: v for k, v in r.items()
                                                       if k in ("requested_action", "amount_usd", "order")}) if r["channel"] == "business" else "")
            w.writerow([r["id"], r["channel"], r["category"], r["label"], r.get("kind", "text"), r["text"], extra, "", ""])
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
