"""Centro ALGORITMI (Universidade do Minho) open positions adapter."""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://algoritmi.uminho.pt/open-positions/"
INSTITUTION = "Centro ALGORITMI – Universidade do Minho"
REGION = "Norte"
OFFICIAL_HOSTS = ("algoritmi.uminho.pt", "uminho.pt", "diariodarepublica.pt", "dre.pt")

DATE_RANGE_SPLIT_RE = re.compile(r"\s*[-–—]\s*")
REF_PREFIX_RE = re.compile(r"^refer[êe]ncia\s*:\s*", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)
    )


def _find_open_panel(soup: BeautifulSoup) -> Tag | None:
    """Return the Elementor tab panel corresponding to the 'Open' tab."""
    for tab_title in soup.select(".elementor-tab-title"):
        if _clean(tab_title.get_text(" ", strip=True)).casefold() != "open":
            continue
        controls = tab_title.get("aria-controls")
        if controls:
            panel = soup.find(id=controls)
            if panel is not None:
                return panel
        data_tab = tab_title.get("data-tab")
        if data_tab:
            panel = soup.select_one(f'.elementor-tab-content[data-tab="{data_tab}"]')
            if panel is not None:
                return panel
        title_id = tab_title.get("id")
        if title_id:
            panel = soup.select_one(f'.elementor-tab-content[aria-labelledby="{title_id}"]')
            if panel is not None:
                return panel
    return None


def _extract_dates(card: Tag) -> tuple[str | None, str | None]:
    date_el = card.select_one("p.news-date")
    if not date_el:
        return None, None
    text = _clean(date_el.get_text(" ", strip=True))
    if not text:
        return None, None
    parts = DATE_RANGE_SPLIT_RE.split(text, maxsplit=1)
    if len(parts) == 2:
        return first_date(parts[0]), first_date(parts[1])
    return None, first_date(text)


def _extract_url(card: Tag, base_url: str) -> str:
    anchor = card.select_one(".news-card-footer a[href]") or card.find("a", href=True)
    if not anchor:
        return ""
    candidate = urljoin(base_url, str(anchor["href"]).strip())
    return candidate if _official_url(candidate) else ""


def parse_listing(
    html: str,
    today: dt.date | None = None,
    *,
    base_url: str = LIST_URL,
) -> list[Offer]:
    """Parse open positions from the Centro ALGORITMI 'Open' tab."""
    if not html or not html.strip():
        return []
    today = today or dt.date.today()
    today_iso = today.isoformat()

    soup = BeautifulSoup(html, "html.parser")
    panel = _find_open_panel(soup)
    if panel is None:
        return []

    offers: list[Offer] = []
    seen_urls: set[str] = set()

    for card in panel.select(".news-card"):
        title_el = card.select_one("p.news-title")
        title = _clean(title_el.get_text(" ", strip=True)) if title_el else ""
        if not title:
            continue

        url = _extract_url(card, base_url)
        if not url or url in seen_urls:
            continue

        published, deadline = _extract_dates(card)
        if deadline and deadline < today_iso:
            continue

        seen_urls.add(url)

        ref_el = card.select_one("p.positions-reference")
        ref = REF_PREFIX_RE.sub("", _clean(ref_el.get_text(" ", strip=True))) if ref_el else ""
        desc_el = card.select_one("p.news-description")
        notes = _clean(desc_el.get_text(" ", strip=True)) if desc_el else ""

        extra = {"algoritmi_ref": ref} if ref else {}
        offers.append(
            Offer(
                source="algoritmi",
                kind="position",
                title=title,
                url=url,
                institution=INSTITUTION,
                region=REGION,
                published=published,
                deadline=deadline,
                notes=notes,
                extra=extra,
            )
        )

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse open positions from Centro ALGORITMI."""
    today = today or dt.date.today()
    html = fetch(LIST_URL)
    offers = parse_listing(html, today=today, base_url=LIST_URL)
    log.info("Centro ALGORITMI: %d open positions", len(offers))
    return offers
