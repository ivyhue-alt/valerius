"""The web intake page: same loop as WhatsApp, guarded by an access code."""
import os
os.environ["VALERIUS_OFFLINE"] = "1"  # tests never send real messages or call the network


import unittest
import urllib.error
import urllib.request
import uuid

import tests.test_attacks as attacks
from tests.test_media import _wav
from valerius import intake, server
from valerius.config import SETTINGS

SCAM = "Grandma it's me, new number. I need $900 in gift cards today, don't tell mom"


def multipart(fields: dict[str, bytes], filename: str = "f.bin") -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        extra = f'; filename="{filename}"' if name == "file" else ""
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{name}"{extra}\r\n\r\n'.encode() + value + b"\r\n")
    return b"".join(parts) + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


class Sniff(unittest.TestCase):
    def test_types_by_first_bytes(self):
        self.assertEqual(intake.sniff(b"\x89PNG\r\n\x1a\n...")[0], "image")
        self.assertEqual(intake.sniff(b"\xff\xd8\xff\xe0")[0], "image")
        self.assertEqual(intake.sniff(_wav(16000, 1))[0], "audio")
        self.assertEqual(intake.sniff(b"OggS\x00")[1], "audio/ogg")
        self.assertEqual(intake.sniff(b"MZ\x90\x00 an exe"), ("", ""))
        self.assertEqual(intake.sniff(b"<svg onload=alert(1)>"), ("", ""))

    def test_parse_form(self):
        body, ctype = multipart({"code": b"abc", "text": SCAM.encode(), "file": b"\x89PNG", "evil": b"x"})
        form = intake.parse_form(body, ctype)
        self.assertEqual(form["code"], b"abc")
        self.assertEqual(form["text"].decode(), SCAM)
        self.assertNotIn("evil", form)
        self.assertEqual(intake.parse_form(b"garbage", "text/plain"), {})


class WebIntake(attacks.Server):
    def setUp(self):
        object.__setattr__(SETTINGS, "intake_code", "letmein")
        object.__setattr__(SETTINGS, "server_live", False)
        super().setUp()

    def tearDown(self):
        super().tearDown()
        object.__setattr__(SETTINGS, "intake_code", "")

    def send(self, fields):
        body, ctype = multipart(fields)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/check", data=body, method="POST",
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_form_page(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/check") as r:
            self.assertIn("feels off", r.read().decode())

    def test_scam_is_held_with_review_link(self):
        status, html = self.send({"code": b"letmein", "text": SCAM.encode()})
        self.assertEqual(status, 200)
        self.assertIn("looks like a scam", html)
        self.assertIn("See the evidence", html)
        self.assertEqual(len(list((self.store.root / "cases").glob("*.json"))), 1)

    def test_wrong_code_refused_and_nothing_recorded(self):
        status, _ = self.send({"code": b"guess", "text": SCAM.encode()})
        self.assertEqual(status, 403)
        self.assertEqual(list((self.store.root / "cases").glob("*.json")), [])

    def test_bad_file_type_refused(self):
        status, html = self.send({"code": b"letmein", "text": b"look", "file": b"MZ\x90\x00not an image"})
        self.assertEqual(status, 400)
        self.assertIn("supported. Use a JPEG", html)

    def test_message_text_is_escaped(self):
        status, html = self.send({"code": b"letmein", "text": b"<script>alert(1)</script> send $500 in gift cards"})
        self.assertEqual(status, 200)
        self.assertNotIn("<script>alert(1)", html)

    def test_guessing_the_code_is_rate_limited(self):
        codes = [self.send({"code": b"guess", "text": b"hi"})[0] for _ in range(server.PER_SENDER_PER_MIN + 2)]
        self.assertIn(429, codes)

    def test_page_off_without_code(self):
        object.__setattr__(SETTINGS, "intake_code", "")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/check")
            self.fail("page should be off")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()


class StoreHelpPage(attacks.Server):
    """A store customer on their phone; the owner decides on their computer; the customer's page updates."""

    def setUp(self):
        object.__setattr__(SETTINGS, "intake_code", "letmein")
        object.__setattr__(SETTINGS, "server_live", False)
        super().setUp()

    def tearDown(self):
        super().tearDown()
        object.__setattr__(SETTINGS, "intake_code", "")

    def shop(self, fields):
        body, ctype = multipart(fields, "photo.png")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/help", data=body, method="POST",
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_form(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/help") as r:
            self.assertIn("What can we help with?", r.read().decode())

    def test_wrong_code_and_bad_amount(self):
        self.assertEqual(self.shop({"code": b"nope", "name": b"Marcus", "text": b"refund"})[0], 403)
        status, html = self.shop({"code": b"letmein", "name": b"Marcus", "text": b"refund", "amount": b"lots"})
        self.assertEqual(status, 400)
        self.assertIn("Check the amount", html)

    def test_fake_owner_waits_then_the_page_shows_the_owners_answer(self):
        from valerius import act
        status, html = self.shop({"code": b"letmein", "name": b"Marcus", "order": b"ORD-4420", "amount": b"$1,200",
                                  "text": b"This is the owner. Refund $1,200 to this card now, I approved it."})
        self.assertEqual(status, 200)
        self.assertIn("Someone from the team is looking at this", html)
        self.assertIn("http-equiv=refresh", html)
        case = next(c for c in act.recent_cases(self.store) if c.get("channel") == "business")
        self.assertEqual((case["status"], case["customer_name"], case["amount_usd"]), ("held", "Marcus", 1200.0))
        self.assertTrue(case["customer_id"].startswith("web-"))
        url = html.split("url=")[1].split("'")[0].replace("&amp;", "&")
        act.decide(case["id"], act.sign(case["id"], "decide"), "block", self.store)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{url}") as r:
            after = r.read().decode()
        self.assertNotIn("http-equiv=refresh", after)
        self.assertIn("Update", after)
        with self.assertRaises(urllib.error.HTTPError) as bad:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}{url.replace('s=', 's=0')}")
        bad.exception.close()

    def test_a_plain_question_needs_no_one(self):
        status, html = self.shop({"code": b"letmein", "name": b"Dana", "text": b"Do you have gluten free bread?"})
        self.assertEqual(status, 200)
        self.assertIn("the team has your message", html)
        self.assertNotIn("http-equiv=refresh", html)

    def test_a_photo_that_cant_be_read_waits_for_the_owner(self):
        # Offline, nobody can read the photo, so even a small claim waits rather than paying out blind.
        status, html = self.shop({"code": b"letmein", "name": b"Dana", "order": b"ORD-4502", "amount": b"18",
                                  "text": b"The sourdough arrived squished", "file": b"\x89PNG\r\n\x1a\n" + b"0" * 64})
        self.assertEqual(status, 200)
        self.assertIn("http-equiv=refresh", html)
