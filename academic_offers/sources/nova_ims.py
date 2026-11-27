"""NOVA Information Management School (NOVA IMS) employment board.

The listing links to official vacancy notices in PDF form. This adapter reads
those notices to distinguish explicit application dates from open-ended
expressions of interest and from statutory working-day periods.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..dates import lisbon_working_day_deadline
from ..http import fetch, fetch_bytes
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://novaims.unl.pt/pt/quem-somos/bolsa-de-emprego/"
MAX_PDF_PAGES = 30
OFFICIAL_HOSTS = ("novaims.unl.pt",)

PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}
MONTH_PATTERN = "|".join(sorted(PT_MONTHS, key=len, reverse=True))
DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](20\d{2})(?!\d)")
DATE_ISO = re.compile(r"(?<!\d)(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)")
DATE_PT = re.compile(
    rf"(?<!\d)(\d{{1,2}})\s+de\s+({MONTH_PATTERN})\s+de\s+(20\d{{2}})(?!\d)",
    re.I,
)
APPLICATION_WINDOW = re.compile(r"prazo\s+de\s+candidatura|prazo\s+para\s+apresenta[cç][ãa]o\s+de\s+candidaturas", re.I)
WORKING_DAYS = re.compile(
    r"prazo\s+de\s+(\d{1,3})\s+dias?\s+[úu]teis.{0,180}?"
    r"(?:a\s+contar|contado|contada).{0,100}?"
    r"(?:dia\s+imediato|dia\s+seguinte).{0,100}?"
    r"(?:publica[cç][ãa]o|publicado)",
    re.I,
)
FUNCTION_FIELD = re.compile(
    r"fun[cç][ãa]o\s+a\s+desempenhar\s*:\s*(.*?)"
    r"(?=\s*(?:descri[cç][ãa]o\s+das?\s+fun[cç][õo]es?|requisitos?|"
    r"habilita[cç][õo]es?\s+m[ií]nimas?|idade\s+m[ií]nima|tipo\s+de\s+contrato|"
    r"dura[cç][ãa]o\s+do\s+contrato|ficheiro[s(]))",
    re.I,
)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)
        and parsed.path.lower().endswith(".pdf")
    )


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a public NOVA IMS PDF notice."""
    reader = PdfReader(io.BytesIO(data))
    return _clean(" ".join(page.extract_text() or "" for page in reader.pages))


def _date_tokens(text: str) -> list[dt.date]:
    values: list[tuple[int, dt.date]] = []
    for pattern, kind in ((DATE_DMY, "dmy"), (DATE_ISO, "iso"), (DATE_PT, "pt")):
        for match in pattern.finditer(text):
            try:
                if kind == "dmy":
                    day, month, year = (int(value) for value in match.groups())
                elif kind == "iso":
                    year, month, day = (int(value) for value in match.groups())
                else:
                    day = int(match.group(1))
                    month = PT_MONTHS[match.group(2).casefold()]
                    year = int(match.group(3))
                values.append((match.start(), dt.date(year, month, day)))
            except (TypeError, ValueError):
                continue
    deduplicated = {(position, value.isoformat()): value for position, value in values}
    return [value for (_, _), value in sorted(deduplicated.items(), key=lambda item: item[0][0])]


def _add_business_days(first_day: dt.date, days: int) -> dt.date:
    """Compatibility wrapper around the shared Lisbon holiday calendar."""
    return lisbon_working_day_deadline(first_day, days)


def parse_notice_text(text: str) -> dict[str, str | None]:
    """Read an explicit application deadline or a statutory working-day period."""
    clean = _clean(text)
    window = APPLICATION_WINDOW.search(clean)
    if window:
        dates = _date_tokens(clean[window.end():window.end() + 700])
        if dates:
            return {"deadline": dates[-1].isoformat(), "deadline_basis": "explicit"}

    working_days = WORKING_DAYS.search(clean)
    if working_days:
        publication_dates = _date_tokens(clean[:min(len(clean), 700)])
        if publication_dates:
            publication = publication_dates[0]
            first_counted_day = publication + dt.timedelta(days=1)
            deadline = _add_business_days(first_counted_day, int(working_days.group(1)))
            return {
                "deadline": deadline.isoformat(),
                "deadline_basis": "working-days",
            }
    return {"deadline": None, "deadline_basis": None}


def _job_card(anchor):
    """Return the smallest ancestor containing the job's labelled fields and PDF link."""
    for parent in anchor.parents:
        if parent.name in {"main", "body", "html", "[document]"}:
            break
        text = _clean(parent.get_text(" ", strip=True))
        pdf_links = [
            link for link in parent.find_all("a", href=True)
            if _official_pdf_url(urljoin(LIST_URL, link["href"]))
        ]
        if (
            re.search(r"Institui[cç][ãa]o\s*:", text, re.I)
            and re.search(r"Fun[cç][ãa]o\s+a\s+desempenhar\s*:", text, re.I)
            and parent.find(["h2", "h3", "h4", "h5"]) is not None
            and len(pdf_links) == 1
            and pdf_links[0] is anchor
        ):
            return parent
    return None


def _title(card, anchor) -> str:
    text = _clean(card.get_text(" ", strip=True))
    match = FUNCTION_FIELD.search(text)
    if match:
        title = _clean(match.group(1)).strip(" -:;")
        if title:
            return title
    heading = card.find(["h2", "h3", "h4", "h5"])
    if heading:
        title = _clean(heading.get_text(" ", strip=True))
        if title:
            return title
    return _clean(anchor.get_text(" ", strip=True))


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse the NOVA IMS job board and enrich each official PDF notice."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    offers: list[Offer] = []
    seen: set[str] = set()
    attempted = 0

    for anchor in main.find_all("a", href=True):
        url = urljoin(base_url, anchor["href"])
        if not _official_pdf_url(url) or url in seen:
            continue
        card = _job_card(anchor)
        if card is None:
            continue
        title = _title(card, anchor)
        if not title or title.casefold() in {"ficheiro(s) para consulta, relativos à oferta", "edital"}:
            continue
        if not re.search(
            r"bolsa|investiga|professor|docente|assistant professor|research",
            title,
            re.I,
        ):
            continue
        seen.add(url)
        attempted += 1
        if attempted > MAX_PDF_PAGES:
            log.warning("NOVA IMS job board exceeded the %d-PDF parsing limit", MAX_PDF_PAGES)
            break

        try:
            notice_text = extract_pdf_text(fetch_bytes(url))
        except Exception as exc:
            log.info("NOVA IMS notice PDF unavailable for %s: %s", url, type(exc).__name__)
            notice_text = ""
        metadata = parse_notice_text(notice_text)

        deadline = metadata["deadline"]
        if deadline and deadline < today.isoformat():
            continue

        is_scholarship = bool(re.search(r"bolsa", title, re.I))
        is_interest = bool(re.search(r"manifesta[cç][ãa]o de interesse", _clean(card.get_text(" ", strip=True)), re.I))
        kind = "call" if is_scholarship else "position"
        position_type = (
            "Bolsa de investigação" if is_scholarship
            else "Manifestação de interesse docente" if is_interest
            else "Docência/investigação"
        )
        notes = []
        if metadata["deadline_basis"] == "working-days":
            notes.append(
                "Prazo calculado a partir do número de dias úteis e da data de publicação "
                "expressos no edital; confirma a contagem no aviso oficial."
            )
        elif not deadline and is_interest:
            notes.append("Manifestação de interesse; o aviso não indica prazo final.")
        elif not deadline:
            notes.append("Prazo não identificado no edital; confirmar no aviso original.")

        offers.append(Offer(
            source="nova-ims",
            kind=kind,
            title=title,
            url=url,
            institution="Universidade NOVA de Lisboa – NOVA IMS",
            region="Lisboa",
            position_type=position_type,
            deadline=deadline,
            notes=" ".join(notes),
            extra={
                "listing_url": base_url,
                "deadline_basis": metadata["deadline_basis"],
            },
        ))

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("NOVA IMS: %d current academic opportunities", len(offers))
    return offers
