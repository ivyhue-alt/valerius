"""Business hours: holds wait overnight, the customer is told when, and the owner gets one morning summary."""
import os
os.environ["VALERIUS_OFFLINE"] = "1"  # tests never send real messages or call the network


import datetime as dt
import tempfile
import unittest
from pathlib import Path

from valerius import act, hours, pipeline
from valerius.types import Channel, Message, OrderRecord


def at(h, m=0, day=3):
    return int(dt.datetime(2026, 11, day, h, m, tzinfo=hours._tz()).timestamp())


class Hours(unittest.TestCase):
    def test_open_and_next_open(self):
        self.assertTrue(hours.is_open(at(10)))
        self.assertFalse(hours.is_open(at(23, 40)))
        self.assertFalse(hours.is_open(at(6)))
        self.assertEqual(hours.next_open(at(23, 40)), at(9, day=4))
        self.assertEqual(hours.next_open(at(6)), at(9))
        self.assertEqual(hours.when_text(at(9, day=4), at(23, 40)), "tomorrow at 9 AM")


class Overnight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = act.Store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def held(self, ts):
        msg = Message(text="I need to return 12 candles", channel=Channel.BUSINESS, requested_action="refund",
                      amount_usd=480, customer_id="C-1", customer_name="Dana",
                      order=OrderRecord(order_id="ORD-1", quantity=12, delivered=True, receipt_on_file=True))
        return act.open_case(pipeline.run(msg), self.store, now=ts)

    def test_night_hold_waits_and_customer_is_told_when(self):
        case = self.held(at(23, 40))
        self.assertEqual(case["status"], "held")
        self.assertTrue(case["after_hours"])
        self.assertFalse(case["owner_pinged"])
        self.assertIn("when we open tomorrow at 9 AM", act.holding_message(case, now=at(23, 40)))

    def test_day_hold_pings_right_away(self):
        case = self.held(at(14))
        self.assertTrue(case["owner_pinged"])
        self.assertIn("looking at this now", act.holding_message(case))

    def test_one_summary_at_opening_and_only_once(self):
        self.held(at(23, 40))
        self.held(at(2, 10, day=4))
        self.assertEqual(act.morning_summary(self.store, now=at(8, day=4)), "")      # not open yet
        text = act.morning_summary(self.store, now=at(9, 1, day=4))
        self.assertIn("2 things came in overnight", text)
        self.assertEqual(act.morning_summary(self.store, now=at(9, 5, day=4)), "")   # not sent twice
