"""The approval page: what was held, why, and the owner's rules, on one screen.

Everything from the message is escaped. Evidence is highlighted in place.
"""

from __future__ import annotations

from html import escape

from .config import SETTINGS

TOKEN_KEYS = ("c", "p", "e", "n", "s")  # only these fields are ever copied from a link into a form

CSS = """
:root{--paper:#eef1f6;--tag:#fff;--ink:#18213a;--soft:#5a6478;--rule:#d6dce6;--hold:#c0262d;--hold-bg:#fcecec;
--warn:#8f5400;--warn-bg:#fff2dc;--clear:#1e7f4f;--clear-bg:#e5f4ec;--act:#2f4fd8;--mark:#ffe27a;
--serif:Charter,"Bitstream Charter","Sitka Text",Cambria,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--paper:#0d1322;--tag:#161f36;--ink:#e8ecf4;--soft:#9aa3b8;--rule:#2a3550;
--hold:#f0707a;--hold-bg:#3a1a22;--warn:#f2b45a;--warn-bg:#3a2a12;--clear:#5cc79a;--clear-bg:#12301f;--act:#93a6ff;--mark:#6b5410}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 var(--sans);-webkit-text-size-adjust:100%}
main{max-width:600px;margin:0 auto;padding:18px 16px 120px}
a{color:var(--act);text-underline-offset:3px}
:focus-visible{outline:3px solid var(--act);outline-offset:2px}
h1{font:600 1.75rem/1.2 var(--serif);margin:6px 0 6px;letter-spacing:-.01em}
h2{font:600 1.1rem/1.3 var(--serif);margin:28px 0 10px}
p{margin:0 0 10px}.soft{color:var(--soft)}.small{font-size:.875rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:.875rem;color:var(--soft)}
.brand{font:600 1rem var(--serif);color:var(--ink)}
.state{display:inline-flex;align-items:center;gap:6px}.state::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--clear)}
.state.paused::before{background:var(--hold)}
.chip{display:inline-block;border-radius:6px;padding:1px 8px;font-size:.8rem;font-weight:600}
.r-hold{color:var(--hold);background:var(--hold-bg)}.r-warn{color:var(--warn);background:var(--warn-bg)}.r-clear{color:var(--clear);background:var(--clear-bg)}
.sheet{background:var(--tag);border:1px solid var(--rule);border-radius:12px;padding:14px 16px}
.tag{position:relative;background:var(--tag);border:1px solid var(--rule);border-radius:14px;padding:16px 16px 0 34px;margin:0 0 14px}
.tag::before{content:"";position:absolute;left:12px;top:20px;width:11px;height:11px;border-radius:50%;background:var(--paper);border:1px solid var(--rule)}
.tag .amt{font:700 1.45rem/1.2 var(--sans);font-variant-numeric:tabular-nums;margin:6px 0 2px}
.tag .why{color:var(--soft);font-size:.92rem}
.tag .foot{border-top:2px dashed var(--rule);margin:14px -16px 0 -34px;padding:12px 16px 14px 34px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.quote{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.95rem}
mark{background:var(--mark);color:inherit;border-radius:3px;padding:0 2px}
ul.plain{list-style:none;margin:0;padding:0}ul.plain li{padding:10px 0;border-top:1px solid var(--rule)}ul.plain li:first-child{border-top:0;padding-top:0}
ul.tags{list-style:none;margin:16px 0 0;padding:0}
ul.dots{margin:0;padding-left:20px}ul.dots li{margin:6px 0}
.rec{font-size:.85rem;color:var(--soft)}code{font-size:.85rem}
.log li{display:flex;gap:10px;align-items:baseline}.log .txt{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btn{display:inline-block;font:600 1rem var(--sans);padding:13px 18px;border-radius:10px;border:0;cursor:pointer;text-decoration:none;text-align:center}
.go{background:var(--act);color:#fff}
@media (prefers-color-scheme:dark){.go{color:#0d1322}}.approve{background:var(--clear);color:#fff}.block{background:var(--hold);color:#fff}
.ghost{background:transparent;color:var(--hold);border:1.5px solid var(--hold)}
.decide{position:fixed;left:0;right:0;bottom:0;background:var(--tag);border-top:1px solid var(--rule);padding:12px 16px calc(12px + env(safe-area-inset-bottom))}
.decide .in{max-width:600px;margin:0 auto}.decide .row{display:flex;gap:10px}.decide .btn{flex:1}
details summary{cursor:pointer;font:600 1.1rem var(--serif);margin:28px 0 10px}
textarea,input[type=password],input[type=text]{width:100%;font:inherit;padding:12px;border-radius:10px;border:1px solid var(--rule);background:var(--tag);color:var(--ink)}
label{display:block;font-weight:600;margin:18px 0 6px}
.verdict{border-radius:14px;padding:18px;margin:10px 0 16px}
.foot-note{margin-top:28px;font-size:.85rem;color:var(--soft)}
@media (prefers-reduced-motion:no-preference){.tag.new{animation:in .35s ease-out}@keyframes in{from{transform:translateY(6px);opacity:0}}}
"""


def _risk_class(risk: str) -> str:
    return {"CRITICAL": "r-hold", "HIGH": "r-hold", "MEDIUM": "r-warn"}.get(str(risk).upper(), "r-clear")


def _risk_label(risk: str) -> str:
    return {"CRITICAL": "Critical", "HIGH": "High risk", "MEDIUM": "Worth a look", "LOW": "Low risk"}.get(str(risk).upper(), str(risk))


def _chip(risk: str) -> str:
    return f"<span class='chip {_risk_class(risk)}'>{escape(_risk_label(risk))}</span>"


def _request(case: dict) -> str:
    act = (case.get("requested_action") or "").replace("_", " ")
    amt = case.get("amount_usd")
    if act and amt is not None:
        return f"{act.capitalize()} ${float(amt):,.2f}"
    if act:
        return act.capitalize()
    return "Forwarded message" if case.get("channel") == "family" else "Message"


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


def _shell(title: str, body: str, after: str = "") -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<meta name=robots content=noindex><meta name=theme-color content='#18213a'><title>{escape(title)}</title>"
            f"<style>{CSS}</style></head><body><main>{body}</main>{after}</body></html>")


def approval_page(case: dict, token: dict[str, str], record: dict[str, int],
                  agent_token: dict[str, str] | None = None, agent_paused: bool = False) -> str:
    quotes: list[str] = []
    for f in case.get("findings", []):
        quotes += [e["quote"] for e in f["evidence"] if e.get("quote")]
    for mr in case.get("model_reasons", {}).values():
        quotes += mr.get("quotes", [])

    held = case.get("status") == "held"

    rules = "".join(
        f"<li>{escape(f['reason'][:1].upper() + f['reason'][1:])} {_chip(f['risk'])}"
        + "".join(f"<div class=rec>Record: <code>{escape(e['field'])} = {escape(e['value'])}</code></div>"
                  for e in f["evidence"] if e.get("field"))
        + "</li>" for f in case.get("findings", [])) or "<li class=soft>No rule fired.</li>"
    gaps = "".join(f"<li>Couldn't check: {escape(g)}</li>" for g in case.get("unverified", []))
    names = {"muse-spark": "Muse Spark", "muse-spark-open": "Muse Spark Open (argues the other side)"}
    models = "".join(
        f"<li><b>{escape(names.get(src, src))}</b> {_chip(case.get('models', {}).get(src, ''))}"
        f"<div class=small>{escape('; '.join(mr.get('reasons', [])))}</div></li>"
        for src, mr in case.get("model_reasons", {}).items())
    disagree = ("<p class='chip r-warn'>The two reviews disagree, so you decide.</p>" if case.get("disagreement") else "")
    paused = ("<p class='sheet r-hold'><b>Your agent is paused.</b> Every action it asks for waits for you.</p>"
              if case.get("paused_agent") else "")

    media_card = ""
    fields = case.get("image_fields") or {}
    regions = (case.get("media") or {}).get("regions") or {}
    if fields or regions:
        from .textnorm import scrub_model_text
        rows = []
        if fields.get("vendor_or_sender"):
            rows.append(f"From {escape(scrub_model_text(fields['vendor_or_sender']))}")
        if fields.get("total_usd") is not None:
            rows.append(f"Total shown: ${float(fields['total_usd']):,.2f}")
        if fields.get("account_last4"):
            rows.append(f"Pay to account ending {escape(str(fields['account_last4']))}")
        if fields.get("visible_text_summary"):
            rows.append(f"Says: {escape(scrub_model_text(fields['visible_text_summary']))}")
        found = [p for p, boxes in regions.items() if boxes]
        if found:
            rows.append("Found in the picture: " + escape(", ".join(found)))
        media_card = ("<h2>What the picture shows</h2><div class=sheet><ul class=plain>"
                      + "".join(f"<li>{r}</li>" for r in rows) +
                      "</ul><p class='small soft' style='margin-top:10px'>Read by Muse Spark and SAM 3.1. "
                      "Instructions written inside images are ignored.</p></div>")

    policy = ""
    if case.get("channel") == "business":
        lines = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
        policy = f"<details><summary>Your rules</summary><div class=sheet><ul class=dots>{lines}</ul></div></details>"

    decide_bar = ""
    if held:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(token.get(k, '')))}'>" for k in TOKEN_KEYS)
        decide_bar = (f"<form class=decide method=post action='/case/{escape(str(case.get('id', '')))}/decide'>{hidden}"
                      "<div class=in><div class=row>"
                      "<button class='btn approve' name=decision value=approve>Approve</button>"
                      "<button class='btn block' name=decision value=block>Block</button></div>"
                      "<p class='small soft' style='margin:8px 0 0;text-align:center'>Nothing happens until you choose. "
                      "This link works once and expires in 2 hours.</p></div></form>")

    track = (f"<p class='small soft'>This agent so far: {record['held']} held, {record['approved']} approved, "
             f"{record['blocked']} blocked.</p>") if case.get("channel") == "business" else ""

    switch = ""
    if case.get("channel") == "business" and agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume agent", "resume") if agent_paused else ("Pause agent", "pause")
        note = ("Your agent is paused. Every action it asks for waits for you." if agent_paused
                else "Something feels off? Pausing makes every action the agent asks for wait for you.")
        switch = (f"<h2>Your agent</h2><div class=sheet><p class=small>{escape(note)}</p>"
                  f"<form method=post action='/agent/{path}'>{hidden}<button class='btn ghost'>{verb}</button></form></div>")

    state = "Waiting for you" if held else str(case.get("status", "")).capitalize()
    body = (f"<div class=top><span class=brand>Valerius</span><span>Case {escape(str(case.get('id', '')))}</span></div>"
            f"<div class='tag new'><div>{_chip(case.get('risk', ''))} <span class='small soft'>{escape(state)}</span></div>"
            f"<div class=amt>{escape(_request(case))}</div>"
            f"<div class=foot><div class=quote>{_highlight(case.get('text', ''), quotes)}</div></div></div>"
            f"{paused}<h2>Why it was held</h2><div class=sheet><ul class=plain>{rules}{gaps}</ul></div>"
            + (f"<h2>Two model reviews</h2><div class=sheet>{disagree}<ul class=plain>{models}</ul></div>" if models or disagree else "")
            + f"{media_card}{policy}{track}{switch}"
            "<p class=foot-note>The models advise. Only you approve. Personal details were removed before review.</p>")
    return _shell("Valerius review", body, decide_bar)


def result_page(title: str, detail: str) -> str:
    return _shell(title, f"<div class=top><span class=brand>Valerius</span></div><h1>{escape(title)}</h1><p>{escape(detail)}</p>")


def intake_form(error: str = "") -> str:
    err = f"<p class='sheet r-hold'>{escape(error)}</p>" if error else ""
    body = (
        "<div class=top><span class=brand>Valerius</span></div>"
        "<h1>Got a message that feels off?</h1>"
        "<p class=soft>Paste it here, or add the screenshot or voice note. You'll get a plain answer in about 15 seconds.</p>"
        + err +
        "<form method=post action='/check' enctype='multipart/form-data'>"
        "<label for=t>The message</label><textarea id=t name=text rows=6 maxlength=4000 "
        "placeholder='Paste what they sent you'></textarea>"
        "<label for=f>Screenshot or voice note <span class=soft>(optional)</span></label>"
        "<input id=f type=file name=file accept='image/jpeg,image/png,image/webp,audio/*'>"
        "<label for=c>Access code</label><input id=c name=code type=password autocomplete=off required>"
        "<p style='margin-top:20px'><button class='btn go' style='width:100%'>Check this message</button></p></form>"
        "<p class=foot-note>Personal details are removed before review. Use made-up or test messages only.</p>")
    return _shell("Valerius check", body)


def intake_result(risk: str, held: bool, reply: str, link: str = "") -> str:
    tone = _risk_class(risk) if (held or str(risk).upper() != "LOW") else "r-clear"
    head = {"r-hold": "Don't act on this yet", "r-warn": "Be careful with this one"}.get(tone, "No common scam signs")
    review = (f"<p><a class='btn go' href='{escape(link)}'>See the evidence</a></p>"
              "<p class='small soft'>That page shows what was found and lets you approve or block. "
              "The link works once and expires in 2 hours.</p>") if held and link else ""
    body = ("<div class=top><span class=brand>Valerius</span></div>"
            f"<div class='verdict {tone}'><h1 style='margin:0 0 8px'>{escape(head)}</h1><p style='margin:0;color:var(--ink)'>{escape(reply)}</p></div>"
            f"{review}<p><a href='/check'>Check another message</a></p>")
    return _shell("Valerius check", body)


def owner_dashboard(cases: list[dict], record: dict[str, int], review_links: dict[str, str],
                    agent_token: dict[str, str] | None, agent_paused: bool) -> str:
    """The owner's phone view: what's waiting, what was decided, and the pause switch."""
    import time as _time
    from .textnorm import scrub_model_text

    def when(ts) -> str:
        try:
            mins = max(0, int((_time.time() - int(ts)) // 60))
        except (TypeError, ValueError):
            return ""
        return "just now" if mins < 1 else f"{mins} min ago" if mins < 60 else \
            f"{mins // 60} h ago" if mins < 1440 else f"{mins // 1440} d ago"

    def reason(c: dict) -> str:
        return (c.get("findings") or [{}])[0].get("reason", "") or ("couldn't check everything" if c.get("unverified") else "")

    def tag(c: dict) -> str:
        link = review_links.get(c.get("id", ""))
        snippet = scrub_model_text(str(c.get("text", "")))[:110]
        go = f"<a class='btn go' href='{escape(link)}'>Review</a>" if link else ""
        return (f"<li class=tag><div>{_chip(c.get('risk', ''))} <span class='small soft'>{escape(when(c.get('created_at')))}</span></div>"
                f"<div class=amt>{escape(_request(c))}</div><div class=why>{escape(reason(c).capitalize())}</div>"
                f"<div class=foot><span class='small soft' style='flex:1;min-width:0'>&ldquo;{escape(snippet)}&rdquo;</span>{go}</div></li>")

    def logrow(c: dict) -> str:
        outcome = {"approved": "Approved", "blocked": "Blocked", "allowed": "Passed"}.get(str(c.get("status")), str(c.get("status")))
        tone = {"Blocked": "r-hold", "Approved": "r-clear", "Passed": "r-clear"}.get(outcome, "r-warn")
        return (f"<li><span class='chip {tone}'>{escape(outcome)}</span>"
                f"<span class=txt>{escape(_request(c))}: {escape(scrub_model_text(str(c.get('text', '')))[:70])}</span>"
                f"<span class='small soft'>{escape(when(c.get('created_at')))}</span></li>")

    waiting = [c for c in cases if c.get("status") == "held"]
    done = [c for c in cases if c.get("status") != "held"][:15]
    n = len(waiting)
    headline = ("Nothing is waiting for you" if n == 0 else
                "1 hold is waiting for you" if n == 1 else f"{n} holds are waiting for you")
    waiting_html = (f"<ul class=tags>{''.join(tag(c) for c in waiting)}</ul>" if waiting else
                    "<p class=soft>Your agent is handling everything within your rules. Holds show up here.</p>")
    done_html = (f"<div class=sheet><ul class='plain log'>{''.join(logrow(c) for c in done)}</ul></div>" if done else
                 "<p class=soft>Nothing handled yet.</p>")

    switch = ""
    if agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume agent", "resume") if agent_paused else ("Pause agent", "pause")
        note = ("Paused. Every action your agent asks for waits for you." if agent_paused else
                "Something feels off? Pausing makes every action your agent asks for wait for you.")
        switch = (f"<h2>Your agent</h2><div class=sheet><p class=small>{escape(note)}</p>"
                  f"<form method=post action='/agent/{path}'>{hidden}<button class='btn ghost'>{verb}</button></form></div>")
    rules = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
    state = (f"<span class='state paused'>Agent paused</span>" if agent_paused else "<span class=state>Agent running</span>")
    body = (f"<div class=top><span class=brand>{escape(SETTINGS.policy.business_name)}</span>{state}</div>"
            f"<h1>{escape(headline)}</h1>"
            f"<p class='small soft'>So far: {record.get('approved', 0)} approved, {record.get('blocked', 0)} blocked.</p>"
            f"{waiting_html}<h2>Recently handled</h2>{done_html}{switch}"
            f"<details><summary>Your rules</summary><div class=sheet><ul class=dots>{rules}</ul></div></details>"
            "<p class=foot-note>This page refreshes every 30 seconds and only shows. "
            "Approve and Block happen on each case's own page, with a link that works once.</p>")
    html = _shell("Valerius", body)
    return html.replace("<meta name=robots content=noindex>",
                        "<meta name=robots content=noindex><meta http-equiv=refresh content=30>"
                        "<meta name=apple-mobile-web-app-capable content=yes>", 1)
