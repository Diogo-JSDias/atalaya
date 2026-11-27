"""Universidade da Beira Interior open researcher competitions.

The official recruitment page separates researcher competitions from academic
teaching competitions. This adapter parses only the active researcher section
and deliberately fails closed if its structure changes.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.ubi.pt/sites/academicos/pt/pagina/recrutamento"
OFFICIAL_HOSTS = ("ubi.pt", "diariodarepublica.pt")
DATE_RE = re.compile(
    r"(?<!\d)(?:(\d{1,2})[/-](\d{1,2})[/-](20\d{2})|(20\d{2})[/-](\d{1,2})[/-](\d{1,2}))(?!\d)"
)
NOTICE_RE = re.compile(r"\bEdital\s+n[ºo°.]?\s*(\d{1,5}/20\d{2})\b", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _normal(value: str) -> str:
    value = unicodedata.normalize("NFKD", _clean(value).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)
    )


def _has_header(table) -> bool:
    for row in table.find_all("tr"):
        text = _normal(row.get_text(" ", strip=True))
        if (
            "investigador" in text
            and "area cientifica" in text
            and "data limite" in text
        ):
            return True
    return False


def _find_open_table(soup):
    researcher_heading = next(
        (
            tag for tag in soup.find_all(["h1", "h2", "h3", "h4"])
            if "concursos para investigadores" in _normal(tag.get_text(" ", strip=True))
        ),
        None,
    )
    if researcher_heading is None:
        raise RuntimeError(
            "UBI researcher recruitment heading not found; page structure may have changed"
        )

    open_heading = next(
        (
            tag for tag in researcher_heading.find_all_next(
                ["h1", "h2", "h3", "h4", "p", "strong"]
            )
            if "candidaturas a decorrer" in _normal(tag.get_text(" ", strip=True))
        ),
        None,
    )
    if open_heading is None:
        raise RuntimeError(
            "UBI open researcher-candidature section not found; page structure may have changed"
        )

    for element in open_heading.find_all_next(
        ["h1", "h2", "h3", "h4", "p", "strong", "table"]
    ):
        if element.name != "table":
            if "candidaturas encerradas" in _normal(element.get_text(" ", strip=True)):
                break
            continue
        if _has_header(element):
            return element
    raise RuntimeError(
        "UBI open researcher table not found; page structure may have changed"
    )


def _deadline(value: str) -> str | None:
    match = DATE_RE.search(value)
    if not match:
        return None
    try:
        if match.group(1):
            day, month, year = (int(match.group(i)) for i in (1, 2, 3))
        else:
            year, month, day = (int(match.group(i)) for i in (4, 5, 6))
        return dt.date(year, month, day).isoformat()
    except (TypeError, ValueError):
        return None


def _notice_number(value: str) -> str:
    match = NOTICE_RE.search(value)
    return match.group(1) if match else ""


def parse_listing(html: str, base_url: str = LIST_URL) -> list[Offer]:
    """Parse only the UBI 'Candidaturas a decorrer' researcher table."""
    soup = BeautifulSoup(html, "html.parser")
    table = _find_open_table(soup)

    header_row = next(
        row for row in table.find_all("tr")
        if (
            "investigador" in _normal(row.get_text(" ", strip=True))
            and "area cientifica" in _normal(row.get_text(" ", strip=True))
            and "data limite" in _normal(row.get_text(" ", strip=True))
        )
    )
    headers = [
        _normal(cell.get_text(" ", strip=True))
        for cell in header_row.find_all(["th", "td"], recursive=False)
    ]
    if not headers:
        headers = [
            _normal(cell.get_text(" ", strip=True))
            for cell in header_row.find_all(["th", "td"])
        ]

    def index_for(prefix: str, fallback: int) -> int:
        return next((i for i, label in enumerate(headers) if prefix in label), fallback)

    researcher_idx = index_for("investigador", 0)
    area_idx = index_for("area cientifica", 1)
    posts_idx = index_for("postos", 2)
    notice_idx = index_for("edital", 4)
    deadline_idx = index_for("data limite", 5)
    register_idx = index_for("registo", 6)

    offers: list[Offer] = []
    seen: set[str] = set()
    unparsed_rows = 0

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if not cells:
            cells = row.find_all(["th", "td"])
        if row is header_row or len(cells) <= max(
            researcher_idx, area_idx, posts_idx, notice_idx, deadline_idx
        ):
            continue

        role = _clean(cells[researcher_idx].get_text(" ", strip=True))
        area = _clean(cells[area_idx].get_text(" ", strip=True))
        if not role or not area:
            continue

        notice_url = ""
        notice_link = None
        for anchor in cells[notice_idx].find_all("a", href=True):
            candidate = urljoin(base_url, anchor["href"])
            if _official_url(candidate):
                notice_url = candidate
                notice_link = anchor
                break
        if not notice_url:
            unparsed_rows += 1
            continue
        if notice_url in seen:
            continue

        notice_text = _clean(notice_link.get_text(" ", strip=True))
        if not _notice_number(notice_text):
            notice_text = _clean(cells[notice_idx].get_text(" ", strip=True))
        notice = _notice_number(notice_text)
        deadline = _deadline(_clean(cells[deadline_idx].get_text(" ", strip=True)))
        posts_match = re.search(r"\b(\d{1,3})\b", cells[posts_idx].get_text(" ", strip=True))
        n_posts = max(1, int(posts_match.group(1))) if posts_match else 1

        application_url = None
        if len(cells) > register_idx:
            for anchor in cells[register_idx].find_all("a", href=True):
                candidate = urljoin(base_url, anchor["href"])
                if urlparse(candidate).scheme in {"http", "https"}:
                    application_url = candidate
                    break

        notes = []
        if notice:
            notes.append(f"Edital n.º {notice}")
        if not deadline:
            notes.append("Prazo não identificado na listagem; confirmar no edital original.")

        seen.add(notice_url)
        offers.append(Offer(
            source="ubi-investigadores",
            kind="position",
            title=f"{role} — {area}",
            url=notice_url,
            institution="Universidade da Beira Interior",
            region="Castelo Branco",
            position_type=role,
            deadline=deadline,
            n_posts=n_posts,
            notes="; ".join(notes),
            extra={
                "ubi_notice": notice or None,
                "ubi_research_area": area,
                "application_url": application_url,
                "listing_url": base_url,
            },
        ))

    if unparsed_rows:
        raise RuntimeError(
            f"{unparsed_rows} UBI open researcher row(s) had no official notice URL"
        )
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Collect UBI researcher competitions whose application deadline has not passed."""
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL))
    current = [
        offer for offer in offers
        if not offer.deadline or offer.deadline >= today.isoformat()
    ]
    log.info("UBI researcher competitions: %d current entries", len(current))
    return current
