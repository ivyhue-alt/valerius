"""Make the benchmark's image files once, with Muse Image, from the image_spec written on day 1.

    python scripts/make_benchmark_images.py

- Every name and brand in the specs is fictional, and the prompt says so.
- An image that already exists is never remade: no picking a "better" image after seeing results.
- Each file's SHA-256 goes into data/images/manifest.json, which is committed before the final run,
  so anyone can check the images weren't changed afterwards.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valerius.config import SETTINGS  # noqa: E402
from valerius.intake import sniff  # noqa: E402

OUT = ROOT / "data" / "images"
EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def existing(row_id: str) -> Path | None:
    for ext in EXT.values():
        p = OUT / f"{row_id}{ext}"
        if p.is_file():
            return p
    return None


def generate(spec: str) -> bytes:
    prompt = (f"A realistic phone photo or screenshot of: {spec}. Every company, brand and name in it is fictional. "
              "Any text in the image is clear and readable. No real brands, no real people.")
    body = json.dumps({"model": "muse-image-1.0", "prompt": prompt, "n": 1, "size": "1024x1024",
                       "response_format": "b64_json"}).encode()
    req = urllib.request.Request(SETTINGS.model_base_url.rstrip("/") + "/images/generations", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {SETTINGS.model_api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    return base64.b64decode(res["data"][0]["b64_json"])


def main() -> int:
    if not SETTINGS.model_api_key:
        print("MODEL_API_KEY is not set in .env")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(x) for x in (ROOT / "data" / "benchmark.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    for r in rows:
        if r.get("kind") != "image":
            continue
        path = existing(r["id"])
        if path is None:
            start = time.monotonic()
            try:
                data = generate(r["image_spec"])
            except (urllib.error.URLError, KeyError, IndexError, ValueError) as e:
                print(f"{r['id']}: failed ({type(e).__name__}); run again to retry this one")
                continue
            kind, mime = sniff(data)
            if kind != "image":
                print(f"{r['id']}: reply was not an image; run again to retry this one")
                continue
            path = OUT / f"{r['id']}{EXT[mime]}"
            path.write_bytes(data)
            print(f"{r['id']} ({r['split']}): made {path.name} in {time.monotonic() - start:.0f}s")
        else:
            print(f"{r['id']} ({r['split']}): already made, kept as is")
        manifest[r["id"]] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "model": "muse-image-1.0"}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Fingerprints saved in {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
