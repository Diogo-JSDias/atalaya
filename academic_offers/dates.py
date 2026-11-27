"""Find a deadline date in free text: dd/mm/yyyy, '3 de diciembre de 2026', 'December 3rd, 2026', '3rd December 2026'."""
from __future__ import annotations

import datetime as dt
import re

EN = "january february march april may june july august september october november december".split()
ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
PT = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
MONTHS = {m: i for i, m in enumerate(EN, 1)} | {m: i for i, m in enumerate(ES, 1)} | {m: i for i, m in enumerate(PT, 1)} | {"setiembre": 9}
_M = "(" + "|".join(MONTHS) + ")"

PATTERNS = [
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)\b"), lambda m: (m[3], m[2], m[1])),
    (re.compile(r"\b(\d{1,2})\s+de\s+" + _M + r"\s+(?:de\s+)?(20\d\d)", re.I), lambda m: (m[3], m[2], m[1])),
    (re.compile(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s+" + _M + r",?\s+(20\d\d)", re.I), lambda m: (m[3], m[2], m[1])),
    (re.compile(_M + r"\s+(\d{1,2})\s*(?:st|nd|rd|th)?\s*,?\s+(20\d\d)", re.I), lambda m: (m[3], m[1], m[2])),
]


def _to_date(y: str, mo: str, d: str) -> dt.date | None:
    month = int(mo) if mo.isdigit() else MONTHS.get(mo.lower())
    try:
        return dt.date(int(y), month, int(d))
    except (TypeError, ValueError):
        return None


def first_date(text: str) -> str | None:
    """Earliest-positioned date in `text`, as ISO string."""
    best = None
    for pat, order in PATTERNS:
        m = pat.search(text)
        if m and (best is None or m.start() < best[0]):
            d = _to_date(*order(m))
            if d:
                best = (m.start(), d)
    return best[1].isoformat() if best else None


def date_after(text: str, keywords: str, window: int = 160) -> str | None:
    """The first date that follows any of the `keywords` (a regex), e.g. 'deadline|fin de la oferta'."""
    for m in re.finditer(keywords, text, re.I):
        d = first_date(text[m.end():m.end() + window])
        if d:
            return d
    return None

def _easter_sunday(year: int) -> dt.date:
    """Gregorian Easter date (Meeus/Jones/Butcher algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def lisbon_working_day_deadline(first_day: dt.date, days: int) -> dt.date:
    """Count Portuguese working days in Lisbon, including national and municipal holidays.

    first_day is the first day counted by the legal notice. The function
    counts that date when it is a weekday and not a public holiday.
    """
    if days < 1:
        raise ValueError("days must be at least one")

    current = first_day
    added = 0
    holiday_cache: dict[int, set[dt.date]] = {}

    while added < days:
        if current.year not in holiday_cache:
            easter = _easter_sunday(current.year)
            holiday_cache[current.year] = {
                dt.date(current.year, 1, 1),
                easter - dt.timedelta(days=2),   # Good Friday
                easter + dt.timedelta(days=60),  # Corpus Christi
                dt.date(current.year, 4, 25),
                dt.date(current.year, 5, 1),
                dt.date(current.year, 6, 10),
                dt.date(current.year, 6, 13),     # Lisbon municipal holiday
                dt.date(current.year, 8, 15),
                dt.date(current.year, 10, 5),
                dt.date(current.year, 11, 1),
                dt.date(current.year, 12, 1),
                dt.date(current.year, 12, 8),
                dt.date(current.year, 12, 25),
            }

        if current.weekday() < 5 and current not in holiday_cache[current.year]:
            added += 1
        if added < days:
            current += dt.timedelta(days=1)

    return current

