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
python -m valerius.server                            # webhook + approval pages on :8080
python scripts/verify_receipts.py                    # check every decision without trusting a model
python scripts/check_secrets.py
```

## How a held action works

1. A risky request is held. The customer gets a fixed holding message; nothing is improvised.
2. The owner gets a signed link that expires in 2 hours and works once.
3. The approval page shows the message with the evidence highlighted, why it was held, the model reviews, and the owner's own rules.
4. Approve or block. Every hold, decision, pause and resume writes a signed receipt chained to the one before.
5. `verify_receipts.py` reruns the rules on every case and checks the chain. No model is needed to check a decision.

The owner can also pause the agent: every action it asks for is then held until they resume it.

Copy `.env.example` to `.env` for keys. `.env` is gitignored.

## Data

All test and benchmark messages are synthetic. No real people's messages, phone numbers or accounts are used.

## Disclosure

A pre-event prototype existed (Oct 25, 2026). Nothing from it (code, data or numbers) is used in this repository; everything here was built during the event. The consumer side was renamed from "Scam Shield" because that name is already in use.
