"""INESC-ID open positions scraper."""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.inesc-id.pt/team/positions/"
PREFERRED_HOSTS = (
    "inesc-id.pt",
    "euraxess.ec.europa.eu",
    "diariodarepublica.pt",
    "dre.pt",
)

_REF_RE = re.compile(
    r"(?:ref(?:erence|er[eê]ncia)?\.?\s*[:#-]?\s*)([A-Za-z0-9][A-Za-z0-9_./-]*)",
    re.IGNORECASE,
)


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _is_preferred_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower().split(":")[0]
    return any(host == domain or host.endswith("." + domain) for domain in PREFERRED_HOSTS)


def _extract_reference(panel) -> str:
    for attr in ("data-ref", "data-reference", "id"):
        val = _clean(panel.get(attr))
        if val and not val.startswith("position-panel"):
            return val
    text = _clean(panel.get_text(" ", strip=True))
    match = _REF_RE.search(text)
    if match:
        return match.group(1).rstrip(".,;:")
    return ""


def _extract_title_and_type(panel) -> tuple[str, str]:
    title = ""
    for selector in ("h2", "h3", "h4", ".position-title", ".title"):
        el = panel.select_one(selector)
        if el:
            title = _clean(el.get_text(" ", strip=True))
            if title:
                break

    position_type = ""
    for selector in (".position-type", ".type", ".badge", ".category"):
        el = panel.select_one(selector)
        if el:
            position_type = _clean(el.get_text(" ", strip=True))
            if position_type:
                break

    return title, position_type


def _extract_url(panel, reference: str) -> str:
    for link in panel.select("a[href]"):
        href = _clean(link.get("href"))
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        candidate = urljoin(LIST_URL, href)
        if _is_preferred_url(candidate):
            return candidate
    if reference:
        return f"{LIST_URL}#{reference}"
    return LIST_URL


def _extract_deadline(panel) -> str | None:
    for selector in (".deadline", ".position-deadline", ".date", ".closing-date"):
        el = panel.select_one(selector)
        if el:
            found = first_date(el.get_text(" ", strip=True))
            if found:
                return found
    return first_date(panel.get_text(" ", strip=True))


def parse_listing(html: str, today: dt.date) -> list[Offer]:
    """Parse active INESC-ID positions from the listing HTML."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    panels = soup.select("div.position-panels div.position-panel")
    if not panels:
        panels = soup.select("div.position-panel")

    today_iso = today.isoformat()
    offers: list[Offer] = []
    seen_keys: set[tuple[str, str]] = set()

    for panel in panels:
        title, position_type = _extract_title_and_type(panel)
        if not title:
            continue

        deadline = _extract_deadline(panel)
        if deadline and deadline < today_iso:
            continue

        reference = _extract_reference(panel)
        url = _extract_url(panel, reference)

        dedup_key = (url, title)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        extra: dict[str, str] = {}
        if reference:
            extra["reference"] = reference

        offers.append(
            Offer(
                source="inesc-id",
                kind="position",
                title=title,
                url=url,
                institution="INESC-ID",
                region="Lisboa",
                position_type=position_type,
                deadline=deadline,
                extra=extra,
            )
        )

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse open positions from INESC-ID."""
    ref_today = today or dt.date.today()
    try:
        html = fetch(LIST_URL)
    except Exception as exc:
        log.warning("Failed to fetch INESC-ID positions: %s", exc)
        return []
    return parse_listing(html, today=ref_today)
