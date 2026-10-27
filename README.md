# Valerius

An independent supervisor for AI agents on WhatsApp. **The model can advise. It can't approve.**

- **Shift Lead** watches a business's AI agent and holds risky actions (big refunds, cancellations, payment or account changes) until the owner approves through a signed link outside the chat.
- **Valerius Family** lets anyone forward a suspicious message, voice note or screenshot and get a plain-language answer, with an alert to a trusted family member when money is at risk.

Built for the Meta Global AI Developer Hackathon (Indie Developer track), Oct 26 to Nov 4, 2026, on the Meta Model API.

> Status: in progress during the hackathon build window.

## The one rule

Deterministic rules set a risk floor. Muse Spark and the second pass can raise risk, never lower it. If any check can't run (missing record, unreadable image, model error), Valerius says so and holds.

## Run it (so far)

Python 3.10+, no dependencies yet.

```
python -m unittest discover -s tests
python -m valerius "Grandma it's me, new number. I need $900 in gift cards right now"
python -m valerius --webhook
python scripts/check_secrets.py
```

Copy `.env.example` to `.env` for keys. `.env` is gitignored.

## Data

All test and benchmark messages are synthetic. No real people's messages, phone numbers or accounts are used.

## Disclosure

A pre-event prototype existed (Oct 25, 2026). Nothing from it (code, data or numbers) is used in this repository; everything here was built during the event. The consumer side was renamed from "Scam Shield" because that name is already in use.
