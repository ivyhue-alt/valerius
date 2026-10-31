"""The web intake page: same loop as WhatsApp, guarded by an access code."""

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
