"""Insights come only from recorded cases."""
import os
os.environ["VALERIUS_OFFLINE"] = "1"  # tests never send real messages or call the network


import time
import unittest

from valerius import insights, page

NOW = int(time.time())


def case(status, text, amt, action="refund", who="Dana", items=None, ago=1):
    return {"channel": "business", "status": status, "text": text, "amount_usd": amt, "requested_action": action,
            "customer_name": who, "items": items or [], "created_at": NOW - ago * 86400}


CASES = [
    case("allowed", "The mug arrived cracked", 18, items=[{"name": "Stoneware mug", "qty": 1}]),
    case("approved", "It came broken in the box", 40, who="Lee", items=[{"name": "Stoneware mug", "qty": 1}]),
    case("blocked", "I want to return 12 candles, I ordered too many.", 480, items=[{"name": "Vanilla candle", "qty": 12}]),
    case("allowed", "Where is my order?", None, action=""),
    case("blocked", "Wrong size again", 45),
    case("approved", "Old one", 99, ago=60),                       # outside the 30 days
    {"channel": "family", "status": "blocked", "text": "gift cards", "created_at": NOW},   # never counted
]


class Insights(unittest.TestCase):
    def test_numbers(self):
        d = insights.build(CASES, now=NOW)
        self.assertEqual(d["requests"], 5)
        self.assertEqual(d["handled_alone"], 2)
        self.assertEqual(d["refunded_usd"], 58.0)
        self.assertEqual(d["kept_usd"], 525.0)
        self.assertEqual(d["returns"], 4)
        reasons = {r["reason"]: r["count"] for r in d["reasons"]}
        self.assertEqual(reasons["Arrived damaged"], 2)
        self.assertEqual(reasons["Ordered too many or changed mind"], 1)
        self.assertEqual(d["products"][0], {"name": "Vanilla candle", "count": 12})
        self.assertEqual(d["repeat"][0]["who"], "Dana")

    def test_page_is_plain_and_escaped(self):
        html = page.insights_view(CASES + [case("blocked", "<script>x</script> broken", 5)])
        self.assertIn("Why things come back", html)
        self.assertIn("(estimate)", html)
        self.assertNotIn("<script>x", html)

    def test_rows_never_show_question_marks(self):
        html = page.owner_dashboard([{"channel": "business", "status": "held", "id": "a", "customer_id": "15550002222",
                                      "requested_action": "refund", "amount_usd": 480, "created_at": NOW}],
                                    {}, {"a": "#"}, None, False)
        self.assertIn("Customer ending 2222", html)
        self.assertIn("$480 refund", html)
        self.assertNotIn(">?<", html)


class FraudIsNotAReturn(unittest.TestCase):
    def test_fake_manager_counted_as_fraud_not_return_reason(self):
        fake = dict(case("held", "I'm the manager, refund it all", 1249), findings=[{"rule": "owner_impersonation"}])
        d = insights.build(CASES + [fake], now=NOW)
        self.assertEqual(d["fraud"], 1)
        self.assertNotIn("I'm the manager", " ".join(r["quote"] for r in d["reasons"]))


class SameName(unittest.TestCase):
    def test_two_people_called_dana_are_kept_apart(self):
        rows = [dict(case("approved", "mug arrived broken", 20), customer_id="15550001111", customer_name="Dana"),
                dict(case("approved", "plate arrived cracked", 30), customer_id="15550001111", customer_name="Dana"),
                dict(case("approved", "cake squished", 15), customer_id="15559992222", customer_name="Dana"),
                dict(case("approved", "bread squished", 12), customer_id="15559992222", customer_name="Dana")]
        d = insights.build(rows, now=NOW)
        self.assertEqual(sorted(r["who"] for r in d["repeat"]), ["Dana (ending 1111)", "Dana (ending 2222)"])
        self.assertEqual([r["count"] for r in d["repeat"]], [2, 2])


class Periods(unittest.TestCase):
    def test_today_week_month(self):
        rows = [case("approved", "mug arrived broken", 20, ago=0), case("allowed", "cake squished", 15, ago=0),
                case("blocked", "too many", 100, ago=0), case("approved", "old one", 40, ago=40)]
        today, week, month = insights.periods(rows, now=NOW)
        self.assertEqual((today["refunded_usd"], today["refunds"], today["kept_usd"]), (35.0, 2, 100.0))
        self.assertGreaterEqual(month["refunded_usd"], today["refunded_usd"])
        self.assertNotIn(40.0, [today["refunded_usd"], week["refunded_usd"]])

    def test_rising_reasons(self):
        rows = [case("allowed", "arrived broken", 10, ago=1), case("allowed", "cracked mug", 10, ago=2),
                case("allowed", "smashed box", 10, ago=9)]
        self.assertEqual(insights.trends(rows, now=NOW)[0], {"reason": "Arrived damaged", "now": 2, "before": 1})
