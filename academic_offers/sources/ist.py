"""Instituto Superior Técnico (IST / ULisboa) DRH recruitment scraper."""
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

BASE_URL = "https://drh.tecnico.ulisboa.pt/"
BOLSEIROS_URL = "https://drh.tecnico.ulisboa.pt/bolseiros/recrutamento/"
DOCENTES_URL = "https://drh.tecnico.ulisboa.pt/docentes/recrutamento/pessoal-docente-de-carreira/"
RESEARCHER_URL = "https://drh.tecnico.ulisboa.pt/investigadores/recrutamento/career-researcher/"
DL57_URL = "https://drh.tecnico.ulisboa.pt/investigadores/recrutamento/dl-572016/"

PAGES = (
    BOLSEIROS_URL,
    DOCENTES_URL,
    RESEARCHER_URL,
    DL57_URL,
)

OFFICIAL_HOSTS = (
    "drh.tecnico.ulisboa.pt",
    "tecnico.ulisboa.pt",
    "ulisboa.pt",
    "diariodarepublica.pt",
    "dre.pt",
)

INSTITUTION = "Instituto Superior Técnico – ULisboa"
REGION = "Lisboa"

_CLOSED_RE = re.compile(
    r"cessa[cç][ãa]o|cancelad[oa]|encerrad[oa]|terminad[oa]|fechad[oa]|"
    r"sem\s+efeito|anulad[oa]|conclu[ií]d[oa]|closed|cancelled|expired",
    re.IGNORECASE,
)
_LEADING_INT_RE = re.compile(r"^\s*(\d{1,3})\b\s*(.*)$")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower().split(":")[0]
    return any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)


def _cell_links(cell: Tag, base_url: str) -> list[str]:
    urls: list[str] = []
    for link in cell.find_all("a", href=True):
        href = _clean(link.get("href"))
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        candidate = urljoin(base_url, href)
        if _is_official_url(candidate):
            urls.append(candidate)
    return urls


def _pick_url(cells: list[Tag], indices: tuple[int, ...], base_url: str) -> str:
    for idx in indices:
        if idx < len(cells):
            for candidate in _cell_links(cells[idx], base_url):
                # Skip generic recruitment guide PDFs when a specific notice exists
                if candidate.lower().endswith("info_concs_doc_v2.pdf"):
                    continue
                return candidate
    for cell in cells:
        for candidate in _cell_links(cell, base_url):
            if candidate.lower().endswith("info_concs_doc_v2.pdf"):
                continue
            return candidate
    return ""


def _parse_posts(text: str) -> tuple[int, str]:
    match = _LEADING_INT_RE.match(text)
    if not match:
        return 1, text
    return max(1, int(match.group(1))), _clean(match.group(2))


def _detect_table_kind(table: Tag, base_url: str, fallback: str | None = None) -> str:
    header_text = " ".join(
        _clean(cell.get_text(" ", strip=True)).lower()
        for cell in table.find_all("th")
    )
    if "tipo de bolsa" in header_text or "responsável" in header_text:
        return "bolseiros"
    if "submissão" in header_text or "categoria" in header_text:
        return "researcher"
    if "posição" in header_text or "edital dr" in header_text:
        return "docentes"

    lower_url = base_url.lower()
    if "bolseiros" in lower_url:
        return "bolseiros"
    if "docentes" in lower_url:
        return "docentes"
    if "career-researcher" in lower_url or "dl-572016" in lower_url:
        return "researcher"
    if fallback:
        return fallback

    for row in table.find_all("tr"):
        tds = row.find_all("td", recursive=False)
        if len(tds) == 7:
            return "docentes"
        if len(tds) == 8:
            # Bolseiros has open date in col 6 and deadline in col 7; researcher has deadline in col 6
            if first_date(_clean(tds[7].get_text(" ", strip=True))):
                return "bolseiros"
            return "researcher"
    return "docentes"


def _parse_bolseiros_row(cells: list[Tag], base_url: str, today_iso: str) -> Offer | None:
    if len(cells) < 8:
        return None
    deadline_text = _clean(cells[7].get_text(" ", strip=True))
    if _CLOSED_RE.search(deadline_text):
        return None
    deadline = first_date(deadline_text)
    if deadline and deadline < today_iso:
        return None

    url = _pick_url(cells, (4, 5), base_url)
    if not url:
        return None

    n_posts, _ = _parse_posts(_clean(cells[0].get_text(" ", strip=True)))
    grant_type = _clean(cells[1].get_text(" ", strip=True))
    supervisor = _clean(cells[2].get_text(" ", strip=True))
    area = _clean(cells[3].get_text(" ", strip=True))
    published = first_date(_clean(cells[6].get_text(" ", strip=True)))

    if grant_type and area:
        title = f"{grant_type} — {area}"
    else:
        title = grant_type or area
    if not title:
        return None

    notes = f"Responsável: {supervisor}" if supervisor else ""
    return Offer(
        source="ist",
        kind="position",
        title=title,
        url=url,
        institution=INSTITUTION,
        region=REGION,
        position_type=grant_type or "Bolsa de investigação",
        area_raw=area,
        deadline=deadline,
        published=published,
        n_posts=n_posts,
        notes=notes,
        extra={"category": "bolseiros"},
    )


def _parse_docentes_row(cells: list[Tag], base_url: str, today_iso: str) -> Offer | None:
    if len(cells) < 7:
        return None
    deadline_text = _clean(cells[5].get_text(" ", strip=True))
    if _CLOSED_RE.search(deadline_text):
        return None
    deadline = first_date(deadline_text)
    if deadline and deadline < today_iso:
        return None

    url = _pick_url(cells, (6, 3), base_url)
    if not url:
        return None

    n_posts, position_type = _parse_posts(_clean(cells[0].get_text(" ", strip=True)))
    department = _clean(cells[1].get_text(" ", strip=True))
    area = _clean(cells[2].get_text(" ", strip=True))
    published = first_date(_clean(cells[4].get_text(" ", strip=True)))

    if position_type and area:
        title = f"{position_type} — {area}"
    else:
        title = position_type or area
    if not title:
        return None

    notes = f"Departamento: {department}" if department else ""
    extra = {"category": "docentes"}
    if department:
        extra["department"] = department

    return Offer(
        source="ist",
        kind="position",
        title=title,
        url=url,
        institution=INSTITUTION,
        region=REGION,
        position_type=position_type or "Pessoal docente de carreira",
        area_raw=area,
        deadline=deadline,
        published=published,
        n_posts=n_posts,
        notes=notes,
        extra=extra,
    )


def _parse_researcher_row(cells: list[Tag], base_url: str, today_iso: str) -> Offer | None:
    if len(cells) < 8:
        return None
    deadline_text = _clean(cells[6].get_text(" ", strip=True))
    if _CLOSED_RE.search(deadline_text):
        return None
    deadline = first_date(deadline_text)
    if deadline and deadline < today_iso:
        return None

    url = _pick_url(cells, (7, 4, 5), base_url)
    if not url:
        return None

    n_posts, _ = _parse_posts(_clean(cells[0].get_text(" ", strip=True)))
    department = _clean(cells[1].get_text(" ", strip=True))
    area = _clean(cells[2].get_text(" ", strip=True))
    category = _clean(cells[3].get_text(" ", strip=True))

    if category and area:
        title = f"{category} — {area}"
    else:
        title = category or area
    if not title:
        return None

    notes = f"Departamento: {department}" if department else ""
    extra = {"category": "investigadores"}
    if department:
        extra["department"] = department

    return Offer(
        source="ist",
        kind="position",
        title=title,
        url=url,
        institution=INSTITUTION,
        region=REGION,
        position_type=category or "Investigador",
        area_raw=area,
        deadline=deadline,
        n_posts=n_posts,
        notes=notes,
        extra=extra,
    )


def parse_listing(html: str, today: dt.date, base_url: str = BASE_URL) -> list[Offer]:
    """Parse active IST DRH recruitment table rows into Offer objects."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    today_iso = today.isoformat()
    offers: list[Offer] = []
    seen: set[tuple[str, str]] = set()
    last_kind: str | None = None

    for table in soup.find_all("table"):
        kind = _detect_table_kind(table, base_url, fallback=last_kind)
        last_kind = kind

        for row in table.find_all("tr"):
            if row.find("th"):
                continue
            cells = row.find_all("td", recursive=False)
            if not cells:
                continue
            row_text = _clean(row.get_text(" ", strip=True))
            if _CLOSED_RE.search(row_text):
                continue

            if kind == "bolseiros":
                offer = _parse_bolseiros_row(cells, base_url, today_iso)
            elif kind == "docentes":
                offer = _parse_docentes_row(cells, base_url, today_iso)
            else:
                offer = _parse_researcher_row(cells, base_url, today_iso)

            if offer is None:
                continue
            key = (offer.url, offer.title)
            if key in seen:
                continue
            seen.add(key)
            offers.append(offer)

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse active recruitment calls across IST DRH pages."""
    today = today or dt.date.today()
    offers: list[Offer] = []
    seen: set[tuple[str, str]] = set()

    for url in PAGES:
        try:
            html = fetch(url)
        except Exception:
            log.warning("Failed to fetch IST page %s", url, exc_info=True)
            continue
        for offer in parse_listing(html, today, base_url=url):
            key = (offer.url, offer.title)
            if key not in seen:
                seen.add(key)
                offers.append(offer)

    return offers
