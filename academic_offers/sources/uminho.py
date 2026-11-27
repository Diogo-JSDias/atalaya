"""Universidade do Minho central academic recruitment portal.

Covers the central recruitment portal (https://recrutamento.uminho.pt/) for
career teaching staff (DOC) and fixed-term or career researchers (INVT, INV).
Excludes managerial (DIR) and technical/administrative staff (PTAG), as well
as closed or post-application procedures.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://recrutamento.uminho.pt/"
CONCURSOS_PATH = "/portal-recrutamento/frontoffice/concursos.xhtml"
ACADEMIC_TYPES: tuple[tuple[str, str], ...] = (
    ("DOC", "Docentes de Carreira"),
    ("INVT", "Investigadores a Termo"),
    ("INV", "Investigadores de Carreira"),
)
OFFICIAL_HOSTS = ("uminho.pt", "diariodarepublica.pt", "dre.pt")

CLOSED_STATUSES = {
    "audiencia",
    "audiência",
    "cancelado",
    "concluido",
    "concluído",
    "em avaliacao",
    "em avaliação",
    "encerrado",
    "homologado",
    "lista final",
    "lista provisoria",
    "lista provisória",
    "pendente homologacao",
    "pendente homologação",
    "terminado",
}

POSTS_RE = re.compile(r"\b(\d{1,3})\s+(?:vagas?(?:\(s\))?|postos?|lugares?)\b", re.I)
OPENING_RE = re.compile(r"abertura\s*:\s*(.+?)(?=fecho\s*:|$)", re.I)
CLOSING_RE = re.compile(r"(?:fecho|prazo(?:\s+de\s+candidatura)?)\s*:\s*(.+)", re.I)
WINDOW_OPEN_RE = re.compile(r"window\.open\(\s*['\"]([^'\"]+)['\"]")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _normal(value: str) -> str:
    return _clean(value).casefold()


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)
    )


def _unescape_js_url(raw: str) -> str:
    return raw.replace(r"\/", "/").replace(r"\-", "-")


def _extract_card_url(card, base_url: str) -> str:
    for anchor in card.find_all("a", href=True):
        candidate = urljoin(base_url, anchor["href"])
        if _official_url(candidate):
            return candidate
    for button in card.find_all("button", onclick=True):
        match = WINDOW_OPEN_RE.search(button["onclick"])
        if match:
            candidate = urljoin(base_url, _unescape_js_url(match.group(1)))
            if _official_url(candidate):
                return candidate
    return ""


def _extract_meta(card) -> tuple[str, str, int]:
    unit = ""
    briefcase = ""
    n_posts = 1
    for item in card.select(".concurso-react-meta .meta-item"):
        text = _clean(item.get_text(" ", strip=True))
        if not text:
            continue
        classes = " ".join(
            cls for icon in item.find_all("i") for cls in icon.get("class", [])
        )
        if "pi-building" in classes and not unit:
            unit = text
        elif "pi-briefcase" in classes and not briefcase:
            briefcase = text
        elif "pi-users" in classes:
            match = POSTS_RE.search(text)
            if match:
                n_posts = max(1, int(match.group(1)))
    if n_posts == 1:
        match = POSTS_RE.search(_clean(card.get_text(" ", strip=True)))
        if match:
            n_posts = max(1, int(match.group(1)))
    return unit, briefcase, n_posts


def _extract_dates(card) -> tuple[str | None, str | None]:
    dates_el = card.select_one(".concurso-react-dates")
    if not dates_el:
        return None, None
    text = _clean(dates_el.get_text(" ", strip=True))
    published = None
    deadline = None

    open_match = OPENING_RE.search(text)
    if open_match:
        published = first_date(open_match.group(1))

    close_match = CLOSING_RE.search(text)
    if close_match:
        deadline = first_date(close_match.group(1))

    return published, deadline


def discover_category_urls(home_html: str, base_url: str = LIST_URL) -> list[tuple[str, str, str]]:
    """Return (code, label, url) tuples for DOC, INVT and INV listings."""
    soup = BeautifulSoup(home_html, "html.parser")
    by_code: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        candidate = urljoin(base_url, anchor["href"])
        if not _official_url(candidate):
            continue
        query = parse_qs(urlparse(candidate).query)
        tipos = query.get("tipo") or []
        if tipos:
            code = tipos[0].upper()
            if code in dict(ACADEMIC_TYPES) and code not in by_code:
                by_code[code] = candidate

    results: list[tuple[str, str, str]] = []
    for code, label in ACADEMIC_TYPES:
        url = by_code.get(code) or urljoin(base_url, f"{CONCURSOS_PATH}?tipo={code}")
        if _official_url(url):
            results.append((code, label, url))
    return results


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    position_type: str = "Pessoal docente/investigador",
    category_code: str | None = None,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse open academic recruitment cards from a UMinho portal listing page."""
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()

    for card in soup.select(".concurso-react-card"):
        status_el = card.select_one(".concurso-react-badges .badge")
        status = _clean(status_el.get_text(" ", strip=True)) if status_el else ""
        if status and _normal(status) in CLOSED_STATUSES:
            continue

        title_el = card.select_one(".concurso-react-title")
        title = _clean(title_el.get_text(" ", strip=True)) if title_el else ""
        if not title:
            continue

        url = _extract_card_url(card, base_url)
        if not url or url in seen:
            continue
        seen.add(url)

        published, deadline = _extract_dates(card)
        if today and deadline and deadline < today.isoformat():
            continue

        ref_el = card.select_one(".concurso-react-ref")
        ref = _clean(ref_el.get_text(" ", strip=True)) if ref_el else ""
        unit, briefcase, n_posts = _extract_meta(card)

        institution = f"Universidade do Minho — {unit}" if unit else "Universidade do Minho"
        notes_parts = []
        if ref:
            notes_parts.append(f"Ref. {ref}.")
        if status:
            notes_parts.append(f"Estado: {status}.")
        if not deadline:
            notes_parts.append("Prazo não identificado na listagem; confirmar no aviso oficial.")

        offers.append(Offer(
            source="uminho",
            kind="position",
            title=title,
            url=url,
            institution=institution,
            region="Braga",
            position_type=briefcase or position_type,
            published=published,
            deadline=deadline,
            n_posts=n_posts,
            notes=" ".join(notes_parts),
            extra={
                "uminho_ref": ref or None,
                "uminho_status": status or None,
                "uminho_unit": unit or None,
                "uminho_type": category_code,
                "listing_url": base_url,
            },
        ))

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Collect open teaching and research opportunities from UMinho's central portal."""
    today = today or dt.date.today()
    home_html = fetch(LIST_URL)
    categories = discover_category_urls(home_html, base_url=LIST_URL)

    offers: list[Offer] = []
    seen_urls: set[str] = set()
    for code, label, url in categories:
        page_offers = parse_listing(
            fetch(url),
            base_url=url,
            position_type=label,
            category_code=code,
            today=today,
        )
        for offer in page_offers:
            if offer.url not in seen_urls:
                seen_urls.add(offer.url)
                offers.append(offer)

    log.info("UMinho central portal: %d open teaching/research entries", len(offers))
    return offers
