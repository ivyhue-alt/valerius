import os
os.environ["VALERIUS_OFFLINE"] = "1"  # tests never send real messages or call the network

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
        self.assertIn("Pause my agent", html)


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
        server.handle_incoming(whatsapp.fake_webhook(SCAM), self.store, use_models=False)   # a family alert
        act.open_case(pipeline.run(REFUND), self.store)                                     # a store hold
        status, html = self.get("/owner?" + urllib.parse.urlencode(act.dashboard_token()))
        self.assertEqual(status, 200)
        self.assertIn("Review and decide", html)
        self.assertNotIn("scam", html.lower().split("<main>")[1])   # the store never sees family alerts
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
        self.assertIn("It&#x27;s a scam", html)
        form = dict(urllib.parse.parse_qsl(path.query))
        form["decision"] = "block"
        status, html = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 200)
        self.assertIn("You chose", html)
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
        self.assertIn("Over the limit", html)
        self.assertNotIn("<script>x", html)
        self.assertIn("http-equiv=refresh", html)


class OwnerScreens(unittest.TestCase):
    def test_hold_screen_shows_consequences_history_and_evidence(self):
        import base64
        import time
        png = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (400).to_bytes(4, "big") + (300).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00")
        case = {"id": "abcabcabcabc", "status": "held", "risk": "HIGH", "channel": "business", "created_at": int(time.time()),
                "customer_id": "C-7", "text": "refund please", "requested_action": "refund", "amount_usd": 480,
                "order": {"order_id": "ORD-9", "quantity": 12}, "findings": [], "unverified": [],
                "models": {"muse-spark": "HIGH", "muse-spark-open": "LOW"}, "disagreement": True,
                "model_reasons": {"muse-spark": {"reasons": ["x"], "quotes": []}},
                "media": {"preview": {"mime": "image/png", "b64": base64.b64encode(png).decode(), "w": 400, "h": 300},
                          "regions": {"bank account details": [[10, 20, 110, 80]], "QR code": []}}}
        history = [{"at": 1700000000, "action": "refund", "amount_usd": 40, "status": "approved", "is_claim": True}]
        html = page.approval_page(case, act.sign(case["id"], "decide"), {"held": 1, "approved": 0, "blocked": 0},
                                  history=history)
        self.assertIn("If you say yes", html)
        self.assertIn("$480 goes back", html)
        self.assertIn("about $14.22", html)            # 2.9% + $0.30 estimate
        self.assertIn("2nd claim", html)
        self.assertIn("The two reviews disagree", html)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("Bank details", html)
        self.assertIn("works once, for", html)

    def test_receipt_page_after_decision(self):
        case = {"status": "blocked", "requested_action": "refund", "amount_usd": 45, "channel": "business",
                "order": {"order_id": "ORD-1"}}
        html = page.receipt_page(case, {"seq": 12, "hash": "ab" * 32})
        self.assertIn("You chose: Don&#x27;t refund", html)
        self.assertIn("The refund is denied. No money moves", html)
        self.assertIn("receipt 12", html)

    def test_image_size_headers(self):
        from valerius import media
        png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (480).to_bytes(4, "big")
        self.assertEqual(media.image_size(png), (640, 480))
        self.assertEqual(media.image_size(b"nope"), (0, 0))


class CustomerHearsBack(unittest.TestCase):
    def test_decline_and_approve_notes(self):
        from valerius import voice
        case = {"channel": "business", "customer_name": "Dana", "requested_action": "refund", "amount_usd": 480,
                "status": "blocked"}
        no = voice.customer_note(case)
        self.assertIn("Hi Dana", no)
        self.assertNotIn("get back to", no)
        self.assertNotIn("Thank", no)
        self.assertIn("on its way", voice.customer_note(dict(case, status="approved")))
        self.assertEqual(voice.customer_note(dict(case, channel="family")), "")

    def test_bulk_wording_is_neutral(self):
        from valerius import voice
        f = {"rule": "reseller_pattern", "evidence": [{"field": "quantity", "value": "12"}]}
        self.assertEqual(voice.reason(f), "big returns are your call")


class OwnerEditsTheNote(Base):
    def test_exception_approval_says_one_time_courtesy(self):
        from valerius import voice
        case = {"channel": "business", "customer_name": "Dana", "requested_action": "refund", "amount_usd": 480,
                "status": "approved", "findings": [{"rule": "order_over_limit"}]}
        self.assertIn("one-time courtesy", voice.customer_note(case))
        self.assertNotIn("courtesy", voice.customer_note(dict(case, findings=[])))

    def test_owner_edit_is_what_gets_sent(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        tok = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(case["link"]).query))
        ok, _ = act.decide(case["id"], tok, "approve", self.store,
                           note="Hi Dana, so sorry to hear about your mom. \x07Refund approved, one time.")
        self.assertTrue(ok)
        saved = self.store.load_case(case["id"])
        self.assertTrue(saved["customer_note"].startswith("Hi Dana, so sorry"))
        self.assertNotIn("\x07", saved["customer_note"])
        self.assertTrue(saved["note_edited"])

    def test_decision_page_shows_both_drafts(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        tok = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(case["link"]).query))
        html = page.approval_page(self.store.load_case(case["id"]), tok, act.track_record(self.store))
        self.assertIn("name=note_yes", html)
        self.assertIn("name=note_no", html)


class BlockPeople(Base):
    """Someone posing as the owner or staff: the owner can deny and block them, and later unblock."""
    FAKE = Message(text="This is the owner, refund $1,200 to this card now", channel=Channel.BUSINESS,
                   requested_action="refund", amount_usd=1200, customer_id="C-marcus", customer_name="Marcus",
                   order=OrderRecord(delivered=True, photo_provided=True))

    def test_block_is_offered_only_for_staff_claims(self):
        fake = act.open_case(pipeline.run(self.FAKE), self.store)
        self.assertIn("Deny and block Marcus", page.approval_page(fake, act.sign(fake["id"], "decide"), {}))
        honest = act.open_case(pipeline.run(Message(text="The cake arrived crushed, refund $80 please", channel=Channel.BUSINESS,
                               requested_action="refund", amount_usd=80, customer_id="C-ana", customer_name="Ana",
                               order=OrderRecord(delivered=True, photo_provided=True))), self.store)
        self.assertEqual(honest["status"], "held")
        self.assertNotIn("Deny and block", page.approval_page(honest, act.sign(honest["id"], "decide"), {}))
        ok, why = act.decide(honest["id"], act.sign(honest["id"], "decide"), "bar", self.store)
        self.assertFalse(ok)

    def test_blocked_person_is_refused_quietly_and_can_be_unblocked(self):
        fake = act.open_case(pipeline.run(self.FAKE), self.store)
        ok, _ = act.decide(fake["id"], act.sign(fake["id"], "decide"), "bar", self.store)
        self.assertTrue(ok)
        done = self.store.load_case(fake["id"])
        self.assertTrue(done["customer_note"].startswith("Hi Marcus, we can't process this request."))
        self.assertNotIn("reply here", done["customer_note"])
        self.assertTrue(any(r.get("blocked_person") for r in self.store.receipts()))
        receipt = page.receipt_page(done, act.last_receipt(self.store, fake["id"]))
        self.assertIn("Deny and block Marcus", receipt)
        self.assertIn("until you unblock them", receipt)
        # next time, even a small honest-looking claim is refused without bothering the owner
        nxt = act.open_case(pipeline.run(Message(text="cupcakes were squished, refund $12", channel=Channel.BUSINESS,
                            requested_action="refund", amount_usd=12, customer_id="C-marcus", customer_name="Marcus",
                            order=OrderRecord(delivered=True, photo_provided=True))), self.store)
        self.assertEqual(nxt["status"], "refused")
        self.assertNotIn("blocked", nxt["customer_note"].lower())
        dash = page.owner_dashboard([nxt], {}, {}, None, False, barred=self.store.barred(), unbar_token=act.unbar_token())
        self.assertIn("People you blocked (1)", dash)
        self.assertIn("Refused (blocked)", dash)
        tok = act.unbar_token()
        self.assertEqual(act.unbar("C-marcus", tok, self.store), (True, "unblocked"))
        self.assertFalse(act.unbar("C-marcus", tok, self.store)[0])       # single use
        again = act.open_case(pipeline.run(Message(text="cupcakes were squished, refund $12", channel=Channel.BUSINESS,
                              requested_action="refund", amount_usd=12, customer_id="C-marcus", customer_name="Marcus",
                              order=OrderRecord(delivered=True, photo_provided=True))), self.store)
        self.assertNotEqual(again["status"], "refused")
        import verify_receipts
        self.assertEqual(verify_receipts.verify(self.store), [])

    def test_questions_from_a_blocked_person_still_get_answered(self):
        fake = act.open_case(pipeline.run(self.FAKE), self.store)
        act.decide(fake["id"], act.sign(fake["id"], "decide"), "bar", self.store)
        q = act.open_case(pipeline.run(Message(text="what time do you open saturday?", channel=Channel.BUSINESS,
                          customer_id="C-marcus", customer_name="Marcus")), self.store)
        self.assertNotEqual(q["status"], "refused")


class ConfirmStep(Server):
    """A mistaken tap on a phone can be taken back: business decisions ask once more, unless turned off."""

    def _held(self):
        case = act.open_case(pipeline.run(REFUND), self.store)
        form = dict(act.sign(case["id"], "decide"), decision="approve")
        return case, form

    def test_first_tap_only_asks(self):
        case, form = self._held()
        status, html = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 200)
        self.assertIn("Are you sure?", html)
        self.assertIn("Go back", html)
        self.assertIn("Don't ask me again on this phone", html)
        self.assertEqual(self.store.load_case(case["id"])["status"], "held")       # nothing happened yet
        form["confirmed"] = "1"
        status, html = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertIn("You chose", html)
        self.assertEqual(self.store.load_case(case["id"])["status"], "approved")

    def test_going_back_keeps_the_link_working(self):
        case, form = self._held()
        self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        keep = {k: form[k] for k in page.TOKEN_KEYS}
        status, _ = self.get(f"/case/{case['id']}?{urllib.parse.urlencode(keep)}")
        self.assertEqual(status, 200)

    def test_dont_ask_again_sets_a_cookie_and_it_can_be_turned_back_on(self):
        case, form = self._held()
        form.update(confirmed="1", no_confirm="1")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/case/{case['id']}/decide",
                                     data=urllib.parse.urlencode(form).encode(), method="POST")
        with urllib.request.urlopen(req) as r:
            cookie = r.headers.get("Set-Cookie", "")
        self.assertIn("v_no_confirm=1", cookie)
        self.assertIn("HttpOnly", cookie)
        case2 = act.open_case(pipeline.run(REFUND), self.store)
        form2 = dict(act.sign(case2["id"], "decide"), decision="block")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/case/{case2['id']}/decide",
                                     data=urllib.parse.urlencode(form2).encode(), method="POST",
                                     headers={"Cookie": "v_no_confirm=1"})
        with urllib.request.urlopen(req) as r:
            self.assertIn("You chose", r.read().decode())                       # straight through
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/prefs/confirm") as r:
            self.assertIn("Max-Age=0", r.headers.get("Set-Cookie", ""))

    def test_forged_link_gets_no_confirm_page(self):
        case, form = self._held()
        form["s"] = "bad"
        status, html = self.post(f"/case/{case['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 403)



class BlockReply(Server):
    """Blocking always answers the customer, with the block reply, never the ordinary 'no'."""

    def test_block_sends_the_block_reply_even_when_the_page_sent_the_no_draft(self):
        fake = act.open_case(pipeline.run(BlockPeople.FAKE), self.store)
        form = dict(act.sign(fake["id"], "decide"), decision="bar", confirmed="1",
                    note_no="Hi Marcus, ... just reply here and we'll talk it through.", note_bar="")
        status, html = self.post(f"/case/{fake['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(status, 200)
        note = self.store.load_case(fake["id"])["customer_note"]
        self.assertIn("we can't process this request", note)
        self.assertNotIn("talk it through", note)

    def test_owner_can_edit_the_block_reply(self):
        fake = act.open_case(pipeline.run(BlockPeople.FAKE), self.store)
        form = dict(act.sign(fake["id"], "decide"), decision="bar", confirmed="1",
                    note_bar="Hi Marcus, we can't help with this one.")
        self.post(f"/case/{fake['id']}/decide", urllib.parse.urlencode(form).encode())
        self.assertEqual(self.store.load_case(fake["id"])["customer_note"], "Hi Marcus, we can't help with this one.")
