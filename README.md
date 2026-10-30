# Valerius

An independent supervisor for AI agents on WhatsApp. **The model can advise. It can't approve.**

- **Shift Lead** watches a business's AI agent and holds risky actions (big refunds, cancellations, payment or account changes) until the owner approves through a signed link outside the chat.
- **Valerius Family** lets anyone forward a suspicious message, voice note or screenshot and get a plain-language answer, with an alert to a trusted family member when money is at risk.

Built for the Meta Global AI Developer Hackathon (Indie Developer track), Oct 26 to Nov 4, 2026, on the Meta Model API.

> Status: in progress during the hackathon build window.

## The one rule

Deterministic rules set a risk floor. Muse Spark and the second pass can raise risk, never lower it. If any check can't run (missing record, unreadable image, model error), Valerius says so and holds.

## Run it

Python 3.10+, standard library only.

```
python -m unittest discover -s tests                 # all tests, no keys needed
python -m valerius "Grandma it's me, new number. I need $900 in gift cards right now"
python -m valerius --live "..."                      # with Muse Spark + second pass (keys in .env)
python scripts/evaluate.py [--live]                  # benchmark, practice rows
python scripts/demo_business.py [--live]             # Shift Lead: fake owner asks for a $1,200 refund
python scripts/demo_business.py --serial             # Shift Lead: same customer's third damage claim in 40 days
python scripts/run_scenarios.py                      # repeat-claims scenarios (reported separately)
python -m valerius.server                            # webhook, web intake (/check) and approval pages on :8080
modal deploy deploy/modal_app.py                     # put it online (keys come from your .env as a Modal Secret)
python scripts/verify_receipts.py                    # check every decision without trusting a model
python scripts/check_secrets.py
```

## What runs where

Every model Valerius calls at runtime is a Meta model.

| Step | What does it | Kind |
|---|---|---|
| Judge the message (verdict, reasons, quotes) | Muse Spark 1.3, Meta Model API | Meta model call |
| Second pass that argues the opposite | Muse Spark Open, hosted on Baseten | Meta model call (same family, so it is a second opinion, not an independent review) |
| Read fixed fields from an image | Muse Spark (image input) | Meta model call |
| Locate logo, total, QR code, bank details in an image | SAM 3.1, Meta Model API | Meta model call |
| Voice note to text | Muse Voice Transcribe | Meta model call |
| Rules, redaction, holds, links, receipts | Python standard library | No model |
| Voice note format conversion (OGG to WAV) | ffmpeg | No model |
| Test images for the benchmark | Muse Image | Meta model call, test data only |
| Test voice file | Windows built-in speech | OS feature, test data only |

Valerius never speaks: there is no text-to-speech.

## WhatsApp, and the web intake page

The WhatsApp webhook is built and tested against Meta's webhook format, with signature checks, duplicate handling and media download. Delivering real WhatsApp messages needs Meta business verification and an app in Live mode, which a solo hackathon test number doesn't have. So people can also forward a message, screenshot or voice note through the web intake page (`/check`, behind an access code). It runs exactly the same loop: rules, both model reviews, hold, signed review link and receipt.

## How a held action works

1. A risky request is held. The customer gets a fixed holding message; nothing is improvised.
2. The owner gets a signed link that expires in 2 hours and works once.
3. The approval page shows the message with the evidence highlighted, why it was held, the model reviews, and the owner's own rules.
4. Approve or block. Every hold, decision, pause and resume writes a signed receipt chained to the one before.
5. `verify_receipts.py` reruns the rules on every case and checks the chain. No model is needed to check a decision.

The owner can also pause the agent: every action it asks for is then held until they resume it.

## Design choices

- **Verification is built in, not optional.** The rules and the hold run on every message; neither the agent nor a model can skip them.
- **Blocking where it matters, deferred where it doesn't.** Holds are blocking: a money action waits for a person. Receipts and the learn step are recorded after.
- **No retry loop past the gate.** Each model is asked once. If they disagree, fail, or a check can't run, the action is held; nothing loops until the models agree.
- **Allowlisted actions.** The supervised agent can only ask for refund, cancel, payment change or account change. Any other or invented action is blocked.
- **Valerius keeps the claim history the business doesn't.** Each customer's refund and reship claims are counted; past the owner's limit, the owner decides. Limits are per item and per request, so a business with larger orders isn't held on every claim.
- **Ground truth is the business's own record.** Claims are checked against the order record and the message's exact words, which are cited as evidence.

Copy `.env.example` to `.env` for keys. `.env` is gitignored.

## Data

All test and benchmark messages are synthetic. No real people's messages, phone numbers or accounts are used.

## Disclosure

A pre-event prototype existed (Oct 25, 2026). Nothing from it (code, data or numbers) is used in this repository; everything here was built during the event. The consumer side was renamed from "Scam Shield" because that name is already in use.
