"""Try a message from the command line.

    python -m valerius "Grandma it's me, new number. I need $900 in gift cards today, don't tell mom"
    python -m valerius --webhook                     # run a fake WhatsApp webhook through intake
    python -m valerius --live "text"                 # also ask Muse Spark and the second pass (keys in .env)
    python -m valerius --live --image FILE "caption" # read an image with Muse Spark + SAM 3.1
    python -m valerius --live --voice FILE           # transcribe a voice note with Muse Voice Transcribe
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import pipeline, whatsapp
from .types import Message


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    live = "--live" in argv
    argv = [a for a in argv if a != "--live"]
    media, kind, audio_path = None, "text", ""
    for flag, k in (("--image", "image"), ("--voice", "audio")):
        if flag in argv:
            i = argv.index(flag)
            media, kind = Path(argv[i + 1]).read_bytes(), k
            audio_path = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    if argv and argv[0] == "--webhook":
        text = " ".join(argv[1:]) or "URGENT: your toll account is suspended. Pay the $4.99 fee at tolls-pay.xyz now"
        msgs = whatsapp.parse_webhook(whatsapp.fake_webhook(text))
    else:
        msgs = [Message(text=" ".join(argv), kind=kind)]
    mime = ""
    if kind == "audio":
        ext = Path(audio_path).suffix.lower()
        mime = {".wav": "audio/wav", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4", ".aac": "audio/aac", ".amr": "audio/amr"}.get(ext, "")
    for m in msgs:
        result = pipeline.run(m, use_models=live, media=media, media_mime=mime)
        print(pipeline.explain(result))
        if result.media:
            print("  media: " + ", ".join(f"{k}={v}" for k, v in result.media.items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
