import unittest

from valerius import pipeline, redact, whatsapp
from valerius.types import Risk


class Redaction(unittest.TestCase):
    def test_card_kept_last4_only(self):
        out, counts = redact.redact("my card is 4111 1111 1111 1111 thanks")
        self.assertIn("[CARD ending 1111]", out)
        self.assertNotIn("4111 1111", out)
        self.assertEqual(counts["card"], 1)

    def test_other_long_numbers_keep_only_last4(self):
        out, _ = redact.redact("order 1234 5678 9012 3456 shipped")
        self.assertIn("[NUMBER ending 3456]", out)
        self.assertNotIn("1234 5678", out)

    def test_ssn_email_phone(self):
        out, counts = redact.redact("SSN 123-45-6789, mail me at a.b@example.com or call (555) 010-2030")
        for token in ("[SSN]", "[EMAIL]", "[PHONE]"):
            self.assertIn(token, out)
        self.assertNotIn("123-45-6789", out)

    def test_account_and_code(self):
        out, _ = redact.redact("routing 021000021 account number 000123456789, the code is 482913")
        self.assertIn("[ACCOUNT ending 6789]", out)
        self.assertIn("[CODE]", out)
        self.assertNotIn("482913", out)

    def test_money_amounts_kept(self):
        out, _ = redact.redact("send $1,200 now")
        self.assertIn("$1,200", out)


class Intake(unittest.TestCase):
    def test_text_roundtrip(self):
        msgs = whatsapp.parse_webhook(whatsapp.fake_webhook("hello there"))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].text, "hello there")
        self.assertTrue(msgs[0].forwarded)

    def test_image_caption(self):
        msgs = whatsapp.parse_webhook(whatsapp.fake_webhook(kind="image", caption="is this invoice real?"))
        self.assertEqual(msgs[0].kind, "image")
        self.assertEqual(msgs[0].text, "is this invoice real?")
        self.assertTrue(msgs[0].media_id)

    def test_voice_note_without_transcript_holds(self):
        msgs = whatsapp.parse_webhook(whatsapp.fake_webhook(kind="audio"))
        r = pipeline.run(msgs[0])
        self.assertTrue(r.hold)
        self.assertTrue(r.assessment.incomplete)

    def test_status_events_ignored(self):
        payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
            "statuses": [{"id": "x", "status": "failed"}]}}]}]}
        self.assertEqual(whatsapp.parse_webhook(payload), [])

    def test_end_to_end_fake_webhook_gets_risk(self):
        payload = whatsapp.fake_webhook("URGENT: your account will be suspended. Pay the $4.99 fee at tolls-pay.xyz now")
        r = pipeline.run(whatsapp.parse_webhook(payload)[0])
        self.assertGreaterEqual(r.risk, Risk.HIGH)


if __name__ == "__main__":
    unittest.main()
