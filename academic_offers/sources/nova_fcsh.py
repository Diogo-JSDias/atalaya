"""NOVA FCSH researcher competitions.

The faculty page can retain notices whose application windows have expired.
For that reason this adapter only accepts the official DRE extract PDF (which
contains the publication date and statutory period), computes the legal
deadline, and excludes calls that have already closed.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import re
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..dates import lisbon_working_day_deadline
from ..http import fetch, fetch_bytes
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.fcsh.unl.pt/faculdade/concursos_para_investigadores/"
OFFICIAL_HOSTS = {"fcsh.unl.pt", "www.fcsh.unl.pt"}
NOTICE_PATH = "/static/documentos/concursos/investigadores/"
MAX_NOTICE_PDFS = 30

PUBLICATION_DATE = re.compile(r"(?<!\d)(\d{2})[-/.](\d{2})[-/.](20\d{2})(?!\d)")
OPEN_PERIOD = re.compile(
    r"prazo\s+de\s+(\d{1,3})\s+dias?\s+[úu]teis\s*,?\s*"
    r"a\s+contar\s+do\s+dia\s+[úu]til\s+imediato\s+ao\s+da\s+presente\s+"
    r"publica[cç][ãa]o",
    re.I,
)
NOTICE_NUMBER = re.compile(
    r"Aviso(?:\s*\(extrato\))?\s+n\.?\s*[º°o]?\s*([0-9]{1,6}/20\d{2}/\d+)",
    re.I,
)
VACANCY_COUNT = re.compile(
    r"contrata[cç][ãa]o\s+de\s+(\d{1,3})\s*(?:\([^)]*\)\s*)?"
    r"(?:Investigador|Assistente\s+de\s+Investiga[cç][ãa]o)",
    re.I,
)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_extract_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    path = unquote(parsed.path).lower()
    return (
        parsed.scheme in {"http", "https"}
        and (host in OFFICIAL_HOSTS)
        and path.startswith(NOTICE_PATH)
        and path.endswith(".pdf")
        and bool(re.search(r"aviso\s*\(extrato\)", path, re.I))
    )


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a text-based official NOVA FCSH PDF."""
    reader = PdfReader(io.BytesIO(data))
    return _clean(" ".join(page.extract_text() or "" for page in reader.pages))


def parse_notice_text(text: str) -> dict[str, str | int | None]:
    """Read the DRE publication date and legal working-day term from an extract."""
    clean = _clean(text)
    date_match = PUBLICATION_DATE.search(clean)
    period_match = OPEN_PERIOD.search(clean)
    number_match = NOTICE_NUMBER.search(clean)

    publication_date = None
    if date_match:
        try:
            day, month, year = (int(value) for value in date_match.groups())
            publication_date = dt.date(year, month, day)
        except ValueError:
            publication_date = None

    deadline = None
    days = int(period_match.group(1)) if period_match else None
    if publication_date and days:
        first_counted_day = publication_date + dt.timedelta(days=1)
        deadline = lisbon_working_day_deadline(first_counted_day, days)

    summary_match = re.search(
        r"Sumário\s*:\s*(.*?)(?=\s+(?:Em cumprimento|Nos termos|Para os devidos efeitos))",
        clean,
        re.I,
    )
    title = _clean(summary_match.group(1)).strip(" .;") if summary_match else ""
    count_match = VACANCY_COUNT.search(clean)
    vacancy_count = int(count_match.group(1)) if count_match else 1

    return {
        "publication_date": publication_date.isoformat() if publication_date else None,
        "deadline": deadline.isoformat() if deadline else None,
        "deadline_days": days,
        "notice_number": number_match.group(1) if number_match else None,
        "title": title,
        "vacancy_count": vacancy_count,
    }


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
    pdf_fetcher=fetch_bytes,
    pdf_extractor=extract_pdf_text,
) -> list[Offer]:
    """Parse only official DRE extract PDFs and keep still-open competitions."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()
    attempted = 0

    for anchor in soup.find_all("a", href=True):
        url = urljoin(base_url, anchor["href"])
        if not _official_extract_url(url) or url in seen:
            continue
        seen.add(url)
        attempted += 1
        if attempted > MAX_NOTICE_PDFS:
            log.warning("NOVA FCSH exceeded the %d extract-PDF limit", MAX_NOTICE_PDFS)
            break

        try:
            notice_text = pdf_extractor(pdf_fetcher(url))
        except Exception as exc:
            log.warning(
                "NOVA FCSH extract unavailable for %s (%s)",
                url, type(exc).__name__,
            )
            continue

        metadata = parse_notice_text(notice_text)
        deadline = metadata["deadline"]
        if not deadline:
            log.warning(
                "NOVA FCSH notice %s has no computable statutory deadline; skipping",
                url,
            )
            continue
        if deadline < today.isoformat():
            continue

        title = metadata["title"] or (
            f"Concurso de recrutamento de investigador "
            f"{metadata['notice_number'] or ''}"
        )
        notice_number = metadata["notice_number"]
        if notice_number and not re.search(re.escape(notice_number), title, re.I):
            title = f"{title} (Aviso n.º {notice_number})"

        days = metadata["deadline_days"]
        offers.append(Offer(
            source="nova-fcsh",
            kind="position",
            title=title,
            url=url,
            institution="Universidade NOVA de Lisboa – NOVA FCSH",
            region="Lisboa",
            position_type="Investigação",
            deadline=deadline,
            n_posts=int(metadata["vacancy_count"] or 1),
            notes=(
                f"Prazo calculado a partir da publicação de "
                f"{metadata['publication_date']} e do prazo legal de {days} dias úteis; "
                "confirma o calendário no aviso oficial."
            ),
            extra={
                "notice_number": notice_number,
                "publication_date": metadata["publication_date"],
                "deadline_basis": "DRE publication + statutory working days",
                "listing_url": base_url,
            },
        ))

    if not attempted and re.search(r"concursos\s+para\s+investigadores", soup.get_text(" ", strip=True), re.I):
        log.warning(
            "NOVA FCSH page has no linked official extract PDFs; no vacancy was inferred"
        )
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Collect NOVA FCSH researcher competitions with a future statutory deadline."""
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("NOVA FCSH: %d current researcher competitions", len(offers))
    return offers
