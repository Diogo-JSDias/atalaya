"""LASIGE positions page.

LASIGE keeps an archive of past calls under a heading that still says "open
call". Each entry is therefore checked against its own application period.
The page currently contains several 2026 entries, but the latest application
window ends on 16 November 2026; those records are excluded on 27 November.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://lasige.pt/positions/"
ALLOWED_NOTICE_HOSTS = {"lasige.pt", "www.lasige.pt", "ciencias.ulisboa.pt", "euraxess.pt", "www.euraxess.pt"}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
PERIOD_RE = re.compile(
    rf"Application\s+period\s*:\s*({MONTH_PATTERN})\s+(\d{{1,2}})"
    rf"\s*(?:to|[-–])\s*(?:({MONTH_PATTERN})\s+)?(\d{{1,2}})"
    rf"\s*,?\s*(20\d{{2}})",
    re.I,
)
OFFER_HINT = re.compile(
    r"has\s+an\s+open\s+call|open\s+call\s+for|recruitment\s+of\s+\d+|"
    r"fellowship|researcher|project",
    re.I,
)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_notice(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and host in ALLOWED_NOTICE_HOSTS
    )


def parse_application_period(value: str) -> tuple[str | None, str | None]:
    """Return start/end ISO dates for the English application-period syntax."""
    match = PERIOD_RE.search(_clean(value))
    if not match:
        return None, None
    start_month = MONTHS[match.group(1).lower()]
    start_day = int(match.group(2))
    end_month = MONTHS[(match.group(3) or match.group(1)).lower()]
    end_day = int(match.group(4))
    year = int(match.group(5))
    start_year = year - 1 if start_month > end_month else year
    try:
        start = dt.date(start_year, start_month, start_day)
        end = dt.date(year, end_month, end_day)
    except ValueError:
        return None, None
    if end < start:
        return None, None
    return start.isoformat(), end.isoformat()


def _card_for_period(node):
    """Find a bounded entry container holding one application-period marker."""
    best = None
    for parent in node.parents:
        if parent.name in {"body", "html", "[document]", "main", "article"}:
            break
        text = _clean(parent.get_text(" ", strip=True))
        if text.count("Application period") > 1:
            break
        if len(text) > 2500:
            break
        if len(text) >= 80 and (
            "Admission Requirements" in text or "Type:" in text or OFFER_HINT.search(text)
        ):
            best = parent
    return best


def _fallback_chunks(soup):
    """Fallback for flat WordPress content where entries are sibling paragraphs."""
    strings = list(soup.find_all(string=True))
    periods = [
        (index, _clean(str(node)), node)
        for index, node in enumerate(strings)
        if "Application period" in str(node)
    ]
    chunks = []
    previous_end = -1
    for period_index, period_text, period_node in periods:
        start = previous_end + 1
        for index in range(period_index - 1, previous_end, -1):
            value = _clean(str(strings[index]))
            if OFFER_HINT.search(value) and len(value) > 25:
                start = index
                break
        text = _clean(" ".join(_clean(str(x)) for x in strings[start:period_index + 1]))
        chunks.append((text, period_node))
        previous_end = period_index
    return chunks


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse LASIGE announcements and keep only future closing dates."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("main") or soup.find("article") or soup
    period_nodes = [
        node for node in content.find_all(string=re.compile(r"Application\s+period\s*:", re.I))
    ]
    offers: list[Offer] = []
    seen: set[tuple[str, str]] = set()

    for node in period_nodes:
        period_text = _clean(str(node))
        start_date, deadline = parse_application_period(period_text)
        if not deadline:
            raise RuntimeError(
                f"LASIGE application period is not parseable: {period_text[:120]}"
            )
        card = _card_for_period(node)
        card_text = _clean(card.get_text(" ", strip=True)) if card else ""
        if not card_text:
            # Fallback to the nearest bounded paragraph/list item.
            parent = node.find_parent(["p", "li", "div"])
            card_text = _clean(parent.get_text(" ", strip=True)) if parent else period_text
        if deadline < today.isoformat():
            continue

        before_period = card_text.split("Application period", 1)[0].strip(" :-")
        if not before_period or not OFFER_HINT.search(before_period):
            # In flat layouts, use the previous text node with a call descriptor.
            prior = node.find_all_previous(string=True, limit=30)
            candidates = [
                _clean(str(value)) for value in prior
                if OFFER_HINT.search(_clean(str(value))) and len(_clean(str(value))) > 25
            ]
            if not candidates:
                raise RuntimeError("LASIGE open-position title not found")
            title = candidates[0]
        else:
            title = before_period
        title = re.sub(r"\s+(?:Type:|Admission Requirements:).*$", "", title, flags=re.I)
        title = _clean(title).strip(" .:-")
        if len(title) > 500:
            title = title[:497].rstrip() + "..."

        anchors = card.find_all("a", href=True) if card else []
        notice_url = next(
            (
                urljoin(base_url, anchor["href"])
                for anchor in anchors
                if _official_notice(urljoin(base_url, anchor["href"]))
            ),
            base_url,
        )
        key = (title, deadline)
        if key in seen:
            continue
        seen.add(key)

        kind = "call" if re.search(r"fellowship|bolsa", title, re.I) else "position"
        type_match = re.search(r"Type:\s*([^.]*(?:fellowship|researcher|position)[^.]*)", card_text, re.I)
        position_type = _clean(type_match.group(1)) if type_match else (
            "Bolsa de investigação" if kind == "call" else "Investigação"
        )
        duration_match = re.search(r"Duration:\s*(.*?)(?=Application period|Announcement link|$)", card_text, re.I)
        notes = f"Período de candidatura: {start_date} a {deadline}."
        if duration_match:
            notes += " Duração indicada: " + _clean(duration_match.group(1))[:250]
        offers.append(Offer(
            source="lasige",
            kind=kind,
            title=title,
            url=notice_url,
            institution="LASIGE – Faculdade de Ciências, Universidade de Lisboa",
            region="Lisboa",
            position_type=position_type,
            deadline=deadline,
            notes=notes,
            extra={
                "application_start": start_date,
                "listing_url": base_url,
            },
        ))

    # If the page still contains calls but no recognizable application periods,
    # surface the change rather than silently making the feed look empty.
    page_text = _clean(content.get_text(" ", strip=True))
    if not period_nodes and re.search(r"has an open call|positions", page_text, re.I):
        raise RuntimeError("LASIGE positions page has no recognizable application-period fields")

    log.info("LASIGE: %d current positions", len(offers))
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    return parse_listing(fetch(LIST_URL), today=today)
