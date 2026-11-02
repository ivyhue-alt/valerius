"""Put Valerius online on Modal so WhatsApp can reach the webhook.

    pip install modal python-dotenv
    modal token new
    modal deploy deploy/modal_app.py

Keys come from your local .env, uploaded to Modal as a Secret. They never go in the repo or the image.
Only the valerius/ package is copied into the image: no .env, no state/, no data/.
Cases and receipts live on a Modal Volume named valerius-state, so they survive restarts.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parent.parent

app = modal.App("valerius")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")  # turns WhatsApp voice notes (OGG) into the WAV that Transcribe accepts
    .pip_install("tzdata==2025.2")  # time zones for the store's business hours
    .add_local_dir(REPO / "valerius", "/root/valerius", ignore=["**/__pycache__/**", "**/*.pyc"])
)
volume = modal.Volume.from_name("valerius-state", create_if_missing=True)


@app.function(
    image=image,
    secrets=[modal.Secret.from_dotenv(REPO)],
    volumes={"/state": volume},
    max_containers=1,        # one server, so rate limits, duplicate checks and links stay consistent
    scaledown_window=1200,   # stay warm 20 minutes after the last message
)
@modal.concurrent(max_inputs=50)
@modal.web_server(8080, startup_timeout=60, label="valerius")
def web() -> None:
    env = dict(os.environ, HOST="0.0.0.0", PORT="8080", VALERIUS_STATE="/state", PYTHONUNBUFFERED="1")
    if "localhost" in env.get("APPROVAL_BASE_URL", "localhost"):
        try:
            env["APPROVAL_BASE_URL"] = web.get_web_url()  # links in alerts point at this server
        except Exception:
            pass
    print(f"approval links use {env.get('APPROVAL_BASE_URL')}")
    subprocess.Popen([sys.executable, "-m", "valerius.server"], cwd="/root", env=env)
