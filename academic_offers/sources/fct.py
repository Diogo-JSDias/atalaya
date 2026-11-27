"""Fundação para a Ciência e a Tecnologia (FCT): open calls index.

Only the official public "open" tab is consumed. The list is an index; each
record links to the FCT notice/detail page. Dates are stored only when an
explicit day/month/year deadline is present in the card text.
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

FCT_OPEN = "https://www.fct.pt/concursos/?paged=1&tab=open"
FCT_HOST = "www.fct.pt"
DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](20\d{2})(?!\d)")
DEADLINE_LABEL = re.compile(
    r"(?:data\s+limite|prazo(?:\s+(?:de|para))?\s+candidaturas?|"
    r"submiss[aã]o\s+de\s+candidaturas|candidaturas\s+até)\s*[:：–-]?\s*(.{0,100})",
    re.I,
)


def _deadline(text: str) -> str | None:
    """Return a full numeric date only when it is attached to a deadline label."""
    for label in DEADLINE_LABEL.finditer(text):
        for day, month, year in DATE_DMY.findall(label.group(1)):
            try:
                return dt.date(int(year), int(month), int(day)).isoformat()
            except ValueError:
                continue
    return None


def parse_open_listing(html: str, base_url: str = FCT_OPEN) -> list[Offer]:
    """Parse opportunity links from the official open-calls tab."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    offers: list[Offer] = []
    seen: set[str] = set()

    for a in main.select("a[href]"):
        title = " ".join(a.get_text(" ", strip=True).split())
        if len(title) < 12:
            continue
        url = urljoin(base_url, a["href"])
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {FCT_HOST, "fct.pt"}:
            continue
        if url.rstrip("/") in { "https://www.fct.pt/concursos", "https://fct.pt/concursos" }:
            continue
        if url in seen:
            continue

        # Read the closest card-like ancestor only. Never climb to the document
        # root: doing so would let another call elsewhere on the page make a
        # navigation/footer link look relevant.
        card = a
        for _ in range(6):
            parent = card.parent
            if parent is None or parent.name in {"main", "body", "html", "[document]"}:
                break
            card = parent
            classes = " ".join(card.get("class", []))
            if card.name in {"article", "li"} or re.search(
                r"\b(card|item|call|contest|opportunit|entry)\b", classes, re.I
            ):
                break
        card_text = " ".join(card.get_text(" ", strip=True).split())
        if not card_text:
            card_text = title
        # Avoid navigation/footer links even if their labels happen to be long.
        if not re.search(r"\b(data limite|candidaturas|concurso|bolsa|emprego científico|investiga)", card_text, re.I):
            continue

        seen.add(url)
        offers.append(Offer(
            source="fct", kind="call", title=title, url=url,
            institution="Fundação para a Ciência e a Tecnologia",
            region="Portugal", position_type="Concurso de financiamento",
            deadline=_deadline(card_text),
            notes="Concurso listado no separador oficial de concursos abertos da FCT. "
                  "Confirma elegibilidade, calendário e condições no aviso original.",
        ))
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    offers: list[Offer] = []
    seen: set[str] = set()
    # The public listing uses a paged query parameter. Stop at the first empty
    # page and cap requests so a changed pagination control cannot cause a crawl.
    for page in range(1, 6):
        page_url = FCT_OPEN.replace("paged=1", "paged=" + str(page))
        page_offers = parse_open_listing(fetch(page_url), page_url)
        if not page_offers:
            break
        for offer in page_offers:
            if offer.url not in seen:
                seen.add(offer.url)
                offers.append(offer)
    log.info("FCT open calls: %d candidate records", len(offers))
    return offers
