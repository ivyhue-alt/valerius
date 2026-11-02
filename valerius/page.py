"""The approval page: what was held, why, and the owner's rules, on one screen.

Everything from the message is escaped. Evidence is highlighted in place.
"""

from __future__ import annotations

from html import escape

from .config import SETTINGS

TOKEN_KEYS = ("c", "p", "e", "n", "s")  # only these fields are ever copied from a link into a form

CSS = """
:root{--bg:#fff;--ink:#111827;--soft:#6b7280;--faint:#9ca3af;--line:#eceef2;--fill:#f4f5f7;--go:#16794a;
--stop:#b42318;--warn:#a15c07;--mark:#fff1a8;--link:#1f4fd1;--on-go:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#0b0d12;--ink:#f3f4f6;--soft:#a3aab8;--faint:#6b7280;--line:#1f2430;
--fill:#151922;--go:#3ccf8e;--stop:#ff7b72;--warn:#f2b45a;--mark:#5a4b0b;--link:#8fb0ff;--on-go:#06210f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
-webkit-text-size-adjust:100%}
main{max-width:520px;margin:0 auto;padding:22px 20px 48px}
a{color:var(--link);text-decoration:none}
:focus-visible{outline:3px solid var(--link);outline-offset:2px;border-radius:6px}
p{margin:0 0 10px}
.top{display:flex;justify-content:space-between;align-items:center;font-size:.85rem;color:var(--soft);margin-bottom:26px}
.top b{color:var(--ink);font-weight:600}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--go);margin-right:6px;vertical-align:1px}
.dot.off{background:var(--stop)}
h1{font-size:1.9rem;line-height:1.15;font-weight:700;letter-spacing:-.02em;margin:0 0 8px}
.who{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.av{flex:none;width:44px;height:44px;border-radius:50%;background:var(--fill);display:grid;place-items:center;
font-weight:700;font-size:1.05rem;color:var(--ink)}
.who .name{font-weight:600}.who .sub,.sub{color:var(--soft);font-size:.95rem}
.amount{font-size:2.9rem;line-height:1;font-weight:700;letter-spacing:-.03em;font-variant-numeric:tabular-nums;margin:4px 0 6px}
.why{font-size:1.15rem;line-height:1.45;margin:22px 0 8px}
.note{font-size:.95rem;color:var(--soft);margin:0 0 4px}
.flag{color:var(--stop);font-weight:600}
.actions{display:grid;gap:10px;margin:28px 0 8px}
.btn{display:block;width:100%;font-family:inherit;font-weight:600;font-size:1.08rem;line-height:1.2;padding:17px;border-radius:14px;border:0;cursor:pointer;
text-align:center}
.yes{background:var(--go);color:var(--on-go)}
.no{background:transparent;color:var(--stop);box-shadow:inset 0 0 0 1.5px var(--line)}
.primary-stop{background:var(--stop);color:#fff}.quiet{color:var(--ink)}
.meta{text-align:center;font-size:.85rem;color:var(--faint);margin:6px 0 0}
details{border-top:1px solid var(--line)}
details:last-of-type{border-bottom:1px solid var(--line)}
summary{list-style:none;cursor:pointer;padding:16px 0;color:var(--link);font-size:1rem;display:flex;justify-content:space-between}
summary::-webkit-details-marker{display:none}
summary::after{content:"\\203A";color:var(--faint);font-size:1.3rem;line-height:1}
details[open] summary::after{transform:rotate(90deg)}
.inner{padding:0 0 18px}
.msg{background:var(--fill);border-radius:14px;padding:12px 14px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.98rem}
mark{background:var(--mark);color:inherit;border-radius:3px;padding:0 2px}
.label{font-size:.85rem;color:var(--soft);margin:14px 0 6px}
.lines{list-style:none;margin:0;padding:0}.lines li{padding:6px 0;font-size:.95rem}
.evidence{position:relative;border-radius:14px;overflow:hidden;background:#000;margin:18px 0 0}
.evidence img,.evidence svg{display:block;width:100%;height:auto}.evidence svg{position:absolute;inset:0}
textarea,input[type=password],input[type=text]{width:100%;font:inherit;font-size:1rem;padding:12px 14px;border-radius:12px;
border:1px solid var(--line);background:var(--fill);color:var(--ink)}
label{display:block;font-size:.9rem;color:var(--soft);margin:16px 0 6px}
.list{list-style:none;margin:8px 0 0;padding:0}
.list a,.list .row{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--line);color:var(--ink)}
.list .main{flex:1;min-width:0}.list .name{font-weight:600}
.list .line{color:var(--soft);font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.list .right{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.list .right small{display:block;font-weight:400;color:var(--faint);font-size:.8rem}
.urgent .av{background:var(--stop);color:#fff}
.section{font-size:.85rem;color:var(--soft);font-weight:600;margin:30px 0 0}
.ok{color:var(--go)}.bad{color:var(--stop)}
.done{width:56px;height:56px;border-radius:50%;background:var(--fill);display:grid;place-items:center;font-size:1.6rem;margin:6px 0 18px}
.receipt{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;overflow-wrap:anywhere;color:var(--soft)}
.foot{margin-top:30px;font-size:.82rem;color:var(--faint)}
.chip{font-size:.8rem;font-weight:600}.r-hold{color:var(--stop)}.r-warn{color:var(--warn)}.r-clear{color:var(--go)}
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
            f"<meta name=robots content=noindex><title>{escape(title)}</title>"
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


def _initial(case: dict) -> str:
    n = (case.get("customer_name") or "").strip()
    return escape(n[:1].upper()) if n else "?"


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _what(case: dict) -> str:
    """The small line under the amount: what they want, in a few words."""
    act = case.get("requested_action", "")
    qty = int((case.get("order") or {}).get("quantity") or 1)
    items = f" for {qty} items" if qty > 1 else ""
    return {"refund": f"refund{items}", "reship": f"replacement{items}", "cancel": "to cancel their order",
            "payment_change": "to change the card on file", "account_change": "to change account details"}.get(act, "a request")


def approval_page(case: dict, token: dict[str, str], record: dict[str, int],
                  agent_token: dict[str, str] | None = None, agent_paused: bool = False,
                  history: list[dict] | None = None, now: int | None = None) -> str:
    """One decision, nothing else on the first screen: who, how much, why, two buttons."""
    import time as _time
    from . import voice
    now = now or int(_time.time())
    quotes: list[str] = []
    for f in case.get("findings", []):
        quotes += [e["quote"] for e in f["evidence"] if e.get("quote")]
    for mr in case.get("model_reasons", {}).values():
        quotes += mr.get("quotes", [])
    held = case.get("status") == "held"
    business = case.get("channel") == "business"
    amt = case.get("amount_usd")
    fee = _fee(amt) if amt is not None and case.get("requested_action") in ("refund", "cancel") else None
    reasons = voice.reasons(case, limit=2)
    why = voice.join(reasons)
    why = (why[:1].upper() + why[1:] + ".") if why else "Your rules say you decide this one."
    claims = [h for h in (history or []) if h.get("is_claim")]

    # ---- first screen
    if business:
        order = (case.get("order") or {}).get("order_id", "")
        head = (f"<div class=who><div class=av>{_initial(case)}</div><div><div class=name>{escape(voice.who(case))}</div>"
                + (f"<div class=sub>Order {escape(order)}</div>" if order else "") + "</div></div>"
                + (f"<div class=amount>${float(amt):,.0f}</div>" if amt is not None else "")
                + f"<div class=sub>{escape(_what(case))}</div>"
                f"<p class=why>{escape(why)}</p>")
        if claims:
            head += f"<p class=note><span class=flag>{_ordinal(len(claims) + 1)} claim</span> in two years.</p>"
        if held:
            head += f"<p class=note>If you say yes, {escape(voice.if_yes(case, fee))}</p>"
            head += f"<p class=note>If you say no, {escape(voice.if_no(case))}</p>"
    else:
        head = (f"<h1>This looks like a scam.</h1>{_evidence_image(case).split('<p class=')[0]}"
                f"<p class=why>{escape(why)}</p>"
                "<p class=note>Don't send money, gift cards or codes. If it says it's family, call them on the number you already have.</p>")

    actions = ""
    if held:
        yes, no = voice.buttons(case)
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(token.get(k, '')))}'>" for k in TOKEN_KEYS)
        try:
            left = max(0, int(token.get("e", 0)) - now) // 60
        except ValueError:
            left = 0
        expires = f"{left // 60} h {left % 60} min" if left >= 60 else f"{left} min"
        if business:
            buttons = (f"<button class='btn yes' name=decision value=approve>{escape(yes)}</button>"
                       f"<button class='btn no' name=decision value=block>{escape(no)}</button>")
        else:  # the safe choice comes first for families
            buttons = (f"<button class='btn primary-stop' name=decision value=block>{escape(no)}</button>"
                       f"<button class='btn no quiet' name=decision value=approve>{escape(yes)}</button>")
        actions = (f"<form id=decide-form method=post action='/case/{escape(str(case.get('id', '')))}/decide'>{hidden}"
                   f"<div class=actions>{buttons}</div></form>"
                   f"<p class=meta>This link works once, for {escape(expires)} more.</p>")

    # ---- everything else, folded
    folds = []
    if held and business:
        name = escape(voice.who(case))
        folds.append(
            f"<details><summary>Edit what {name} will get</summary><div class=inner>"
            f"<label for=ny>If you say yes</label><textarea id=ny name=note_yes rows=5 maxlength=1200 form=decide-form>"
            f"{escape(voice.customer_note(dict(case, status='approved')))}</textarea>"
            f"<label for=nn>If you say no</label><textarea id=nn name=note_no rows=5 maxlength=1200 form=decide-form>"
            f"{escape(voice.customer_note(dict(case, status='blocked')))}</textarea></div></details>")
    detail = []
    if case.get("text", "").strip():
        detail.append(f"<div class=label>{'What they wrote' if business else 'The message'}</div>"
                      f"<div class=msg>{_highlight(case.get('text', ''), quotes)}</div>")
    if business and _evidence_image(case):
        detail.append(_evidence_image(case))
    if business and case.get("customer_id"):
        items = "".join(
            f"<li>{escape(_date(h['at']))}: {escape((h['action'] or 'message').replace('_', ' '))}"
            + (f" {_money(h['amount_usd'])}" if h.get("amount_usd") is not None else "")
            + f", {escape(h['status'])}</li>" for h in (history or [])[-8:])
        detail.append(f"<div class=label>Their history, last two years</div><ul class=lines>{items or '<li>Nothing before this.</li>'}</ul>"
                      f"<p class=note>Your limit is {SETTINGS.policy.max_claims} claims in {SETTINGS.policy.claim_window_days} days.</p>")
    review = _review_line(case)
    if review or case.get("model_reasons"):
        lines = "".join(
            f"<li><b>{'Muse Spark' if src == 'muse-spark' else 'Second check'}</b> "
            f"{_chip(case.get('models', {}).get(src, ''))}: {escape((mr.get('reasons') or [''])[0])}</li>"
            for src, mr in case.get("model_reasons", {}).items())
        detail.append(f"<div class=label>How it was checked</div><p class=note>{escape(review)}</p><ul class=lines>{lines}</ul>")
    if detail:
        folds.append(f"<details><summary>More details</summary><div class=inner>{''.join(detail)}</div></details>")
    if business:
        rules = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
        folds.append(f"<details><summary>Your rules</summary><div class=inner><ul class=lines>{rules}</ul></div></details>")
        if agent_token:
            hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
            verb, path = ("Resume my agent", "resume") if agent_paused else ("Pause my agent", "pause")
            folds.append(f"<details><summary>Something feels off?</summary><div class=inner><p class=note>Pause your agent and "
                         f"everything it asks for waits for you.</p><form method=post action='/agent/{path}'>{hidden}"
                         f"<button class='btn no'>{verb}</button></form></div></details>")
    if case.get("paused_agent"):
        head = "<p class='note flag'>Your agent is paused, so everything waits for you.</p>" + head

    brand = SETTINGS.policy.business_name if business else "Valerius"
    body = (f"<div class=top><b>{escape(brand)}</b><span>{escape(_ago(case.get('created_at'), now))}</span></div>"
            f"{head}{actions}<div style='margin-top:26px'>{''.join(folds)}</div>"
            "<p class=foot>Valerius checks. You decide.</p>")
    return _shell("Valerius", body)


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
    """After a decision: what happened and exactly what the customer got."""
    import time as _time
    from . import voice
    status = str(case.get("status", ""))
    business = case.get("channel") == "business"
    title = voice.done(case).replace("You chose: ", "").rstrip(".")
    fee = _fee(case["amount_usd"]) if case.get("amount_usd") is not None and case.get("requested_action") in ("refund", "cancel") else None
    result = voice.if_yes(case, fee) if status == "approved" else voice.if_no(case)
    result = result[:1].upper() + result[1:]
    got = (f"<div class=label>What {escape(voice.who(case))} got</div><div class=msg>{escape(case['customer_note'])}</div>"
           if business and case.get("customer_note") else "")
    proof = ""
    if receipt:
        proof = (f"<details><summary>Proof</summary><div class=inner><p class=note>This is receipt {escape(str(receipt.get('seq', '')))}. "
                 "Each receipt locks in the one before it, so nobody can quietly change the history.</p>"
                 f"<p class=receipt>{escape(str(receipt.get('hash', '')))}</p></div></details>")
    body = (f"<div class=top><b>Valerius</b><span>{escape(_date(_time.time()))}</span></div>"
            f"<div class=done>{'&#10003;' if status == 'approved' else '&#10005;'}</div>"
            f"<h1>Done. You chose: {escape(title)}.</h1><p class=note>{escape(result)}</p>{got}"
            f"<div style='margin-top:26px'>{proof}</div><p class=foot>Saved with a receipt. You can close this page.</p>")
    return _shell("Valerius receipt", body)


def result_page(title: str, detail: str) -> str:
    return _shell(title, f"<div class=top><b>Valerius</b></div><h1>{escape(title)}</h1><p class=note>{escape(detail)}</p>")


def intake_form(error: str = "") -> str:
    err = f"<p class='note flag'>{escape(error)}</p>" if error else ""
    body = (
        "<div class=top><b>Valerius</b></div>"
        "<h1>Got a message that feels off?</h1>"
        "<p class=note>Paste it here, or add the screenshot or voice note. You'll get a plain answer in about 15 seconds.</p>"
        + err +
        "<form method=post action='/check' enctype='multipart/form-data'>"
        "<label for=t>The message</label><textarea id=t name=text rows=6 maxlength=4000 "
        "placeholder='Paste what they sent you'></textarea>"
        "<label for=f>Screenshot or voice note (optional)</label>"
        "<input id=f type=file name=file accept='image/jpeg,image/png,image/webp,audio/*'>"
        "<label for=c>Access code</label><input id=c name=code type=password autocomplete=off required>"
        "<div class=actions><button class='btn yes'>Check this message</button></div></form>"
        "<p class=foot>Personal details are removed before review. Use made-up or test messages only.</p>")
    return _shell("Valerius check", body)


def intake_result(risk: str, held: bool, reply: str, link: str = "") -> str:
    bad = held or str(risk).upper() != "LOW"
    head = "Don't act on this yet." if bad else "No common scam signs."
    review = (f"<div class=actions><a class='btn yes' href='{escape(link)}'>See the evidence</a></div>"
              "<p class=meta>The link works once and expires in 2 hours.</p>") if held and link else ""
    body = (f"<div class=top><b>Valerius</b></div><h1 class='{'bad' if bad else 'ok'}'>{escape(head)}</h1>"
            f"<p class=why>{escape(reply)}</p>{review}<p class=foot><a href='/check'>Check another message</a></p>")
    return _shell("Valerius check", body)


def owner_dashboard(cases: list[dict], record: dict[str, int], review_links: dict[str, str],
                    agent_token: dict[str, str] | None, agent_paused: bool, view: str = "waiting",
                    tab_query: str = "", claim_counts: dict[str, int] | None = None) -> str:
    """The owner's phone: a short list of people waiting on a decision, then what already happened."""
    from . import voice

    def row(c: dict) -> str:
        link = review_links.get(c.get("id", ""))
        amt = c.get("amount_usd")
        r = voice.reasons(c, limit=1)
        line = (r[0][:1].upper() + r[0][1:]) if r else "Your rules say you decide this one"
        inner = (f"<div class=av>{_initial(c)}</div><div class=main><div class=name>{escape(voice.who(c))}</div>"
                 f"<div class=line>{escape(_what(c).capitalize())}. {escape(line)}.</div></div>"
                 f"<div class=right>{f'${float(amt):,.0f}' if amt is not None else ''}<small>{escape(_ago(c.get('created_at')))}</small></div>")
        cls = " class=urgent" if c.get("risk") == "CRITICAL" else ""
        return f"<li{cls}><a href='{escape(link)}' aria-label='Review and decide'>{inner}</a></li>" if link else f"<li{cls}><div class=row>{inner}</div></li>"

    def past(c: dict) -> str:
        status = str(c.get("status"))
        outcome = {"approved": ("ok", "You said yes"), "blocked": ("bad", "You said no"),
                   "allowed": ("ok", "Handled by your agent")}.get(status, ("", status))
        amt = c.get("amount_usd")
        return (f"<li><div class=row><div class=av>{_initial(c)}</div><div class=main><div class=name>{escape(voice.who(c))}</div>"
                f"<div class='line {outcome[0]}'>{escape(outcome[1])}</div></div>"
                f"<div class=right>{f'${float(amt):,.0f}' if amt is not None else ''}<small>{escape(_ago(c.get('created_at')))}</small></div></div></li>")

    cases = [c for c in cases if c.get("channel") == "business"]  # family scam alerts go to the family contact, not the store
    waiting = sorted([c for c in cases if c.get("status") == "held"],
                     key=lambda c: (c.get("risk") != "CRITICAL", -int(c.get("created_at", 0))))
    done = [c for c in cases if c.get("status") != "held"][:12]
    n = len(waiting)
    words = ["", "One thing", "Two things", "Three things", "Four things", "Five things"]
    headline = "You're all caught up." if n == 0 else f"{words[n] if n < 6 else str(n) + ' things'} need{'s' if n == 1 else ''} you."
    waiting_html = (f"<ul class=list>{''.join(row(c) for c in waiting)}</ul>" if waiting else
                    "<p class=note>Your agent is handling everything within your rules. Anything that needs you shows up here.</p>")
    done_html = (f"<div class=section>Earlier</div><ul class=list>{''.join(past(c) for c in done)}</ul>" if done else "")
    rules = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
    folds = f"<details><summary>Your rules</summary><div class=inner><ul class=lines>{rules}</ul></div></details>"
    if agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume my agent", "resume") if agent_paused else ("Pause my agent", "pause")
        folds += (f"<details><summary>Something feels off?</summary><div class=inner><p class=note>Pause your agent and "
                  f"everything it asks for waits for you.</p><form method=post action='/agent/{path}'>{hidden}"
                  f"<button class='btn no'>{verb}</button></form></div></details>")
    state = ("<span><span class='dot off'></span>Agent paused</span>" if agent_paused else
             "<span><span class=dot></span>Agent on</span>")
    body = (f"<div class=top><b>{escape(SETTINGS.policy.business_name)}</b>{state}</div>"
            f"<h1>{escape(headline)}</h1>"
            f"<p class=note>You've said yes {record.get('approved', 0)} times and no {record.get('blocked', 0)} times.</p>"
            f"{waiting_html}{done_html}<div style='margin-top:30px'>{folds}</div>"
            "<p class=foot>Updates every 30 seconds.</p>")
    html = _shell("Valerius", body)
    return html.replace("<meta name=robots content=noindex>",
                        "<meta name=robots content=noindex><meta http-equiv=refresh content=30>"
                        "<meta name=apple-mobile-web-app-capable content=yes>", 1)
