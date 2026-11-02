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
@media (prefers-color-scheme:dark){:root{--paper:#0d1322;--tag:#161f36;--ink:#eef1f7;--soft:#bcc4d4;--rule:#2a3550;
--hold:#f0707a;--hold-bg:#3a1a22;--warn:#f2b45a;--warn-bg:#3a2a12;--clear:#5cc79a;--clear-bg:#12301f;--act:#93a6ff;--mark:#6b5410}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.5 var(--sans);-webkit-text-size-adjust:100%}
main{max-width:600px;margin:0 auto;padding:18px 16px 120px}
a{color:var(--act);text-underline-offset:3px}
:focus-visible{outline:3px solid var(--act);outline-offset:2px}
h1{font:700 1.6rem/1.2 var(--sans);margin:6px 0 6px;letter-spacing:-.01em}
h2{font:600 1rem/1.3 var(--sans);color:var(--soft);margin:28px 0 10px}
p{margin:0 0 10px}.soft{color:var(--soft)}.small{font-size:.875rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:.875rem;color:var(--soft)}
.brand{font:700 1rem var(--sans);color:var(--ink)}
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
@media (prefers-color-scheme:dark){.go,.approve,.block,.urgent{color:#0d1322}}.approve{background:var(--clear);color:#fff}.block{background:var(--hold);color:#fff}
.ghost{background:transparent;color:var(--hold);border:1.5px solid var(--hold)}
.decide{position:fixed;left:0;right:0;bottom:0;background:var(--tag);border-top:1px solid var(--rule);padding:12px 16px calc(12px + env(safe-area-inset-bottom))}
.decide .in{max-width:600px;margin:0 auto}.decide .row{display:flex;gap:10px}.decide .btn{flex:1}
details summary{cursor:pointer;font:600 1rem var(--sans);color:var(--soft);margin:28px 0 10px}
textarea,input[type=password],input[type=text]{width:100%;font:inherit;padding:12px;border-radius:10px;border:1px solid var(--rule);background:var(--tag);color:var(--ink)}
label{display:block;font-weight:600;margin:18px 0 6px}
.verdict{border-radius:14px;padding:18px;margin:10px 0 16px}
.foot-note{margin-top:28px;font-size:.85rem;color:var(--soft)}
.facts{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:12px 0 0;font-size:.95rem}
.facts dt{color:var(--soft)}.facts dd{margin:0;font-weight:600}
.then{display:grid;gap:8px;margin:0}.then div{border-radius:10px;padding:10px 12px;font-size:.95rem}
.then b{display:block;font-size:.85rem;margin-bottom:2px}.then span{color:var(--ink)}
.timeline{list-style:none;margin:0;padding:0 0 0 14px;border-left:2px solid var(--rule)}
.timeline li{position:relative;padding:4px 0 10px 10px;font-size:.95rem}
.timeline li::before{content:"";position:absolute;left:-21px;top:10px;width:10px;height:10px;border-radius:50%;background:var(--rule)}
.timeline li.now::before{background:var(--hold)}
.evidence{position:relative;border-radius:12px;overflow:hidden;border:1px solid var(--rule);background:#000}
.evidence img,.evidence svg{display:block;width:100%;height:auto}.evidence svg{position:absolute;inset:0}
.verdict-line{font-weight:600;margin:0 0 8px}
.tabs{display:flex;gap:6px;margin:14px 0 6px}.tabs a{padding:8px 14px;border-radius:999px;text-decoration:none;color:var(--ink);border:1px solid var(--rule);font-size:.9rem}
.tabs a.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.urgent{background:var(--hold);color:#fff}
.thread{display:flex;flex-direction:column;gap:8px;margin:14px 0 0}
.from{font-size:.8rem;color:var(--soft);margin:6px 0 0 4px}
.bubble{background:var(--tag);border:1px solid var(--rule);border-radius:20px 20px 20px 6px;padding:11px 15px;max-width:92%;
font-size:1.05rem;line-height:1.45;align-self:flex-start}
.bubble.big{font-size:1.2rem;font-weight:600}
.bubble.photo{padding:4px;overflow:hidden}.bubble.photo .evidence{border:0;border-radius:16px}
.quoted{align-self:flex-start;max-width:92%;border-left:3px solid var(--rule);padding:4px 0 4px 12px;margin:2px 0 2px 6px;
color:var(--soft);font-size:.95rem}
.quoted .quote{color:var(--ink)}
.bubble.urgent-edge{border-left:4px solid var(--hold)}
.inbox{list-style:none;margin:16px 0 0;padding:0;display:flex;flex-direction:column;gap:10px}
.inbox a.item{display:block;text-decoration:none;color:var(--ink)}
.when{font-size:.8rem;color:var(--soft);margin:2px 0 0 6px}
.receipt{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.85rem;overflow-wrap:anywhere}
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



def _money(x) -> str:
    return f"${float(x):,.2f}"


def _fee(amount) -> float:
    p = SETTINGS.policy
    return round(float(amount) * p.processor_fee_pct / 100 + p.processor_fee_usd, 2)


def _ago(ts, now: int | None = None) -> str:
    import time as _time
    try:
        mins = max(0, int(((now or _time.time()) - int(ts)) // 60))
    except (TypeError, ValueError):
        return ""
    return "just now" if mins < 1 else f"{mins} min ago" if mins < 60 else \
        f"{mins // 60} h ago" if mins < 1440 else f"{mins // 1440} days ago"


def _date(ts) -> str:
    import datetime as _dt
    try:
        return _dt.datetime.fromtimestamp(int(ts), _dt.timezone.utc).strftime("%b %-d, %Y")
    except (TypeError, ValueError, OSError):
        return ""


def _consequences(case: dict) -> tuple[str, str]:
    """What happens if the owner approves, and if they block. Plain words, estimates labelled."""
    act = case.get("requested_action", "")
    amt = case.get("amount_usd")
    if case.get("channel") == "family":
        return ("You've checked it yourself and it's safe. Nothing else happens.",
                "It stays marked as a scam. Nothing is sent and no money moves.")
    block = "No money moves. Your agent tells the customer a team member will follow up."
    if act == "refund" and amt is not None:
        return (f"{_money(amt)} goes back to the customer. Your card processor usually keeps its fee on the original "
                f"sale, about {_money(_fee(amt))} (estimate).", block)
    if act == "reship" and amt is not None:
        return (f"A replacement worth {_money(amt)} ships out, plus your shipping cost.", block)
    if act == "cancel":
        extra = f" If the payment was already taken, the processor fee (about {_money(_fee(amt))}) usually isn't returned." \
            if amt is not None else ""
        return ("The order is canceled." + extra, "The order stays as it is. " + block)
    if act == "payment_change":
        return ("The customer's payment details change. If this is a takeover, the next charge goes to someone else.", block)
    if act == "account_change":
        return ("The customer's account details change, including where codes and receipts go.", block)
    return ("Your agent goes ahead with the request.", block)


def _review_line(case: dict) -> str:
    models = case.get("models", {}) or {}
    a, b = models.get("muse-spark"), models.get("muse-spark-open")
    if not (a and b):
        return "Only one review could run, so you decide." if (a or b) else ""
    hold = {"HIGH", "CRITICAL"}
    if case.get("disagreement"):
        return "The two reviews disagree. One says hold, the other says it may be honest. You decide."
    if a in hold and b in hold:
        return "Both reviews say hold."
    if a not in hold and b not in hold:
        return "Both reviews found no strong sign of fraud. Your rules held it."
    return "The reviews lean different ways, so you decide."


def _evidence_image(case: dict) -> str:
    prev = (case.get("media") or {}).get("preview") or {}
    if not prev.get("b64") or prev.get("mime") not in ("image/png", "image/jpeg", "image/webp"):
        return ""
    w, h = int(prev.get("w", 0)), int(prev.get("h", 0))
    if not (w and h):
        return ""
    names = {"bank account details": "Bank details", "total amount": "Total", "QR code": "QR code", "logo": "Logo"}
    shapes = []
    for prompt, boxes in ((case.get("media") or {}).get("regions") or {}).items():
        for box in boxes or []:
            try:
                x1, y1, x2, y2 = (float(v) for v in box)
            except (TypeError, ValueError):
                continue
            label = escape(names.get(prompt, prompt))
            sw = max(w, h) / 220
            shapes.append(f"<rect x='{x1:.0f}' y='{y1:.0f}' width='{x2 - x1:.0f}' height='{y2 - y1:.0f}' fill='none' "
                          f"stroke='#ffd23f' stroke-width='{sw:.1f}' rx='{sw * 2:.1f}'/>"
                          f"<rect x='{x1:.0f}' y='{max(0, y1 - sw * 11):.0f}' width='{sw * (len(label) * 5.4 + 8):.0f}' "
                          f"height='{sw * 10:.0f}' fill='#ffd23f' rx='{sw:.1f}'/>"
                          f"<text x='{x1 + sw * 4:.0f}' y='{max(0, y1 - sw * 11) + sw * 7.4:.0f}' font-size='{sw * 7.5:.0f}' "
                          f"font-family='system-ui,sans-serif' font-weight='700' fill='#18213a'>{label}</text>")
    svg = f"<svg viewBox='0 0 {w} {h}' aria-hidden=true>{''.join(shapes)}</svg>" if shapes else ""
    return (f"<div class=evidence><img alt='The picture that was sent' src='data:{prev['mime']};base64,{prev['b64']}'>{svg}</div>"
            "<p class='small soft' style='margin-top:8px'>Yellow boxes: where SAM 3.1 found each item. "
            "Instructions written inside images are ignored.</p>")


def approval_page(case: dict, token: dict[str, str], record: dict[str, int],
                  agent_token: dict[str, str] | None = None, agent_paused: bool = False,
                  history: list[dict] | None = None, now: int | None = None) -> str:
    """One hold, written like a note from a trusted shift lead, with the decision at the thumb."""
    import time as _time
    from . import voice
    now = now or int(_time.time())
    quotes: list[str] = []
    for f in case.get("findings", []):
        quotes += [e["quote"] for e in f["evidence"] if e.get("quote")]
    for mr in case.get("model_reasons", {}).values():
        quotes += mr.get("quotes", [])
    held = case.get("status") == "held"
    amt = case.get("amount_usd")
    fee = _fee(amt) if amt is not None and case.get("requested_action") in ("refund", "cancel") else None

    bubbles = [f"<div class='bubble big{' urgent-edge' if case.get('risk') == 'CRITICAL' else ''}'>"
               f"{escape(voice.opener(case))} {escape(voice.ask(case) if case.get('channel') == 'business' else "Someone sent you this, and I think it's a scam.")}</div>"]
    photo = _evidence_image(case)
    if photo:
        bubbles.append(f"<div class='bubble photo'>{photo.split('<p class=')[0]}</div>")
    if case.get("text", "").strip():
        who = "They wrote" if case.get("channel") == "business" else "The message says"
        bubbles.append(f"<div class=quoted>{who}:<div class=quote>{_highlight(case.get('text', ''), quotes)}</div></div>")
    bubbles.append(f"<div class=bubble>{escape(voice.because(case))}</div>")
    claims = [h for h in (history or []) if h.get("is_claim")]
    if case.get("channel") == "business" and claims:
        bubbles.append(f"<div class=bubble>For context, they've made {len(claims)} other claim"
                       f"{'s' if len(claims) != 1 else ''} in the last two years. It's all under Their history below.</div>")
    if held:
        bubbles.append(f"<div class=bubble>If you say yes, {escape(voice.if_yes(case, fee))} "
                       f"If you say no, {escape(voice.if_no(case))}</div>")
    if case.get("paused_agent"):
        bubbles.append("<div class=bubble>Your agent is paused right now, so I'm holding everything it asks for.</div>")

    timeline = ""
    if case.get("channel") == "business" and case.get("customer_id"):
        items = "".join(
            f"<li>{escape(_date(h['at']))}: {escape((h['action'] or 'message').replace('_', ' '))}"
            + (f" {_money(h['amount_usd'])}" if h.get("amount_usd") is not None else "")
            + f", {escape(h['status'])}</li>" for h in (history or [])[-8:])
        items += f"<li class=now>Today: {escape(_request_lower(case))}, waiting on you</li>" if held else ""
        timeline = (f"<details><summary>Their history</summary><div class=sheet><ul class=timeline>{items}</ul>"
                    f"<p class='small soft' style='margin:6px 0 0'>Your limit is {SETTINGS.policy.max_claims} claims in "
                    f"{SETTINGS.policy.claim_window_days} days. I keep two years of history.</p></div></details>")

    model_lines = "".join(
        f"<li><b>{'Muse Spark' if src == 'muse-spark' else 'Second check, which argues the other side'}</b> "
        f"{_chip(case.get('models', {}).get(src, ''))}<div class=small>{escape((mr.get('reasons') or [''])[0])}</div></li>"
        for src, mr in case.get("model_reasons", {}).items())
    rules_fired = "".join(f"<li>{escape(f['rule'].replace('_', ' '))} {_chip(f['risk'])}</li>" for f in case.get("findings", []))
    how = (f"<details><summary>How I checked</summary><div class=sheet>"
           f"<p class=verdict-line>{escape(_review_line(case) or 'Your rules held it.')}</p>"
           f"<ul class=plain>{model_lines}</ul>"
           + (f"<p class='small soft' style='margin:10px 0 4px'>Rules that fired</p><ul class=dots>{rules_fired}</ul>" if rules_fired else "")
           + "</div></details>")

    decide_bar = ""
    if held:
        yes, no = voice.buttons(case)
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(token.get(k, '')))}'>" for k in TOKEN_KEYS)
        try:
            left = max(0, int(token.get("e", 0)) - now) // 60
        except ValueError:
            left = 0
        expires = f"{left // 60} h {left % 60} min" if left >= 60 else f"{left} min"
        decide_bar = (f"<form class=decide method=post action='/case/{escape(str(case.get('id', '')))}/decide'>{hidden}"
                      "<div class=in><div class=row>"
                      f"<button class='btn approve' name=decision value=approve>{escape(yes)}</button>"
                      f"<button class='btn block' name=decision value=block>{escape(no)}</button></div>"
                      f"<p class=small style='margin:8px 0 0;text-align:center'>This link works once, for {escape(expires)} more.</p>"
                      "</div></form>")

    switch = ""
    if case.get("channel") == "business" and agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume my agent", "resume") if agent_paused else ("Pause my agent", "pause")
        switch = (f"<details><summary>Something feels off?</summary><div class=sheet><p class=small>Pause your agent and "
                  f"I'll hold everything it asks for until you turn it back on.</p>"
                  f"<form method=post action='/agent/{path}'>{hidden}<button class='btn ghost'>{verb}</button></form></div></details>")
    policy = ""
    if case.get("channel") == "business":
        lines = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
        policy = f"<details><summary>Your rules</summary><div class=sheet><ul class=dots>{lines}</ul></div></details>"

    name = SETTINGS.policy.business_name if case.get("channel") == "business" else "Valerius"
    body = (f"<div class=top><span class=brand>{escape(name)}</span><span>{escape(_ago(case.get('created_at'), now))}</span></div>"
            f"{'<div class=from>From Valerius</div>' if name != 'Valerius' else ''}<div class=thread>{''.join(bubbles)}</div>"
            f"{timeline}{how}{policy}{switch}"
            "<p class=foot-note>I check, you decide. Personal details were taken out before anything was reviewed.</p>")
    return _shell("Valerius", body, decide_bar)


def _evidence_label(field: str, value: str) -> str:
    if field.startswith("image."):
        name = field[6:].replace("_", " ")
        if value in ("True", "true"):
            return f"In the picture: {escape(name.replace('has ', ''))}"
        return f"In the picture: {escape(name)} {escape(value)}"
    return f"On record: {escape(field.replace('_', ' '))} {escape(value)}"


def _request_lower(case: dict) -> str:
    r = _request(case)
    return r[:1].lower() + r[1:]


def receipt_page(case: dict, receipt: dict | None) -> str:
    """After a decision: a short note the owner can show staff or a customer."""
    import time as _time
    from . import voice
    status = str(case.get("status", ""))
    fee = _fee(case["amount_usd"]) if case.get("amount_usd") is not None and case.get("requested_action") in ("refund", "cancel") else None
    result = voice.if_yes(case, fee) if status == "approved" else voice.if_no(case)
    result = result[:1].upper() + result[1:]
    proof = ""
    if receipt:
        proof = (f"<details><summary>Proof</summary><div class=sheet><p class=small>This is receipt {escape(str(receipt.get('seq', '')))}. "
                 f"Each receipt locks in the one before it, so nobody can quietly change the history. "
                 f"Anyone can recheck it with the rules alone.</p>"
                 f"<p class=receipt>{escape(str(receipt.get('hash', '')))}</p></div></details>")
    body = (f"<div class=top><span class=brand>Valerius</span><span>{escape(_date(_time.time()))}</span></div>"
            f"<div class=thread>"
            f"<div class='bubble big'>Done. {escape(voice.done(case))}</div>"
            f"<div class=bubble>{escape(result)}</div>"
            + (f"<div class=quoted>What {escape(voice.who(case))} got:<div class=quote>{escape(case['customer_note'])}</div></div>"
               if case.get("customer_note") else "")
            + f"<div class=bubble>I saved a receipt, in case anyone asks later.</div></div>"
            f"{proof}<p class=foot-note>You can close this page.</p>")
    return _shell("Valerius receipt", body)


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
                    agent_token: dict[str, str] | None, agent_paused: bool, view: str = "waiting",
                    tab_query: str = "", claim_counts: dict[str, int] | None = None) -> str:
    """The owner's phone view: like a text thread from a shift lead. Waiting first; history on its own tab."""
    from . import voice

    def note(c: dict) -> str:
        if c.get("channel") == "business":
            first = voice.ask(c)
        else:
            first = "Someone sent a message that looks like a scam."
        r = voice.reasons(c, limit=1)
        line = f"{first} {r[0][:1].upper() + r[0][1:]}." if r else first
        link = review_links.get(c.get("id", ""))
        urgent = c.get("risk") == "CRITICAL"
        inner = (f"<div class='bubble{' urgent-edge' if urgent else ''}' style='max-width:100%'>"
                 f"{'<b>Needs you now.</b> ' if urgent else ''}{escape(line)}</div>"
                 f"<div class=when>{escape(_ago(c.get('created_at')))}{', tap to decide' if link else ''}</div>")
        return f"<li><a class=item href='{escape(link)}'>{inner}</a></li>" if link else f"<li>{inner}</li>"

    def past(c: dict) -> str:
        status = str(c.get("status"))
        if status == "allowed":
            text = f"{voice.ask(c)[:-1] if c.get('channel') == 'business' else 'A message came in'}, and it was within your rules, so your agent handled it."
            if c.get("channel") == "business" and not c.get("requested_action"):
                text = "A customer asked a question, and your agent handled it."
        else:
            yes, no = voice.buttons(c)
            said = yes if status == "approved" else no
            text = f"{voice.ask(c) if c.get('channel') == 'business' else 'A possible scam came in.'} You chose: {said}."
        return f"<li><div class=bubble style='max-width:100%'>{escape(text)}</div><div class=when>{escape(_ago(c.get('created_at')))}</div></li>"

    cases = [c for c in cases if c.get("channel") == "business"]  # family scam alerts go to the family contact, not the store
    waiting = sorted([c for c in cases if c.get("status") == "held"],
                     key=lambda c: (c.get("risk") != "CRITICAL", -int(c.get("created_at", 0))))
    done = [c for c in cases if c.get("status") != "held"][:30]
    n = len(waiting)
    words = ["Nothing", "One thing", "Two things", "Three things", "Four things", "Five things", "Six things",
             "Seven things", "Eight things", "Nine things"]
    headline = "Nothing needs you right now." if n == 0 else f"{words[n] if n < 10 else str(n) + ' things'} need{'s' if n == 1 else ''} you."
    q = escape(tab_query)
    tabs = (f"<nav class=tabs><a class='{'on' if view != 'history' else ''}' href='/owner?{q}'>Needs you ({n})</a>"
            f"<a class='{'on' if view == 'history' else ''}' href='/owner?{q}&amp;view=history'>Earlier</a></nav>")
    if view == "history":
        main_html = (f"<ul class=inbox>{''.join(past(c) for c in done)}</ul>" if done else
                     "<p class=soft>Nothing has come through yet.</p>")
    else:
        main_html = (f"<ul class=inbox>{''.join(note(c) for c in waiting)}</ul>" if waiting else
                     "<div class=thread><div class=bubble>All quiet. Your agent is handling things within your rules, "
                     "and I'll put anything that needs you right here.</div></div>")

    switch = ""
    if agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume my agent", "resume") if agent_paused else ("Pause my agent", "pause")
        switch = (f"<details><summary>Something feels off?</summary><div class=sheet><p class=small>Pause your agent and "
                  f"I'll hold everything it asks for until you turn it back on.</p>"
                  f"<form method=post action='/agent/{path}'>{hidden}<button class='btn ghost'>{verb}</button></form></div></details>")
    rules = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
    state = ("<span class='state paused'>Agent paused</span>" if agent_paused else
             "<span class=state>Agent on, within your rules</span>")
    so_far = f"You've said yes {record.get('approved', 0)} times and no {record.get('blocked', 0)} times so far."
    body = (f"<div class=top><span class=brand>{escape(SETTINGS.policy.business_name)}</span>{state}</div>"
            f"<h1>{escape(headline)}</h1><p class='small soft'>{escape(so_far)}</p>"
            f"{tabs}{main_html}{switch}"
            f"<details><summary>Your rules</summary><div class=sheet><ul class=dots>{rules}</ul></div></details>"
            "<p class=foot-note>This page refreshes every 30 seconds. Tap a note to decide.</p>")
    html = _shell("Valerius", body)
    return html.replace("<meta name=robots content=noindex>",
                        "<meta name=robots content=noindex><meta http-equiv=refresh content=30>"
                        "<meta name=apple-mobile-web-app-capable content=yes>", 1)
