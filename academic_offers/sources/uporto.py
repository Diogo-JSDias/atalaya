"""Universidade do Porto central opportunities archive.

Consumes only the institution's public "prazo=abertas" listing. The parser
keeps research, academic and research-scholarship records, not general training
or unrelated operational vacancies.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://noticias.up.pt/oportunidades/?prazo=abertas"
MAX_PAGES = 5
DEADLINE_PREFIX = re.compile(r"(?:até|prazo(?: de candidatura)?)\s*[:：]?\s*", re.I)
ACADEMIC = re.compile(
    r"professor|docente|investigador|investiga[cç][ãa]o|"
    r"bolsa(?:s)?(?:\s+(?:de\s+)?(?:investiga[cç][ãa]o|p[oó]s[- ]?doutoramento|doutoramento))?|"
    r"p[oó]s[- ]?doutor|doutoramento|research|cient[ií]fic",
    re.I,
)
UPORTO_HOST = "noticias.up.pt"


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == UPORTO_HOST


def _deadline(text: str) -> str | None:
    clean = " ".join(text.split())
    for label in DEADLINE_PREFIX.finditer(clean):
        # Parse only the text immediately after an explicit deadline label.
        value = first_date(clean[label.end():label.end() + 90])
        if value:
            return value
    return None


def _posts(title: str) -> int:
    match = re.search(r"\b(\d{1,2})\s+(?:vagas?|postos?|bolsas?)\b", title, re.I)
    return max(1, int(match.group(1))) if match else 1


def parse_listing(html: str, base_url: str = LIST_URL) -> list[Offer]:
    """Parse relevant cards from the official open-opportunities archive."""
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()

    for article in soup.find_all("article"):
        heading = article.find(["h1", "h2", "h3", "h4", "h5"])
        link = heading.find("a", href=True) if heading else None
        if not link:
            link = article.find("a", href=True)
        if not link:
            continue
        title = " ".join(link.get_text(" ", strip=True).split())
        if not title or not ACADEMIC.search(title):
            continue

        url = urljoin(base_url, link["href"])
        if not _official_url(url) or url in seen:
            continue
        seen.add(url)

        card_text = " ".join(article.get_text(" ", strip=True).split())
        category = ""
        for node in article.find_all(["a", "span", "div", "p"]):
            value = " ".join(node.get_text(" ", strip=True).split())
            if value.casefold() in {"bolsas", "recrutamento"}:
                category = value.title()
                break
        if not category:
            category = "Bolsas" if re.search(r"bolsa", title, re.I) else "Recrutamento"

        deadline = _deadline(card_text)
        is_call = category.casefold() == "bolsas" or bool(re.search(r"bolsa", title, re.I))
        notes = [f"Categoria: {category}"]
        if not deadline:
            notes.append("Prazo não identificado no cartão; confirmar no aviso original.")

        offers.append(Offer(
            source="uporto", kind="call" if is_call else "position",
            title=title, url=url, institution="Universidade do Porto",
            region="Porto", position_type=category,
            deadline=deadline, n_posts=_posts(title), notes=" ".join(notes),
            extra={"uporto_category": category},
        ))
    return offers


def _page_url(page: int) -> str:
    parsed = urlparse(LIST_URL)
    query = parse_qs(parsed.query)
    if page:
        query["oport_paged"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Collect currently open academic/research opportunities from U.Porto."""
    today = today or dt.date.today()
    offers: list[Offer] = []
    seen: set[str] = set()

    for page in range(MAX_PAGES):
        page_url = _page_url(page)
        html = fetch(page_url)
        if not BeautifulSoup(html, "html.parser").find("article"):
            break
        for offer in parse_listing(html, page_url):
            if offer.deadline and offer.deadline < today.isoformat():
                continue
            if offer.url not in seen:
                seen.add(offer.url)
                offers.append(offer)

    log.info("U.Porto opportunities: %d open academic/research entries", len(offers))
    return offers
