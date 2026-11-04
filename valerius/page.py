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
.said{font-size:1.05rem;line-height:1.45;margin:20px 0 0;padding-left:12px;border-left:3px solid var(--line);color:var(--ink)}
.said small{display:block;color:var(--soft);font-size:.82rem;margin-bottom:2px}
.late{font-size:.85rem;color:var(--warn);margin:0 0 10px}
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
.tabs{display:flex;gap:6px;margin:-8px 0 22px}.tabs a{padding:8px 14px;border-radius:999px;color:var(--soft);font-size:.92rem}
.tabs a.on{background:var(--fill);color:var(--ink);font-weight:600}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0 6px}
.stat{background:var(--fill);border-radius:14px;padding:14px}
.stat b{display:block;font-size:1.6rem;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stat span{font-size:.85rem;color:var(--soft)}
.bars{list-style:none;margin:10px 0 0;padding:0}.bars li{margin:0 0 14px}
.bars .top2{display:flex;justify-content:space-between;font-size:.95rem}
.bar{height:8px;border-radius:4px;background:var(--fill);margin:6px 0 4px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent,#111827);border-radius:4px}
.bars q{display:block;font-size:.85rem;color:var(--soft);quotes:"\\201C" "\\201D"}
.receipt{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;overflow-wrap:anywhere;color:var(--soft)}
.foot{margin-top:30px;font-size:.82rem;color:var(--faint)}
.chip{font-size:.8rem;font-weight:600}.r-hold{color:var(--stop)}.r-warn{color:var(--warn)}.r-clear{color:var(--go)}
/* ---- the Valerius look */
:root{--brand:#15172b;--brand-ink:#f5f3ff;--accent:#5b4bdb;--amber:#f5b83d;--amber-bg:#fff6e0;--stop-bg:#fdecea;--go-bg:#e8f5ee;
--bubble:#eef0f6;--card:#fff;--shadow:0 1px 2px rgba(21,23,43,.06),0 8px 24px rgba(21,23,43,.06)}
@media (prefers-color-scheme:dark){:root{--brand:#0f1020;--card:#12151d;--bubble:#1b2030;--amber-bg:#2e2508;--stop-bg:#2c1414;
--go-bg:#0f2a1c;--shadow:none}}
body.v{background:var(--fill)}
body.v main{padding:0 0 120px}
.appbar{background:var(--brand);color:var(--brand-ink);padding:14px 20px 18px;display:flex;justify-content:space-between;align-items:center;
font-size:.85rem}
.appbar .mark{display:flex;align-items:center;gap:9px;font-weight:700;letter-spacing:.01em;font-size:.95rem}
.appbar .mark svg{flex:none}.appbar .when{opacity:.7}
.wrap{padding:0 16px}
.hero{background:var(--card);border-radius:20px;padding:18px 18px 16px;margin:-6px 0 12px;box-shadow:var(--shadow);position:relative}
.state{display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
color:#8a5a00;background:var(--amber-bg);padding:5px 10px;border-radius:999px;margin-bottom:14px}
.state i{width:7px;height:7px;border-radius:50%;background:var(--amber)}
.hero .who{margin-bottom:10px}
.hero .amount{font-size:3.1rem;margin:6px 0 2px}
.flags{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0;padding:0;list-style:none}
.flags li{background:var(--stop-bg);color:var(--stop);font-size:.9rem;font-weight:600;padding:7px 11px;border-radius:10px;
display:flex;gap:6px;align-items:flex-start;line-height:1.3}
.flags li::before{content:"!";flex:none;width:17px;height:17px;border-radius:50%;background:var(--stop);color:#fff;font-size:.72rem;
display:grid;place-items:center;margin-top:1px}
.flags.calm li{background:var(--fill);color:var(--ink)}.flags.calm li::before{background:var(--soft)}
.chat{background:var(--card);border-radius:20px;padding:14px 16px 16px;margin:0 0 12px;box-shadow:var(--shadow)}
.chat small{display:block;color:var(--soft);font-size:.8rem;margin:0 0 8px}
.bubble{background:var(--bubble);border-radius:18px 18px 18px 6px;padding:11px 14px;font-size:1rem;line-height:1.45;
overflow-wrap:anywhere;max-width:92%}
.outcomes{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 12px}
.outcome{border-radius:16px;padding:12px 13px;font-size:.88rem;line-height:1.4;background:var(--card);box-shadow:var(--shadow)}
.outcome b{display:block;font-size:.78rem;letter-spacing:.04em;text-transform:uppercase;margin-bottom:4px}
.outcome.y b{color:var(--go)}.outcome.n b{color:var(--soft)}
.outcome .if{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.pill{background:var(--card);box-shadow:var(--shadow);border-radius:999px;padding:6px 12px;font-size:.85rem;color:var(--soft)}
.pill b{color:var(--stop)}
.panel{background:var(--card);border-radius:20px;padding:2px 16px;box-shadow:var(--shadow);margin:12px 0 0}
.panel details{border-top:0;border-bottom:1px solid var(--line)}.panel details:last-of-type{border-bottom:0}
.dock{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);
padding:12px 16px calc(12px + env(safe-area-inset-bottom));box-shadow:0 -8px 24px rgba(21,23,43,.08)}
.dock .actions{grid-template-columns:1.4fr 1fr;margin:0;max-width:488px;margin:0 auto}
.dock .btn{padding:15px 10px;font-size:1rem}
.dock .yes{background:var(--brand);color:var(--brand-ink)}
@media (prefers-color-scheme:dark){.dock .yes{background:var(--brand-ink);color:var(--brand)}}
.dock .no{color:var(--ink)}
.dock .meta{max-width:488px;margin:8px auto 0}
.dock .barbtn{grid-column:1/-1;background:var(--stop-bg);color:var(--stop);padding:12px 10px;font-size:.95rem}
.outcome.b{margin:0 0 12px}.outcome.b b{color:var(--stop)}
.brow{display:flex;justify-content:space-between;align-items:center;gap:10px}.brow small{display:block;color:var(--soft);font-size:.8rem}
.btn.small{width:auto;padding:8px 14px;font-size:.9rem}
.v .btn.yes{background:var(--brand);color:var(--brand-ink)}.v .btn.stopbtn{background:var(--stop);color:#fff}
.v .panel .actions{margin:12px 0 16px}.v .hero h1{font-size:1.6rem;margin:0 0 8px}
label.check{display:flex;gap:10px;align-items:center;color:var(--ink);font-size:.95rem;margin:16px 0 0;cursor:pointer}
label.check input{width:20px;height:20px;accent-color:var(--brand)}
.v .done-list .name,.v .done-list .right{color:var(--soft);font-weight:500}
.v .foot{text-align:center;padding:0 16px}
.v .late{background:var(--amber-bg);border-radius:14px;padding:10px 12px;color:#8a5a00;margin:0 0 12px}
@media (min-width:720px){body.v main{max-width:560px;margin:0 auto}.appbar{border-radius:0 0 20px 20px}}
@media (min-width:720px){.dock{position:static;background:transparent;border:0;box-shadow:none;max-width:560px;
margin:-100px auto 40px;padding:0 16px}body.v main{padding-bottom:110px}}
@media (min-width:1000px){body.v.wide main{max-width:900px}body.v.wide .stats{grid-template-columns:repeat(4,1fr)}}
/* receipt */
.ticket{background:var(--card);border-radius:20px;box-shadow:var(--shadow);margin:-6px 0 12px;position:relative;overflow:hidden}
.ticket .tp{padding:22px 18px 18px}.ticket .bt{padding:16px 18px 18px;border-top:2px dashed var(--line)}
.ticket::before,.ticket::after{content:"";position:absolute;width:22px;height:22px;border-radius:50%;background:var(--fill);top:var(--cut)}
.ticket::before{left:-11px}.ticket::after{right:-11px}
.seal{display:flex;align-items:center;gap:12px}.seal .n{font-weight:700;font-variant-numeric:tabular-nums}
.chain{display:flex;align-items:center;gap:6px;margin:12px 0 0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;
color:var(--soft)}.chain span{background:var(--fill);border-radius:6px;padding:3px 6px}.chain span.me{background:var(--brand);color:var(--brand-ink)}
.v .done{width:52px;height:52px;margin:0 0 14px}
.v .done.ok{background:var(--go-bg);color:var(--go)}.v .done.bad{background:var(--stop-bg);color:var(--stop)}
/* dashboard */
.v .list{background:var(--card);border-radius:20px;box-shadow:var(--shadow);padding:0 16px;margin:10px 0 0}
.v .list li:last-child a,.v .list li:last-child .row{border-bottom:0}
.v .list li{position:relative}
.v .list li.urgent::before{content:"";position:absolute;left:-16px;top:14px;bottom:14px;width:4px;border-radius:0 4px 4px 0;background:var(--stop)}
.v .tabs{margin:14px 0 6px}.v .tabs a.on{background:var(--card);box-shadow:var(--shadow)}
.v h1.big{font-size:1.7rem;margin:18px 0 4px}
.v .stat{background:var(--card);box-shadow:var(--shadow)}
.v .bars,.v .wrap>.lines{background:var(--card);border-radius:20px;box-shadow:var(--shadow);padding:14px 16px}
.v .section{margin:22px 4px 0}
.v .panel .lines li{border-bottom:1px solid var(--line)}.v .panel .lines li:last-child{border-bottom:0}
"""

LOGO = ("<svg width=22 height=22 viewBox='0 0 24 24' aria-hidden=true><path d='M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5z' "
        "fill='#5b4bdb'/><path d='m8 9 4 7 4-7' fill='none' stroke='#fff' stroke-width='2.2' stroke-linecap='round' "
        "stroke-linejoin='round'/></svg>")


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


def _shell(title: str, body: str, after: str = "", look: str = "") -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<meta name=robots content=noindex><title>{escape(title)}</title>"
            f"<style>{CSS}</style></head><body{' class=' + look if look else ''}><main>{body}</main>{after}</body></html>")


def _bar(left: str, right: str = "") -> str:
    return (f"<div class=appbar><span class=mark>{LOGO}{escape(left)}</span>"
            f"<span class=when>{right}</span></div>")



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
        f"{mins // 60} h ago" if mins < 1440 else ("1 day ago" if mins < 2880 else f"{mins // 1440} days ago")


def _date(ts) -> str:
    import datetime as _dt
    try:
        d = _dt.datetime.fromtimestamp(int(ts), _dt.timezone.utc)
        return f"{d:%b} {d.day}, {d.year}"          # %-d isn't supported on Windows
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


PERSON = ("<svg viewBox='0 0 24 24' width=20 height=20 aria-hidden=true fill='currentColor'>"
          "<circle cx=12 cy=8 r=4 /><path d='M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7z'/></svg>")


def _initial(case: dict) -> str:
    n = (case.get("customer_name") or "").strip()
    return escape(n[:1].upper()) if n else PERSON


def _name(case: dict) -> str:
    """Never 'A customer' on a list: the name, else the order number, else the last digits of their number."""
    if case.get("customer_name"):
        return case["customer_name"]
    order = (case.get("order") or {}).get("order_id")
    if order:
        return f"Order {order}"
    cid = str(case.get("customer_id") or "")
    return f"Customer ending {cid[-4:]}" if len(cid) >= 4 else "Customer"


def _amount_label(case: dict) -> str:
    amt, act = case.get("amount_usd"), case.get("requested_action", "")
    if amt is None:
        return ""
    word = {"refund": "refund", "reship": "replacement", "cancel": "order"}.get(act, "")
    return f"${float(amt):,.0f}" + (f" {word}" if word else "")


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
        who = escape(voice.who(case))
        flags = "".join(f"<li>{escape(r[:1].upper() + r[1:])}</li>" for r in reasons) or \
            "<li>Your rules say you decide this one</li>"
        head = ("<section class=hero>"
                + ("<span class=state><i></i>Needs you</span>" if held else "")
                + f"<div class=who><div class=av>{_initial(case)}</div><div><div class=name>{who}</div>"
                + (f"<div class=sub>Order {escape(order)}</div>" if order else "") + "</div></div>"
                + (f"<div class=amount>${float(amt):,.0f}</div>" if amt is not None else "")
                + f"<div class=sub>{escape(_what(case))}</div>"
                + f"<ul class=flags aria-label='Why it waited for you'>{flags}</ul></section>")
        said = case.get("text", "").strip()
        if said:
            short = said if len(said) <= 240 else said[:237].rsplit(" ", 1)[0] + "..."
            head += (f"<section class=chat><small>In their words, to your agent</small>"
                     f"<div class=bubble>{_highlight(short, quotes)}</div></section>")
        if claims:
            head += f"<div class=pills><span class=pill><b>{_ordinal(len(claims) + 1)} claim</b> in two years</span></div>"
        if held:
            yes_text, no_text = voice.if_yes(case, fee), voice.if_no(case)
            head += ("<div class=outcomes>"
                     f"<div class='outcome y'><b>If you say yes</b>{escape(yes_text[:1].upper() + yes_text[1:])}</div>"
                     f"<div class='outcome n'><b>If you say no</b>{escape(no_text[:1].upper() + no_text[1:])}</div></div>")
            from .act import can_bar
            if can_bar(case):
                bar_text = voice.if_bar(case)
                head += (f"<div class='outcome b'><b>If you block {escape(voice.who(case))}</b>"
                         f"{escape(bar_text[:1].upper() + bar_text[1:])}</div>")
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
            from .act import can_bar
            buttons = (f"<button class='btn yes' name=decision value=approve>{escape(yes)}</button>"
                       f"<button class='btn no' name=decision value=block>{escape(no)}</button>")
            if can_bar(case):
                buttons += f"<button class='btn barbtn' name=decision value=bar>{escape(voice.bar_button(case))}</button>"
        else:  # the safe choice comes first for families
            buttons = (f"<button class='btn primary-stop' name=decision value=block>{escape(no)}</button>"
                       f"<button class='btn no quiet' name=decision value=approve>{escape(yes)}</button>")
        actions = (f"<form id=decide-form method=post action='/case/{escape(str(case.get('id', '')))}/decide'>{hidden}"
                   f"<div class=actions>{buttons}</div></form>"
                   f"<p class=meta>This link works once, for {escape(expires)} more.</p>")

    # ---- everything else, folded
    from .act import can_bar
    folds = []
    if held and business:
        name = escape(voice.who(case))
        folds.append(
            f"<details><summary>Edit what {name} will get</summary><div class=inner>"
            f"<label for=ny>If you say yes</label><textarea id=ny name=note_yes rows=5 maxlength=1200 form=decide-form>"
            f"{escape(voice.customer_note(dict(case, status='approved')))}</textarea>"
            f"<label for=nn>If you say no</label><textarea id=nn name=note_no rows=5 maxlength=1200 form=decide-form>"
            f"{escape(voice.customer_note(dict(case, status='blocked')))}</textarea>"
            + (f"<p class=note>If you block them, they get: &ldquo;{escape(voice.barred_note(case))}&rdquo;</p>"
               if can_bar(case) else "")
            + "</div></details>")
    detail = []
    if case.get("text", "").strip() and (not business or len(case.get("text", "").strip()) > 240):
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
    late = ""
    if case.get("paused_agent"):
        late += "<p class='note flag'>Your agent is paused, so everything waits for you.</p>"
    if business and case.get("after_hours"):
        from . import hours
        t = hours.local(case.get("created_at", now))
        at = f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"
        late += (f"<p class=late>Came in at {at}, while you were closed. {escape(voice.who(case))} was told "
                 "you'd look at it when you open.</p>")

    if business:
        dock = f"<div class=dock>{actions}</div>" if actions else ""
        body = (_bar(SETTINGS.policy.business_name, escape(_ago(case.get('created_at'), now)))
                + f"<div class=wrap>{late}{head}<div class=panel>{''.join(folds)}</div></div>"
                "<p class=foot>Valerius checks. You decide.</p>")
        return _shell("Valerius", body, after=dock, look="v")
    body = (f"<div class=top><b>Valerius</b><span>{escape(_ago(case.get('created_at'), now))}</span></div>"
            f"{late}{head}{actions}<div style='margin-top:26px'>{''.join(folds)}</div>"
            "<p class=foot>Valerius checks. You decide.</p>")
    return _shell("Valerius", body)


SHOP_CSS = """<style>
body.shop{background:#faf7f2}.shop main{padding:0 0 40px}
.shop .storebar{background:#fff;border-bottom:1px solid #eee5d8;padding:14px 18px;display:flex;align-items:center;gap:12px}
.shop .storebar .logo{width:38px;height:38px;border-radius:12px;background:#7a4b2a;color:#fff;display:grid;place-items:center;font-weight:700}
.shop .storebar b{display:block}.shop .storebar span{font-size:.82rem;color:#8a7b6b}
.shop .wrap{padding:16px}
.shop .card{background:#fff;border-radius:20px;padding:18px;box-shadow:0 1px 2px rgba(60,40,20,.06),0 8px 24px rgba(60,40,20,.06);margin:0 0 12px}
.shop h1{font-size:1.5rem;margin:0 0 4px}.shop .lead{color:#8a7b6b;margin:0 0 6px}
.shop label{color:#5c4f43}.shop input[type=text],.shop textarea,.shop input[type=password]{background:#faf7f2;border-color:#eee5d8}
.shop .row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.shop .send{background:#7a4b2a;color:#fff;margin-top:18px}
.shop .thread{display:flex;flex-direction:column;gap:10px}
.shop .me,.shop .them{max-width:86%;padding:11px 14px;border-radius:18px;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere}
.shop .me{align-self:flex-end;background:#7a4b2a;color:#fff;border-bottom-right-radius:6px}
.shop .them{align-self:flex-start;background:#fff;box-shadow:0 1px 2px rgba(60,40,20,.08);border-bottom-left-radius:6px}
.shop .them small{display:block;color:#8a7b6b;font-size:.78rem;margin-bottom:3px}
.shop .wait{display:flex;align-items:center;gap:8px;color:#8a7b6b;font-size:.9rem;margin:6px 4px 0}
.shop .wait i{width:8px;height:8px;border-radius:50%;background:#e0a84a;animation:p 1.4s infinite}
@keyframes p{50%{opacity:.25}}
.shop .stamp{display:inline-block;font-weight:700;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase;padding:5px 10px;
border-radius:999px;margin:0 0 10px}.shop .stamp.ok{background:#e8f5ee;color:#16794a}.shop .stamp.no{background:#f4efe8;color:#5c4f43}
.shop .powered{text-align:center;color:#b3a594;font-size:.78rem;margin-top:22px}
@media (prefers-color-scheme:dark){body.shop{background:#15120f}.shop .storebar,.shop .card,.shop .them{background:#1f1a16;border-color:#2e2620}
.shop input[type=text],.shop textarea,.shop input[type=password]{background:#15120f;border-color:#2e2620}}
</style>"""


def _storebar() -> str:
    name = SETTINGS.policy.business_name
    return (f"<div class=storebar><div class=logo>{escape(name[:1])}</div><div><b>{escape(name)}</b>"
            "<span>Help with an order</span></div></div>")


def shop_form(error: str = "") -> str:
    """The store's help page a customer opens on their phone."""
    err = f"<p class='note flag'>{escape(error)}</p>" if error else ""
    body = (_storebar() + "<div class=wrap><div class=card><h1>What can we help with?</h1>"
            "<p class=lead>Tell us what happened and we'll sort it out.</p>" + err
            + "<form method=post action='/help' enctype='multipart/form-data'>"
            "<div class=row2><div><label for=n>First name</label><input id=n name=name type=text maxlength=40 required "
            "autocomplete=given-name></div><div><label for=o>Order number</label><input id=o name=order type=text "
            "maxlength=24 placeholder='ORD-4502'></div></div>"
            "<label for=t>What happened?</label><textarea id=t name=text rows=4 maxlength=4000 required></textarea>"
            "<label for=a>Refund you're asking for (optional)</label><input id=a name=amount type=text inputmode=decimal "
            "maxlength=12 placeholder='$24'>"
            "<label for=f>Photo (optional)</label><input id=f type=file name=file accept='image/jpeg,image/png,image/webp'>"
            "<label for=c>Demo access code</label><input id=c name=code type=password autocomplete=off required>"
            "<button class='btn send'>Send</button></form></div>"
            "<p class=powered>Replies come from the store. Checked by Valerius.</p></div>")
    return _shell(SETTINGS.policy.business_name, body).replace("</style>", "</style>" + SHOP_CSS, 1) \
        .replace("<body>", "<body class=shop>", 1)


def shop_status(case: dict, token: dict[str, str], holding: str) -> str:
    """What the customer sees after sending: their message, the store's reply, and the result when it comes."""
    from urllib.parse import urlencode
    from . import voice
    status = case.get("status")
    final = status in ("approved", "blocked", "refused", "allowed")
    if status == "allowed":
        reply = (voice.customer_note(dict(case, status="approved")) if case.get("requested_action")
                 else "Thanks, the team has your message and will reply here soon.")
    elif final:
        reply = case.get("customer_note") or holding
    else:
        reply = holding
    stamp = ""
    if final and case.get("requested_action"):
        ok = status in ("approved", "allowed")
        stamp = f"<span class='stamp {'ok' if ok else 'no'}'>{'Approved' if ok else 'Update'}</span>"
    said = (case.get("text") or "").strip()
    refresh = "" if final else (f"<meta http-equiv=refresh content='6;url=/status/{escape(str(case.get('id', '')))}?"
                                f"{escape(urlencode({k: token.get(k, '') for k in TOKEN_KEYS}))}'>")
    body = (_storebar() + "<div class=wrap>" + stamp + "<div class=thread>"
            f"<div class=me>{escape(said[:600])}</div>"
            f"<div class=them><small>{escape(SETTINGS.policy.business_name)}</small>{escape(reply)}</div></div>"
            + ("" if final else "<p class=wait><i></i>This page updates on its own.</p>")
            + "<p class=powered>Replies come from the store. Checked by Valerius.</p></div>")
    html = _shell(SETTINGS.policy.business_name, body).replace("</style>", "</style>" + SHOP_CSS, 1)
    return html.replace("<body>", "<body class=shop>", 1).replace("<head>", "<head>" + refresh, 1)


def confirm_page(case: dict, form: dict[str, str], choice: str) -> str:
    """One more look before money moves, so a mistaken tap on a phone can be taken back."""
    from urllib.parse import urlencode
    from . import voice
    who = voice.who(case)
    who = "this customer" if who == "A customer" else who
    amt = case.get("amount_usd")
    money = f"${float(amt):,.0f}" if amt is not None else ""
    yes, no = voice.buttons(case)
    fee = _fee(amt) if amt is not None and case.get("requested_action") in ("refund", "cancel") else None
    if choice == "approve":
        title = {"refund": f"Send {money} back to {who}?", "reship": f"Send {who} a replacement?",
                 "cancel": f"Cancel {who}'s order?"}.get(case.get("requested_action", ""), f"{yes} for {who}?")
        result, label, cls = voice.if_yes(case, fee), yes, "yes"
        draft = voice.customer_note(dict(case, status="approved"))
        note = form.get("note_yes") or draft
    elif choice == "bar":
        title, result, label, cls = f"Deny and block {who}?", voice.if_bar(case), voice.bar_button(case), "stopbtn"
        note = draft = voice.barred_note(case)
    else:
        title = {"refund": f"Deny {who}'s refund?"}.get(case.get("requested_action", ""), f"{no}?")
        result, label, cls = voice.if_no(case), no, "stopbtn"
        draft = voice.customer_note(dict(case, status="blocked"))
        note = form.get("note_no") or draft
    keep = {k: form.get(k, "") for k in TOKEN_KEYS}
    hidden = "".join(f"<input type=hidden name='{k}' value='{escape(v)}'>" for k, v in keep.items())
    hidden += (f"<input type=hidden name=decision value='{escape(choice)}'><input type=hidden name=confirmed value=1>"
               f"<input type=hidden name=note_yes value='{escape(form.get('note_yes', ''))}'>"
               f"<input type=hidden name=note_no value='{escape(form.get('note_no', ''))}'>")
    back = f"/case/{escape(str(case.get('id', '')))}?{escape(urlencode(keep))}"
    body = (_bar(SETTINGS.policy.business_name, "Check before it goes")
            + "<div class=wrap><section class=hero><span class=state><i></i>Are you sure?</span>"
            f"<h1>{escape(title)}</h1><p class=note>{escape(result[:1].upper() + result[1:])}</p></section>"
            f"<section class=chat><small>What {escape(who)} will get{' (you edited this)' if note.strip() != draft.strip() else ''}</small><div class=bubble>{escape(note)}</div></section>"
            f"<form method=post action='/case/{escape(str(case.get('id', '')))}/decide' class=panel>{hidden}"
            "<label class=check><input type=checkbox name=no_confirm value=1> Don't ask me again on this phone</label>"
            f"<div class=actions><button class='btn {cls}'>Yes, {escape(label[:1].lower() + label[1:])}</button>"
            f"<a class='btn no' href='{back}'>Go back</a></div></form>"
            "<p class=foot>Nothing has happened yet. Going back keeps everything as it is.</p></div>")
    return _shell("Are you sure?", body, look="v")


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
    result = (voice.if_yes(case, fee) if status == "approved" else
              voice.if_bar(case) if case.get("barred_person") else voice.if_no(case))
    result = result[:1].upper() + result[1:]
    got = (f"<div class=label>What {escape(voice.who(case))} got</div><div class=msg>{escape(case['customer_note'])}</div>"
           if business and case.get("customer_note") else "")
    seq = receipt.get("seq") if receipt else None
    h = str(receipt.get("hash", "")) if receipt else ""
    proof = ""
    if receipt:
        proof = (f"<details><summary>Proof</summary><div class=inner><p class=note>This is receipt {escape(str(seq))}. "
                 "Each receipt locks in the one before it, so nobody can quietly change the history.</p>"
                 f"<p class=receipt>{escape(h)}</p></div></details>")
    ok = status == "approved"
    mark = f"<div class='done {'ok' if ok else 'bad'}'>{'&#10003;' if ok else '&#10005;'}</div>"
    if not business:
        body = (f"<div class=top><b>Valerius</b><span>{escape(_date(_time.time()))}</span></div>"
                f"{mark}<h1>Done. You chose: {escape(title)}.</h1><p class=note>{escape(result)}</p>{got}"
                f"<div style='margin-top:26px'>{proof}</div><p class=foot>Saved with a receipt. You can close this page.</p>")
        return _shell("Valerius receipt", body)
    chain = ""
    if receipt and isinstance(seq, int) and seq > 1:
        chain = (f"<div class=chain aria-label='Receipt chain'><span>#{seq - 1}</span>&rarr;"
                 f"<span class=me>#{seq} &middot; {escape(h[:8])}</span></div>")
    body = (_bar(SETTINGS.policy.business_name, escape(_date(_time.time())))
            + "<div class=wrap><section class=ticket style='--cut:calc(100% - 118px)'><div class=tp>"
            f"{mark}<h1>Done. You chose: {escape(title)}.</h1><p class=note>{escape(result)}</p>{got}</div>"
            "<div class=bt><div class=seal><b class=n>Receipt"
            + (f" #{escape(str(seq))}" if receipt else "") + "</b><span class=sub>Locked into your history</span></div>"
            + f"{chain}</div></section><div class=panel>{proof}</div></div>"
            "<p class=foot>Saved with a receipt. You can close this page.</p>")
    return _shell("Valerius receipt", body, look="v")


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
                    tab_query: str = "", claim_counts: dict[str, int] | None = None,
                    barred: dict | None = None, unbar_token: dict[str, str] | None = None,
                    confirm_on: bool = True) -> str:
    """The owner's phone: a short list of people waiting on a decision, then what already happened."""
    from . import voice

    def row(c: dict) -> str:
        link = review_links.get(c.get("id", ""))
        amt = c.get("amount_usd")
        r = voice.reasons(c, limit=1)
        line = (r[0][:1].upper() + r[0][1:]) if r else "Your rules say you decide this one"
        inner = (f"<div class=av>{_initial(c)}</div><div class=main><div class=name>{escape(_name(c))}</div>"
                 f"<div class=line>{escape(line)}.</div></div>"
                 f"<div class=right>{escape(_amount_label(c))}"
                 f"<small>{'overnight' if c.get('after_hours') else escape(_ago(c.get('created_at')))}</small></div>")
        cls = " class=urgent" if c.get("risk") == "CRITICAL" else ""
        return f"<li{cls}><a href='{escape(link)}' aria-label='Review and decide'>{inner}</a></li>" if link else f"<li{cls}><div class=row>{inner}</div></li>"

    def past(c: dict) -> str:
        status = str(c.get("status"))
        outcome = {"approved": ("ok", "You said yes"),
                   "blocked": ("bad", "You blocked them" if c.get("barred_person") else "You said no"),
                   "refused": ("bad", "Refused (blocked)"),
                   "allowed": ("ok", "Handled by your agent")}.get(status, ("", status))
        amt = c.get("amount_usd")
        return (f"<li><div class=row><div class=av>{_initial(c)}</div><div class=main><div class=name>{escape(_name(c))}</div>"
                f"<div class='line {outcome[0]}'>{escape(outcome[1])}</div></div>"
                f"<div class=right>{escape(_amount_label(c))}<small>{escape(_ago(c.get('created_at')))}</small></div></div></li>")

    all_cases = cases
    cases = [c for c in cases if c.get("channel") == "business"]  # family scam alerts go to the family contact, not the store
    waiting = sorted([c for c in cases if c.get("status") == "held"],
                     key=lambda c: (c.get("risk") != "CRITICAL", -int(c.get("created_at", 0))))
    done = [c for c in cases if c.get("status") != "held"][:12]
    n = len(waiting)
    words = ["", "One thing", "Two things", "Three things", "Four things", "Five things"]
    headline = "You're all caught up." if n == 0 else f"{words[n] if n < 6 else str(n) + ' things'} need{'s' if n == 1 else ''} you."
    waiting_html = (f"<div class=section>Waiting for you: tap one to decide</div><ul class=list>"
                    f"{''.join(row(c) for c in waiting)}</ul>" if waiting else
                    "<p class=note>Your agent is handling everything within your rules. Anything that needs you shows up here.</p>")
    done_html = (f"<div class=section>Already decided, nothing to do</div><ul class='list done-list'>"
                 f"{''.join(past(c) for c in done)}</ul>" if done else "")
    rules = "".join(f"<li>{escape(x)}</li>" for x in SETTINGS.policy.lines())
    folds = f"<details><summary>Your rules</summary><div class=inner><ul class=lines>{rules}</ul></div></details>"
    if agent_token:
        hidden = "".join(f"<input type=hidden name='{k}' value='{escape(str(agent_token.get(k, '')))}'>" for k in TOKEN_KEYS)
        verb, path = ("Resume my agent", "resume") if agent_paused else ("Pause my agent", "pause")
        folds += (f"<details><summary>Something feels off?</summary><div class=inner><p class=note>Pause your agent and "
                  f"everything it asks for waits for you.</p><form method=post action='/agent/{path}'>{hidden}"
                  f"<button class='btn no'>{verb}</button></form></div></details>")
    if not confirm_on:
        folds += ("<details><summary>Ask me before each decision: off</summary><div class=inner><p class=note>On this "
                  "phone, your taps go through without the \"Are you sure?\" step.</p>"
                  "<a class='btn no small' href='/prefs/confirm'>Turn it back on</a></div></details>")
    if barred:
        rows = []
        for cid, b in barred.items():
            hid = "".join(f"<input type=hidden name='{k}' value='{escape(str((unbar_token or {}).get(k, '')))}'>"
                          for k in TOKEN_KEYS)
            who = escape(b.get("name") or (f"Customer ending {cid[-4:]}" if len(cid) >= 4 else "Customer"))
            rows.append(f"<li class=brow><span>{who}<small>since {escape(_date(b.get('at')))}</small></span>"
                        + (f"<form method=post action='/barred/unblock'>{hid}<input type=hidden name=who value='{escape(cid)}'>"
                           "<button class='btn no small'>Unblock</button></form>" if unbar_token else "") + "</li>")
        folds += (f"<details><summary>People you blocked ({len(barred)})</summary><div class=inner><p class=note>They "
                  "pretended to be you or your staff. Their refunds, replacements and account changes are refused, "
                  f"and they aren't told why.</p><ul class=lines>{''.join(rows)}</ul></div></details>")
    state = ("<span><span class='dot off'></span>Agent paused</span>" if agent_paused else
             "<span><span class=dot></span>Agent on</span>")
    q = escape(tab_query)
    tabs = (f"<nav class=tabs><a class='{'on' if view != 'insights' else ''}' href='/owner?{q}'>Needs you"
            f"{f' ({n})' if n else ''}</a><a class='{'on' if view == 'insights' else ''}' href='/owner?{q}&amp;view=insights'>"
            "Insights</a></nav>")
    if view == "insights":
        main = insights_view(all_cases)
    else:
        main = (f"<h1 class=big>{escape(headline)}</h1>{waiting_html}{done_html}")
    body = (_bar(SETTINGS.policy.business_name, state)
            + f"<div class=wrap>{tabs}{main}<div class=panel>{folds}</div></div>"
            "<p class=foot>Updates every 30 seconds.</p>")
    html = _shell("Valerius", body, look="'v wide'")
    return html.replace("<meta name=robots content=noindex>",
                        "<meta name=robots content=noindex><meta http-equiv=refresh content=30>"
                        "<meta name=apple-mobile-web-app-capable content=yes>", 1)


def insights_view(cases: list[dict]) -> str:
    """What the owner learns from the last 30 days, in plain numbers."""
    from . import insights
    d = insights.build(cases)
    money = lambda x: f"${x:,.0f}"  # noqa: E731
    if not d["requests"]:
        return ("<h1>Insights</h1><p class=note>Nothing in the last 30 days yet. As your agent handles requests, "
                "you'll see what comes back, why, and what it costs you.</p>")
    handled = round(100 * d["handled_alone"] / d["requests"]) if d["requests"] else 0
    html = (f"<h1>Your last {d['days']} days</h1>"
            f"<p class=note>Your agent handled {d['handled_alone']} of {d['requests']} requests on its own ({handled}%). "
            f"{d['waited_for_you']} waited for you.</p>"
            "<div class=stats>"
            f"<div class=stat><b>{money(d['refunded_usd'])}</b><span>refunded</span></div>"
            f"<div class=stat><b>{money(d['kept_usd'])}</b><span>kept (refunds you said no to)</span></div>"
            f"<div class=stat><b>{money(d['fees_usd'])}</b><span>card fees on refunds (estimate)</span></div>"
            f"<div class=stat><b>{d['returns']}</b><span>returns and replacements asked for</span></div></div>"
            + (f"<p class=note><span class=flag>{d['fraud']} looked like fraud</span> (someone posing as staff, or trying "
               "to trick your agent). They're left out of the return reasons below.</p>" if d["fraud"] else ""))
    if d["reasons"]:
        html += "<div class=section>Why things come back</div><ul class=bars>" + "".join(
            f"<li><div class=top2><span>{escape(r['reason'])}</span><span>{r['count']}</span></div>"
            f"<div class=bar><i style='width:{r['share']}%'></i></div>"
            + (f"<q>{escape(r['quote'])}</q>" if r["quote"] else "") + "</li>" for r in d["reasons"]) + "</ul>"
    if d["products"]:
        html += "<div class=section>Products that come back most</div><ul class=lines>" + "".join(
            f"<li>{escape(p['name'])}: {p['count']}</li>" for p in d["products"]) + "</ul>"
    if d["repeat"]:
        html += "<div class=section>Customers who claim most often</div><ul class=lines>" + "".join(
            f"<li>{escape(r['who'])}: {r['count']} claims, {money(r['usd'])} asked for</li>" for r in d["repeat"]) + "</ul>"
    html += ("<p class=foot>Sales made through your agent will show here once Valerius is connected to your store's orders.</p>")
    return html
