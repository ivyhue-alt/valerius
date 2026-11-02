"""Business hours: is the store open now, and when does it open next.

Holds never expire. Outside hours they wait quietly (or ping anyway, if the owner chose that), the
customer is told when they'll hear back, and at opening the owner gets one summary instead of a flood.
"""

from __future__ import annotations

import datetime as dt

from .config import SETTINGS


def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(SETTINGS.policy.timezone)
    except Exception:  # no time zone data installed: fall back to US Eastern standard time
        return dt.timezone(dt.timedelta(hours=-5))


def local(ts: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(int(ts), _tz())


def is_open(ts: int) -> bool:
    p = SETTINGS.policy
    return p.open_hour <= local(ts).hour < p.close_hour


def next_open(ts: int) -> int:
    """Unix time of the next opening at or after ts."""
    p = SETTINGS.policy
    t = local(ts)
    opening = t.replace(hour=p.open_hour, minute=0, second=0, microsecond=0)
    if t.hour >= p.open_hour:
        opening += dt.timedelta(days=1)
    return int(opening.timestamp())


def when_text(ts: int, now: int) -> str:
    """'9 AM' if it's later today, 'tomorrow at 9 AM' otherwise."""
    t, n = local(ts), local(now)
    hour = f"{t.hour % 12 or 12}{':%02d' % t.minute if t.minute else ''} {'AM' if t.hour < 12 else 'PM'}"
    return hour if t.date() == n.date() else f"tomorrow at {hour}" if (t.date() - n.date()).days == 1 else t.strftime("%A at ") + hour
