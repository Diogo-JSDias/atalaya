"""ITQB NOVA open positions scraper."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

LIST_URL = "https://www.itqb.unl.pt/jobs/"
OFFICIAL_HOSTS = ("itqb.unl.pt", "unl.pt", "diariodarepublica.pt", "dre.pt")
_RANGE_SEP = re.compile(r"\s+[-–—]\s+|\s+(?:to|a|até)\s+", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return parsed.scheme in {"http", "https"} and any(
        host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS
    )


def _extract_deadline(period_text: str) -> str | None:
    """Extract the closing date from an application period string."""
    chunks = _RANGE_SEP.split(period_text)
    dates = [d for chunk in chunks if (d := first_date(chunk))]
    if dates:
        return dates[-1]
    return first_date(period_text)


def parse_listing(html: str, today: dt.date) -> list[Offer]:
    """Parse the ITQB NOVA open-positions table into Offer objects."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", id="all-open-positions", class_="open-positions")
    if container is None:
        return []

    today_iso = today.isoformat()
    offers: list[Offer] = []

    for row in container.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        title = _clean(cells[0].get_text(" ", strip=True))
        area_raw = _clean(cells[1].get_text(" ", strip=True))
        period_text = _clean(cells[2].get_text(" ", strip=True))
        link = cells[3].find("a", href=True)
        if not title or link is None:
            continue

        url = urljoin(LIST_URL, link["href"].strip())
        if not _is_official_url(url):
            continue

        deadline = _extract_deadline(period_text)
        if deadline and deadline < today_iso:
            continue

        offers.append(
            Offer(
                source="itqb-nova",
                kind="position",
                title=title,
                url=url,
                institution="ITQB NOVA",
                region="Lisboa",
                area_raw=area_raw,
                deadline=deadline,
            )
        )

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse open positions from ITQB NOVA."""
    today = today or dt.date.today()
    html = fetch(LIST_URL)
    return parse_listing(html, today=today)
