"""IEETA (Universidade de Aveiro) open positions adapter."""
from __future__ import annotations

import datetime as dt
import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.ieeta.pt/join-us/"
INSTITUTION = "IEETA – Universidade de Aveiro"
REGION = "Centro"
OFFICIAL_HOSTS = ("ieeta.pt", "ua.pt", "diariodarepublica.pt", "dre.pt")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)
    )


def _extract_url(article: Tag, base_url: str) -> str:
    anchor = article.select_one("h2.ieeta-jobcard__title a[href]") or article.find("a", href=True)
    if not anchor:
        return ""
    candidate = urljoin(base_url, str(anchor["href"]).strip())
    return candidate if _official_url(candidate) else ""


def _extract_deadline(article: Tag) -> str | None:
    for dt_el in article.find_all("dt"):
        label = _clean(dt_el.get_text(" ", strip=True)).rstrip(":").casefold()
        if label != "application deadline":
            continue
        dd_el = dt_el.find_next_sibling("dd")
        if dd_el:
            return first_date(_clean(dd_el.get_text(" ", strip=True)))
    return None


def parse_listing(
    html: str,
    today: dt.date | None = None,
    *,
    base_url: str = LIST_URL,
) -> list[Offer]:
    """Parse open positions from the IEETA join-us page."""
    if not html or not html.strip():
        return []
    today = today or dt.date.today()
    today_iso = today.isoformat()

    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen_urls: set[str] = set()

    for article in soup.select('article[id^="job-"]'):
        title_el = article.select_one("h2.ieeta-jobcard__title")
        title = _clean(title_el.get_text(" ", strip=True)) if title_el else ""
        if not title:
            continue

        url = _extract_url(article, base_url)
        if not url or url in seen_urls:
            continue

        deadline = _extract_deadline(article)
        if deadline and deadline < today_iso:
            continue

        seen_urls.add(url)
        offers.append(
            Offer(
                source="ieeta",
                kind="position",
                title=title,
                url=url,
                institution=INSTITUTION,
                region=REGION,
                deadline=deadline,
            )
        )

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse open positions from IEETA."""
    today = today or dt.date.today()
    html = fetch(LIST_URL)
    offers = parse_listing(html, today=today, base_url=LIST_URL)
    log.info("IEETA: %d open positions", len(offers))
    return offers
