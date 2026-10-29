"""The approval page: what was held, why, and the owner's rules, on one screen.

Everything from the message is escaped. Evidence is highlighted in place.
"""

from __future__ import annotations

from html import escape

from .config import SETTINGS

TOKEN_KEYS = ("c", "p", "e", "n", "s")  # only these fields are ever copied from a link into a form

CSS = """
:root{--bg:#f7f6f3;--card:#fff;--ink:#1c1b19;--muted:#6b6862;--line:#e6e3dc;--hold:#b4232c;--ok:#1d7a46;--mark:#fde68a;--accent:#2b4c7e}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1e1c;--ink:#f1efe9;--muted:#a19d94;--line:#34322e;--hold:#ef6a70;--ok:#5cc28b;--mark:#7a5d0c;--accent:#8fb0e6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:640px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:1.3rem;margin:0 0 4px}h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:22px 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-weight:600;font-size:.85rem;color:#fff;background:var(--hold)}
.pill.ok{background:var(--ok)}.muted{color:var(--muted)}
.msg{white-space:pre-wrap;word-wrap:break-word}mark{background:var(--mark);color:inherit;border-radius:3px;padding:0 2px}
ul{margin:0;padding-left:20px}li{margin:4px 0}
.row{display:flex;gap:10px;margin-top:16px}button{flex:1;font:inherit;font-weight:600;padding:14px;border-radius:10px;border:0;cursor:pointer}
.approve{background:var(--ok);color:#fff}.block{background:var(--hold);color:#fff}
.small{font-size:.85rem}code{font-size:.85rem}
"""


def _highlight(text: str, quotes: list[str]) -> str:
    spans: list[tuple[int, int]] = []
    for q in quotes:
        if not q:
            continue
        start = text.find(q)
        while start != -1:
            spans.append((start, start + len(q)))
            start = text.find(q, start + 1)
    spans.sort()
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, pos = [], 0
    for s, e in merged:
        out.append(escape(text[pos:s]))
        out.append(f"<mark>{escape(text[s:e])}</mark>")
        pos = e
    out.append(escape(text[pos:]))
    return "".join(out)


def _shell(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<meta name=robots content=noindex><title>{escape(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>")


def approval_page(case: dict, token: dict[str, str], record: dict[str, int],
                  agent_token: dict[str, str] | None = None, agent_paused: bool = False) -> str:
    quotes: list[str] = []
    for f in case.get("findings", []):
        quotes += [e["quote"] for e in f["evidence"] if e.get("quote")]
    for mr in case.get("model_reasons", {}).values():
        quotes += mr.get("quotes", [])

    held = case.get("status") == "held"
    status = f"<span class='pill{'' if held else ' ok'}'>{escape(str(case.get('status', '?')).upper())}</span>"
    action = ""
    if case.get("requested_action"):
        amt = f" of ${case['amount_usd']:,.2f}" if case.get("amount_usd") is not None else ""
        action = f"<p><b>Requested:</b> {escape(case['requested_action'].replace('_', ' '))}{escape(amt)}</p>"

    rules = "".join(
        f"<li>{escape(f['reason'])} <span class='muted small'>({escape(f['rule'])}, {escape(f['risk'])})</span>"
        + "".join(f"<br><span class='small muted'>record: <code>{escape(e['field'])} = {escape(e['value'])}</code></span>"
                  for e in f["evidence"] if e.get("field"))
        + "</li>" for f in case.get("findings", [])) or "<li class=muted>No rule fired.</li>"
    gaps = "".join(f"<li>Could not verify: {escape(g)}</li>" for g in case.get("unverified", []))
    models = "".join(
        f"<li><b>{escape(src)}</b>: {escape(case.get('models', {}).get(src, ''))} &middot; {escape('; '.join(mr.get('reasons', [])))}</li>"
        for src, mr in case.get("model_reasons", {}).items())
    disagree = "<p><b>The two model reviews disagree, so a person decides.</b></p>" if case.get("disagreement") else ""
    paused = "<p><b>The agent is paused.</b> Every requested action is held until you resume it.</p>" if case.get("paused_agent") else ""

    policy = ""
    if case.get("channel") == "business":
        lines = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
        policy = f"<h2>Your rules ({escape(SETTINGS.policy.business_name)})</h2><div class=card><ul>{lines}</ul></div>"

    buttons = ""
    if held:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(token.get(k, '')))}'>" for k in TOKEN_KEYS)
        buttons = (f"<form method=post action='/case/{escape(str(case.get('id', '')))}/decide'>{hidden}<div class=row>"
                   "<button class=approve name=decision value=approve>Approve</button>"
                   "<button class=block name=decision value=block>Block</button></div></form>"
                   "<p class='small muted'>This link works once and expires in 2 hours. Nothing happens until you choose.</p>")

    track = (f"<p class='small muted'>This agent so far: {record['held']} held, {record['approved']} approved, "
             f"{record['blocked']} blocked.</p>") if case.get("channel") == "business" else ""

    switch = ""
    if case.get("channel") == "business" and agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume agent", "resume") if agent_paused else ("Pause agent", "pause")
        note = ("The agent is paused: every requested action is held." if agent_paused
                else "Something wrong? Pausing holds every action the agent asks for until you resume it.")
        switch = (f"<h2>Agent</h2><div class=card><p class=small>{escape(note)}</p>"
                  f"<form method=post action='/agent/{path}'>{hidden}<button class=block>{verb}</button></form></div>")

    body = (f"<h1>Valerius review {status}</h1><p class=muted>Risk: <b>{escape(str(case.get('risk', '?')))}</b> &middot; case {escape(str(case.get('id', '')))}</p>"
            f"{paused}{action}<h2>The message</h2><div class='card msg'>{_highlight(case.get('text', ''), quotes)}</div>"
            f"<h2>Why it was held</h2><div class=card><ul>{rules}{gaps}</ul></div>"
            + (f"<h2>Model reviews</h2><div class=card>{disagree}<ul>{models}</ul></div>" if models or disagree else "")
            + f"{policy}{buttons}{track}{switch}"
            "<p class='small muted'>The model can advise. It can't approve. Personal details were removed before review.</p>")
    return _shell("Valerius review", body)


def result_page(title: str, detail: str) -> str:
    return _shell(title, f"<h1>{escape(title)}</h1><p>{escape(detail)}</p>")
