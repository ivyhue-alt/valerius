"""Check the post-final-run reseller fix on fresh rows written AFTER the fix.

    python scripts/run_fresh.py            # rules only
    python scripts/run_fresh.py --live     # with both model reviews

Rows live in data/fresh_reseller.csv, written and labeled by Tay before this script is run.
label: hold = the owner should decide; allow = the agent can handle it.
refunds_last_90d also counts as this customer's earlier claims; photo_provided and shipped are yes, no or empty (not stated).
Reported separately from the locked benchmark, never mixed into it.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius import pipeline  # noqa: E402
from valerius.types import Message, OrderRecord  # noqa: E402


def main() -> int:
    live = "--live" in sys.argv
    rows = [r for r in csv.DictReader(open(ROOT / "data" / "fresh_reseller.csv", encoding="utf-8")) if r.get("text")]
    bad = [r["id"] for r in rows if r["label"].strip().lower() not in ("hold", "allow")]
    if bad:
        print("Every row needs label 'hold' or 'allow': " + ", ".join(bad))
        return 1
    right = 0
    for r in rows:
        order = OrderRecord(order_id=f"ORD-{r['id']}", purchased_at="2026-10-05", purchase_city="Newark",
                            purchase_country="US", ship_country="US", delivered=True, receipt_on_file=True,
                            photo_provided={"yes": True, "no": False}.get(r.get("photo_provided", "").strip().lower()),
                            quantity=int(r["quantity"] or 1),
                            minutes_since_purchase=int(r["minutes_since_purchase"]) if r.get("minutes_since_purchase") else None,
                            shipped={"yes": True, "no": False}.get(r.get("shipped", "").strip().lower()),
                            refunds_last_90d=int(r["refunds_last_90d"] or 0))
        amount = float(r["amount_usd"]) if r["amount_usd"] else None
        past = int(r["refunds_last_90d"] or 0)
        msg = Message(text=r["text"], channel="business", requested_action=r["requested_action"].strip(),
                      amount_usd=amount, order=order, conversation_id=r["id"], customer_id=f"C-{r['id']}",
                      prior_claims=past)
        res = pipeline.run(msg, use_models=live)
        want = r["label"].strip().lower() == "hold"
        ok = res.hold == want
        right += ok
        print(f"  {r['id']} want {'hold ' if want else 'allow'} got {'hold ' if res.hold else 'allow'} "
              f"{res.risk.name:8} {'ok' if ok else 'WRONG'}")
    print(f"Fresh reseller rows: {right}/{len(rows)} as labeled"
          f" ({'rules + both models' if live else 'rules only'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
