"""Minimal OpenAI-compatible chat client (standard library only).

Used for Muse Spark on the Meta Model API and Muse Spark Open on Baseten.
Any failure is returned as an error string, never raised past the caller,
so the pipeline can treat it as "verification incomplete" and hold.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Reply:
    content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.content.strip())


def chat(base_url: str, api_key: str, model: str, messages: list[dict[str, str]], *,
         timeout: float = 45.0, extra: dict[str, Any] | None = None) -> Reply:
    if not api_key:
        return Reply(error="no API key configured")
    body: dict[str, Any] = {"model": model, "messages": messages}
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        return Reply(error=f"HTTP {e.code}: {detail}", seconds=time.monotonic() - start)
    except Exception as e:  # network, timeout, bad JSON
        return Reply(error=f"{type(e).__name__}: {e}", seconds=time.monotonic() - start)
    try:
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        if isinstance(content, list):  # some APIs return content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    except (KeyError, IndexError, TypeError):
        return Reply(error="unexpected response shape", raw=data, seconds=time.monotonic() - start)
    usage = data.get("usage") or {}
    return Reply(content=content, prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                 completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                 seconds=time.monotonic() - start, raw=data)
