import json
import unittest

from valerius import media, pipeline
from valerius.types import Message, Risk

SAM_REPLY = {"output": [{"type": "message", "content": [{"type": "output_text",
             "text": "<0f>0<|box;x1=269;y1=156;x2=412;y2=313;w=1600;h=1600|><|mask;x=0;y=0;data=abc|>"}]}]}
EMPTY_SAM = {"output": [{"type": "message", "content": [{"type": "output_text", "text": ""}]}]}
INVOICE = {"vendor_or_sender": "Brightline Plumbing Co.", "total_usd": 1280.0, "account_last4": "000123454471",
           "says_bank_details_changed": True, "asks_for_payment": True, "asks_for_gift_cards_or_crypto": False,
           "has_qr_code": False, "urgent_or_threatening": False, "links_or_domains": [],
           "visible_text_summary": "Invoice with new bank details"}


def fake_post(fields=INVOICE, fail=False):
    def post(path, payload):
        if fail:
            return {}, "HTTP 500: boom"
        if path == "/responses":
            return SAM_REPLY, ""
        return {"choices": [{"message": {"content": json.dumps(fields)}}]}, ""
    return post


class Sam(unittest.TestCase):
    def test_parse_boxes(self):
        self.assertEqual(media.parse_sam(SAM_REPLY), [[269, 156, 412, 313]])

    def test_no_match_is_empty(self):
        self.assertEqual(media.parse_sam(EMPTY_SAM), [])


class ImageReading(unittest.TestCase):
    def test_fields_cleaned_and_last4_only(self):
        r = media.read_image(b"\x89PNG\r\n\x1a\nxxxx", post=fake_post())
        self.assertEqual(r.error, "")
        self.assertEqual(r.fields["account_last4"], "4471")
        self.assertIn("logo", r.regions)

    def test_invoice_with_new_bank_details_is_critical(self):
        msg = Message(text="Is this invoice real? They want $1,280", kind="image")
        res = pipeline.run(msg, media=b"img", image_reader=lambda d: media.read_image(d, post=fake_post()))
        self.assertTrue(res.message.media_read)
        self.assertEqual(res.risk, Risk.CRITICAL)
        self.assertIn("image_payment_redirect", [f.rule for f in res.assessment.findings])
        self.assertFalse(any("not yet read" in g for g in res.assessment.incomplete))

    def test_amount_mismatch_between_image_and_message(self):
        fields = dict(INVOICE, says_bank_details_changed=False)
        msg = Message(text="They say I owe $300", kind="image")
        res = pipeline.run(msg, media=b"img", image_reader=lambda d: media.read_image(d, post=fake_post(fields)))
        self.assertIn("image_amount_mismatch", [f.rule for f in res.assessment.findings])

    def test_plain_receipt_image_passes_once_read(self):
        fields = dict(INVOICE, says_bank_details_changed=False, asks_for_payment=False, total_usd=32.1,
                      vendor_or_sender="Corner Market", account_last4=None)
        msg = Message(text="Thanks for your order! Your receipt for $32.10 is attached.", kind="image")
        res = pipeline.run(msg, media=b"img", image_reader=lambda d: media.read_image(d, post=fake_post(fields)))
        self.assertFalse(res.hold)

    def test_failed_reading_stays_unverified(self):
        msg = Message(text="look at this", kind="image")
        res = pipeline.run(msg, media=b"img", image_reader=lambda d: media.read_image(d, post=fake_post(fail=True)))
        self.assertTrue(res.hold)
        self.assertFalse(res.message.media_read)


class Voice(unittest.TestCase):
    def test_transcript_goes_through_the_rules(self):
        msg = Message(text="", kind="audio")
        said = "Grandma it's me, I lost my phone. I need $900 in gift cards right now, don't tell Mom."
        res = pipeline.run(msg, media=b"ogg", transcriber=lambda d: (said, ""))
        self.assertTrue(res.message.media_read)
        self.assertGreaterEqual(res.risk, Risk.HIGH)
        self.assertIn("[voice note]", res.message.text)

    def test_failed_transcription_holds(self):
        res = pipeline.run(Message(text="", kind="audio"), media=b"ogg", transcriber=lambda d: ("", "HTTP 500"))
        self.assertTrue(res.hold)

    def test_extract_transcript_shapes(self):
        self.assertEqual(media.extract_transcript({"text": "hi"}), "hi")
        self.assertEqual(media.extract_transcript({"turns": [{"text": "a"}, {"transcript": "b"}]}), "a b")


if __name__ == "__main__":
    unittest.main()
