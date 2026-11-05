"""Secrets check: run before every commit and before the repo goes public.

    python scripts/check_secrets.py            # check every tracked + staged file
    python scripts/check_secrets.py --install  # add it as a git pre-commit hook

Exits 1 and lists file:line for anything that looks like a key, token, real
phone number or account ID. Benchmark data uses 555 numbers and fake IDs,
which are allowed.
"""

from __future__ import annotations

import hashlib

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_FILES = re.compile(r"(^|/)(\.env(\..*)?|webhook\.txt|.*\.pem|.*\.key|.*\.bundle|.*\.sqlite|.*\.db)$|^(state|secrets|private|real_data)/")
ALLOWED_FILES = {".env.example"}

PATTERNS = [
    ("Meta / Facebook access token", re.compile(r"\bEAA[A-Za-z0-9]{30,}")),
    ("OpenAI-style secret key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Slack/Discord webhook", re.compile(r"https://(hooks\.slack\.com|discord(app)?\.com/api/webhooks)/\S+")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Secret assigned in code", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{24,}['\"]")),
    # E.164 phone numbers that are not 555 test numbers
    ("Phone number", re.compile(r"\+?1[\s\-\.]?\(?(?!555)[2-9]\d{2}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b")),
    # WhatsApp/Meta numeric IDs are 15-17 digits
    ("Meta numeric ID", re.compile(r"(?<![\d.])\d{15,17}(?![\d.])")),
]

# Binary files a person checked frame by frame (no keys, links, codes or real customer data on screen), pinned by hash.
REVIEWED_BINARIES = {"demo/valerius-demo.mp4": "72e33e96105d77fca70a576dcf35576dca40b2a85068e9fa6e3ee52d62d34723"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ogg", ".mp3", ".wav", ".pdf", ".zip"}
SELF = "scripts/check_secrets.py"


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def scan(files: list[str]) -> list[str]:
    problems = []
    for f in files:
        if f in ALLOWED_FILES:
            continue
        if FORBIDDEN_FILES.search(f):
            problems.append(f"{f}: this file must never be committed")
            continue
        if f == SELF or Path(f).suffix.lower() in SKIP_SUFFIXES:
            continue
        path = ROOT / f
        if not path.is_file():
            continue
        if REVIEWED_BINARIES.get(f) == hashlib.sha256(path.read_bytes()).hexdigest():
            continue                     # checked by hand; any change to the file makes it fail again
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            problems.append(f"{f}: not a text file, so it can't be scanned; check it by hand or remove it")
            continue
        for n, line in enumerate(lines, 1):
            if "secrets-check: allow" in line:
                continue
            for label, pat in PATTERNS:
                if pat.search(line):
                    problems.append(f"{f}:{n}: looks like a {label}")
    return problems


def install_hook() -> None:
    hook = ROOT / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\npython scripts/check_secrets.py || exit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    print(f"Installed pre-commit hook at {hook}")


def main() -> int:
    if "--install" in sys.argv:
        install_hook()
        return 0
    problems = scan(tracked_files())
    if problems:
        print("SECRETS CHECK FAILED:")
        for p in problems:
            print("  " + p)
        print("Fix these before committing. If a line is a known-safe example, add the comment 'secrets-check: allow'.")
        return 1
    print("Secrets check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
