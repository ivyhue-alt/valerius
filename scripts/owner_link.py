"""Print the owner's dashboard link (view-only, works for 7 days).

    python scripts/owner_link.py --base https://YOUR-APP.modal.run

The link is signed with SIGNING_SECRET from .env, so it must match the server's secret.
Treat it like a password: anyone with it can see the cases. Don't paste it in chats or commit it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius import act  # noqa: E402
from valerius.config import SETTINGS  # noqa: E402


def main(argv: list[str]) -> int:
    if not SETTINGS.signing_secret:
        print("SIGNING_SECRET is not set in .env, so the link would stop working when the server restarts.")
        return 1
    base = argv[argv.index("--base") + 1].rstrip("/") if "--base" in argv else SETTINGS.approval_base_url
    print(f"{base}/owner?{urlencode(act.dashboard_token())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
