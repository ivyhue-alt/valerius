import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from valerius import act, page, pipeline, server, whatsapp  # noqa: E402
from valerius.types import Channel, Message, OrderRecord  # noqa: E402
import verify_receipts  # noqa: E402

SCAM = "Grandma it's me, new number. I need $900 in gift cards right now, don't tell mom"
REFUND = Message(text="This is the owner, refund $1,200 to this card now", channel=Channel.BUSINESS,
                 requested_action="refund", amount_usd=1200, order=OrderRecord(delivered=True, photo_provided=True))
SMALL = Message(text="Cupcakes were squished, photo attached, refund please", channel=Channel.BUSINESS,
                requested_action="refund", amount_usd=12, order=OrderRecord(delivered=True, photo_provided=True))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = act.Store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()


class Links(Base):
    def test_valid_link(self):
        self.assertEqual(act.check_token(act.sign("abc", "decide"), []), "")

    def test_tampered_link(self):
        t = act.sign("abc", "decide")
        t["c"] = "xyz"
        self.assertIn("signature", act.check_token(t, []))

    def test_expired_link(self):
        t = act.sign("abc", "decide", ttl_s=10, now=1000)
        self.assertIn("expired", act.check_token(t, [], now=2000))

    def test_single_use(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        tok = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(case["link"]).query))
        ok, info = act.decide(case["id"], tok, "block", self.store)
        self.assertTrue(ok)
        ok2, info2 = act.decide(case["id"], tok, "approve", self.store)
        self.assertFalse(ok2)
        self.assertEqual(self.store.load_case(case["id"])["status"], "blocked")


class Cases(Base):
    def test_held_case_has_link_allowed_case_does_not(self):
        held = act.open_case(pipeline.run(REFUND), self.store)
        allowed = act.open_case(pipeline.run(SMALL), self.store)
        self.assertEqual(held["status"], "held")
        self.assertIn("/case/", held["link"])
        self.assertEqual(allowed["status"], "allowed")
        self.assertNotIn("link", allowed)

    def test_pause_holds_every_requested_action(self):
        act.set_paused(True, self.store)
        case = act.open_case(pipeline.run(SMALL), self.store)
        self.assertEqual(case["status"], "held")
        self.assertTrue(case["paused_agent"])
        act.set_paused(False, self.store)
        self.assertEqual(act.open_case(pipeline.run(SMALL), self.store)["status"], "allowed")

    def test_agent_switch_needs_valid_single_use_token(self):
        tok = act.agent_token()
        self.assertEqual(act.switch_agent(True, tok, self.store), (True, "paused"))
        self.assertFalse(act.switch_agent(False, tok, self.store)[0])  # reused
        self.assertFalse(act.switch_agent(False, act.sign("x", "decide"), self.store)[0])

    def test_track_record_counts_receipts(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        tok = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(case["link"]).query))
        act.decide(case["id"], tok, "approve", self.store)
        self.assertEqual(act.track_record(self.store), {"held": 1, "approved": 1, "blocked": 0})


class Receipts(Base):
    def make(self):
        act.open_case(pipeline.run(REFUND), self.store)
        act.open_case(pipeline.run(Message(text=SCAM)), self.store)
        act.set_paused(True, self.store)

    def test_clean_chain_verifies(self):
        self.make()
        self.assertEqual(verify_receipts.verify(self.store), [])

    def test_edited_receipt_is_caught(self):
        self.make()
        lines = self.store.receipts_path.read_text().splitlines()
        r = json.loads(lines[0])
        r["event"] = "approved"
        lines[0] = json.dumps(r)
        self.store.receipts_path.write_text("\n".join(lines) + "\n")
        self.assertTrue(any("changed" in p for p in verify_receipts.verify(self.store)))

    def test_deleted_receipt_is_caught(self):
        self.make()
        lines = self.store.receipts_path.read_text().splitlines()
        del lines[1]
        self.store.receipts_path.write_text("\n".join(lines) + "\n")
        self.assertTrue(verify_receipts.verify(self.store))

    def test_edited_message_is_caught(self):
        self.make()
        cid = self.store.receipts()[0]["case_id"]
        case = self.store.load_case(cid)
        case["text"] = "harmless text"
        self.store.save_case(case)
        probs = verify_receipts.verify(self.store)
        self.assertTrue(any("fingerprint" in p for p in probs))

    def test_model_verdicts_kept_separate_from_rules(self):
        r = pipeline.run(Message(text=SCAM))
        case = act.open_case(r, self.store)
        rec = self.store.receipts()[-1]
        self.assertIn("rules", rec)
        self.assertIn("models", rec)
        self.assertEqual(rec["rules"]["floor"], case["rules"]["floor"])


class Page(Base):
    def test_message_html_is_escaped(self):
        m = Message(text="<script>alert(1)</script> send $900 in gift cards right now")
        case = act.open_case(pipeline.run(m), self.store)
        html = page.approval_page(case, act.sign(case["id"], "decide"), act.track_record(self.store))
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

    def test_evidence_is_highlighted_and_policy_shown(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        html = page.approval_page(case, act.sign(case["id"], "decide"), act.track_record(self.store), act.agent_token())
        self.assertIn("<mark>", html)
        self.assertIn("Refunds and reships up to $50", html)
        self.assertIn("Pause agent", html)


class Replies(unittest.TestCase):
    def test_scam_reply_is_plain_and_firm(self):
        text = act.family_reply(pipeline.run(Message(text=SCAM)))
        self.assertTrue(text.startswith("This looks like a scam"))

    def test_unverified_reply_says_so(self):
        text = act.family_reply(pipeline.run(Message(text="", kind="image")))
        self.assertIn("couldn't fully check", text)


class Server(Base):
    def setUp(self):
        super().setUp()
        server.STORE = self.store
        self.srv = server.serve(0)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def post(self, path, data: bytes, ctype="application/x-www-form-urlencoded"):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method="POST",
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_health(self):
        self.assertEqual(self.get("/health"), (200, "ok"))

    def test_owner_dashboard_needs_its_link(self):
        server.handle_incoming(whatsapp.fake_webhook(SCAM), self.store, use_models=False)
        status, html = self.get("/owner?" + urllib.parse.urlencode(act.dashboard_token()))
        self.assertEqual(status, 200)
        self.assertIn("Review and decide", html)
        self.assertEqual(self.get("/owner")[0], 403)
        self.assertEqual(self.get("/owner?" + urllib.parse.urlencode(act.sign("owner", "decide")))[0], 403)

    def test_webhook_end_to_end_then_owner_decides(self):
        payload = whatsapp.fake_webhook(SCAM)
        done = server.handle_incoming(payload, self.store, use_models=False)
        self.assertEqual(done[0]["status"], "held")
        case = self.store.load_case(done[0]["case"])
        path = urllib.parse.urlparse(case["link"])
        status, html = self.get(f"{path.path}?{path.query}")
        self.assertEqual(status, 200)
        self.assertIn("Approve", html)
        form = dict(urllib.parse.parse_qsl(path.query))
        form["decision"] = "block"
        status, html = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 200)
        self.assertIn("Blocked", html)
        status, _ = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 403)

    def test_bad_link_is_refused(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        status, html = self.get(f"/case/{case['id']}?c={case['id']}&p=decide&e=9999999999&n=x&s=bad")
        self.assertEqual(status, 403)

    def test_webhook_verify_rejects_wrong_token(self):
        status, _ = self.get("/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=42")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()


class OwnerDashboard(unittest.TestCase):
    def test_dashboard_token_rules(self):
        t = act.dashboard_token()
        self.assertTrue(act.dashboard_ok(t))
        self.assertTrue(act.dashboard_ok(t))          # reusable (view only)
        self.assertFalse(act.dashboard_ok(dict(t, c="abc")))
        self.assertFalse(act.dashboard_ok(act.sign("owner", "decide")))   # a decide link can't open the dashboard
        self.assertFalse(act.dashboard_ok(act.dashboard_token(now=0)))     # expired
        self.assertFalse(act.dashboard_ok(dict(t, s="0" * 64)))

    def test_leaked_link_can_be_cancelled(self):
        import time
        old = act.dashboard_token(now=int(time.time()) - 600)
        self.assertTrue(act.dashboard_ok(old))
        object.__setattr__(act.SETTINGS, "dashboard_not_before", int(time.time()) - 60)
        try:
            self.assertFalse(act.dashboard_ok(old))
            self.assertTrue(act.dashboard_ok(act.dashboard_token()))
        finally:
            object.__setattr__(act.SETTINGS, "dashboard_not_before", 0)

    def test_page_lists_waiting_cases_escaped(self):
        from valerius import page
        cases = [{"id": "aaaaaaaaaaaa", "status": "held", "risk": "HIGH", "channel": "business", "created_at": 0,
                  "text": "<script>x</script> refund $900", "requested_action": "refund", "amount_usd": 900,
                  "findings": [{"reason": "over the limit"}]},
                 {"id": "bbbbbbbbbbbb", "status": "blocked", "risk": "HIGH", "channel": "family", "text": "hi"}]
        html = page.owner_dashboard(cases, {"approved": 1, "blocked": 1}, {"aaaaaaaaaaaa": "http://x/case/aaaaaaaaaaaa?c=1"},
                                    None, False)
        self.assertIn("Review and decide", html)
        self.assertIn("over the limit", html)
        self.assertNotIn("<script>x", html)
        self.assertIn("http-equiv=refresh", html)
