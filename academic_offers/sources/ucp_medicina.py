"""Catholic University of Portugal – Faculty of Medicine recruitment.

The page labels a group of notices as ongoing, but can retain stale entries.
Each linked edital is inspected. Its signed date and statutory working-day
period provide a conservative lower bound for the deadline; the actual legal
deadline remains unset unless the publication date is available.
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

LIST_URL = "https://fm.ucp.pt/pt-pt/about-overview/apresentacao/despachos-e-concursos"
OFFICIAL_HOSTS = {"fm.ucp.pt"}
MAX_NOTICE_PDFS = 30

PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}
MONTH_PATTERN = "|".join(sorted(PT_MONTHS, key=len, reverse=True))
SIGNED_DATE = re.compile(
    rf"Lisboa,\s*(\d{{1,2}})\s+de\s+({MONTH_PATTERN})\s+de\s+(20\d{{2}})",
    re.I,
)
OPEN_PERIOD = re.compile(r"prazo\s+de\s+(\d{1,3})\s+dias?\s+[úu]teis", re.I)
NOTICE_NUMBER = re.compile(r"EDITAL\s*/\s*(\d{4})\s*/\s*(20\d{2})", re.I)
NOTICE_LINK = re.compile(r"Edital\s*/\s*\d{4}\s*/\s*20\d{2}", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and host in OFFICIAL_HOSTS
        and parsed.path.lower().endswith("/file")
        and bool(re.search(r"/asset/\d+/file$", parsed.path))
    )


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return _clean(" ".join(page.extract_text() or "" for page in reader.pages))


def parse_notice_text(text: str) -> dict[str, str | int | None]:
    clean = _clean(text)
    date_match = SIGNED_DATE.search(clean)
    period_match = OPEN_PERIOD.search(clean)
    number_match = NOTICE_NUMBER.search(clean)

    signed_date = None
    if date_match:
        try:
            signed_date = dt.date(
                int(date_match.group(3)),
                PT_MONTHS[date_match.group(2).casefold()],
                int(date_match.group(1)),
            )
        except (KeyError, ValueError):
            signed_date = None

    period_days = int(period_match.group(1)) if period_match else None
    minimum_deadline = None
    if signed_date and period_days:
        # The notice says the statutory period starts on publication. Publication
        # cannot precede the signed date, so this is a conservative lower bound.
        minimum_deadline = lisbon_working_day_deadline(signed_date, period_days)

    return {
        "signed_date": signed_date.isoformat() if signed_date else None,
        "period_days": period_days,
        "minimum_deadline": minimum_deadline.isoformat() if minimum_deadline else None,
        "notice_number": (
            f"{number_match.group(1)}/{number_match.group(2)}"
            if number_match else None
        ),
    }


def _is_ongoing(anchor) -> bool:
    marker = anchor.find_previous(string=re.compile(r"A decorrer|Terminados", re.I))
    return marker is not None and _clean(str(marker)).casefold() == "a decorrer"


def _title(anchor) -> str:
    title_pattern = re.compile(
        r"(?:Concurso\\s+de\\s+Recrutamento|Recruitment\\s+for\\s+the\\s+position)",
        re.I,
    )
    for previous in anchor.find_all_previous(string=True):
        value = _clean(str(previous)).strip(" •:-")
        if not value:
            continue
        if value.casefold() in {"a decorrer", "terminados"}:
            break
        if NOTICE_LINK.fullmatch(value):
            continue
        if title_pattern.search(value):
            return value

    parent = anchor.find_parent(["li", "p", "div"])
    if parent:
        value = _clean(parent.get_text(" ", strip=True))
        value = NOTICE_LINK.sub("", value).strip(" •:-")
        if value and title_pattern.search(value):
            return value
    return "Concurso docente – Faculdade de Medicina"


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
    pdf_fetcher=fetch_bytes,
    pdf_extractor=extract_pdf_text,
) -> list[Offer]:
    """Collect only current-section Medicine editais with a future lower-bound deadline."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()
    attempted = 0

    for anchor in soup.find_all("a", href=True):
        if not NOTICE_LINK.fullmatch(_clean(anchor.get_text(" ", strip=True))):
            continue
        if not _is_ongoing(anchor):
            continue

        url = urljoin(base_url, anchor["href"])
        if not _official_pdf_url(url) or url in seen:
            continue
        seen.add(url)
        attempted += 1
        if attempted > MAX_NOTICE_PDFS:
            log.warning("UCP Medicine exceeded the %d-PDF parsing limit", MAX_NOTICE_PDFS)
            break

        try:
            notice_text = pdf_extractor(pdf_fetcher(url))
        except Exception as exc:
            log.warning("UCP Medicine edital unavailable for %s (%s)", url, type(exc).__name__)
            continue

        metadata = parse_notice_text(notice_text)
        signed_date = metadata["signed_date"]
        minimum_deadline = metadata["minimum_deadline"]
        if not signed_date or not minimum_deadline:
            log.warning("UCP Medicine edital %s has no computable statutory period", url)
            continue
        if minimum_deadline < today.isoformat():
            # The faculty page has stale 'A decorrer' items. Suppress calls whose
            # term would already have expired even if counted from the signature.
            continue

        title = _title(anchor)
        notice_no = metadata["notice_number"]
        if notice_no and notice_no not in title:
            title = f"{title} (Edital {notice_no})"

        offers.append(Offer(
            source="ucp-medicina",
            kind="position",
            title=title,
            url=url,
            institution="Universidade Católica Portuguesa – Faculdade de Medicina",
            region="Lisboa",
            position_type="Professor Auxiliar",
            deadline=None,
            notes=(
                f"O edital estabelece {metadata['period_days']} dias úteis a contar da publicação. "
                f"Assinado em {signed_date}; o termo mínimo calculado desde a assinatura é "
                f"{minimum_deadline}. A data efetiva de publicação não consta do PDF consultado; "
                "confirmar o prazo no aviso oficial."
            ),
            extra={
                "notice_number": notice_no,
                "signed_date": signed_date,
                "minimum_possible_deadline": minimum_deadline,
                "deadline_basis": "publication date not established; signed-date lower bound only",
                "listing_url": base_url,
            },
        ))

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("UCP Faculty of Medicine: %d potentially current recruitment notices", len(offers))
    return offers
