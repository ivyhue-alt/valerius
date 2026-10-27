"""Try a message from the command line.

    python -m valerius "Grandma it's me, new number. I need $900 in gift cards today, don't tell mom"
    python -m valerius --webhook       # run a fake WhatsApp webhook through intake
    python -m valerius --live "text"   # also ask Muse Spark and the second pass (needs keys in .env)
"""

from __future__ import annotations

import sys

from . import pipeline, whatsapp
from .types import Message


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    live = argv[0] == "--live"
    if live:
        argv = argv[1:]
    if argv and argv[0] == "--webhook":
        text = " ".join(argv[1:]) or "URGENT: your toll account is suspended. Pay the $4.99 fee at tolls-pay.xyz now"
        msgs = whatsapp.parse_webhook(whatsapp.fake_webhook(text))
    else:
        msgs = [Message(text=" ".join(argv))]
    for m in msgs:
        print(pipeline.explain(pipeline.run(m, use_models=live)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
