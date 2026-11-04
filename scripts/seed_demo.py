"""Fill the demo store with a believable morning of requests, through the store help page.

    python scripts/seed_demo.py --base https://YOUR-APP.modal.run

Sends made-up requests (from data/fresh_reseller.csv, with invented first names) through /help, exactly like a
customer on a phone would, so each one goes through the full loop: rules, Muse Spark, the second pass, and a hold
for the owner when it's risky. Uses INTAKE_CODE from .env and prints only the result of each request.
Everything here is synthetic. Each request uses model credits, so run it once before recording.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius.config import SETTINGS  # noqa: E402

# (first name, order, refund amount or "", what they wrote). The 12 candles request is left waiting on purpose.
REQUESTS = [
    ("Priya", "ORD-4471", "", "Where is my order? It was supposed to arrive yesterday."),
    ("Dee", "ORD-4475", "25", "My t-shirt has a stain, can I get a refund?"),
    ("Sam", "ORD-4480", "", "Can I swap this shirt for the same shirt in black?"),
    ("Lee", "ORD-4483", "", "Can I add a birthday message to my cake order for Saturday?"),
    ("Ana", "ORD-4486", "", "Do you have gluten free sourdough this weekend?"),
    ("Tasha", "ORD-4490", "480", "I want to return 12 candles, I ordered too many."),
]


def post(base: str, fields: dict[str, str]) -> int:
    b = uuid.uuid4().hex
    body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items())
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(f"{base}/help", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main(argv: list[str]) -> int:
    if "--base" not in argv:
        print(__doc__)
        return 1
    base = argv[argv.index("--base") + 1].rstrip("/")
    if not SETTINGS.intake_code:
        print("INTAKE_CODE is not set in .env.")
        return 1
    for name, order, amount, text in REQUESTS:
        status = post(base, {"code": SETTINGS.intake_code, "name": name, "order": order, "amount": amount, "text": text})
        print(f"{name}: {'sent' if status == 200 else f'failed ({status})'}")
    print("Done. Open your dashboard; the 12 candles request should be waiting for you.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
