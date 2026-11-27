"""NOVA School of Law recruitment opportunities.

This source pairs the faculty's official recruitment page with its DRE notice.
The statutory working-day term is calculated from the DRE publication date,
and the result is cross-checked against the closing date on the faculty page.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..dates import first_date, lisbon_working_day_deadline
from ..http import fetch, fetch_bytes
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://novalaw.unl.pt/abertura-de-procedimentos-de-recrutamento-2/"
OFFICIAL_HOST = "novalaw.unl.pt"

PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}
MONTH_PATTERN = "|".join(sorted(PT_MONTHS, key=len, reverse=True))
DATE_DMY = re.compile(r"(?<!\d)(\d{2})[-/.](\d{2})[-/.](20\d{2})(?!\d)")
OPEN_PERIOD = re.compile(
    r"prazo\s+de\s+(\d{1,3})\s+dias?\s+[úu]teis\s*,?\s*"
    r"a\s+contar\s+do\s+dia\s+imediato\s+da\s+publica[cç][ãa]o\s+do\s+aviso",
    re.I,
)
NOTICE_NUMBER = re.compile(r"Edital\s+n\.?\s*[º°o]?\s*(\d{1,6}/20\d{2})", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _official_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and (host == OFFICIAL_HOST or host.endswith("." + OFFICIAL_HOST))
        and parsed.path.lower().endswith(".pdf")
    )


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return _clean(" ".join(page.extract_text() or "" for page in reader.pages))


def parse_notice_text(text: str) -> dict[str, str | int | None]:
    clean = _clean(text)
    date_match = DATE_DMY.search(clean)
    period_match = OPEN_PERIOD.search(clean)
    number_match = NOTICE_NUMBER.search(clean)

    publication_date = None
    if date_match:
        try:
            day, month, year = (int(value) for value in date_match.groups())
            publication_date = dt.date(year, month, day)
        except ValueError:
            publication_date = None

    period_days = int(period_match.group(1)) if period_match else None
    deadline = None
    if publication_date and period_days:
        first_counted_day = publication_date + dt.timedelta(days=1)
        deadline = lisbon_working_day_deadline(first_counted_day, period_days)

    title_match = re.search(
        r"recrutamento\s+de\s+um/a\s+(.+?)(?=,\s*na\s+[áa]rea|\s+na\s+[áa]rea)",
        clean,
        re.I,
    )
    title = _clean(title_match.group(1)) if title_match else ""
    return {
        "publication_date": publication_date.isoformat() if publication_date else None,
        "period_days": period_days,
        "deadline": deadline.isoformat() if deadline else None,
        "notice_number": number_match.group(1) if number_match else None,
        "title": title,
    }


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
    pdf_fetcher=fetch_bytes,
    pdf_extractor=extract_pdf_text,
) -> list[Offer]:
    """Parse official NOVA Law recruitment notice and verify its closing date."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    pdf_links = [
        anchor for anchor in soup.find_all("a", href=True)
        if _official_pdf_url(urljoin(base_url, anchor["href"]))
        and "edital" in anchor["href"].casefold()
    ]
    if not pdf_links:
        raise RuntimeError("NOVA School of Law recruitment notice PDF not found")

    offers: list[Offer] = []
    seen: set[str] = set()
    for anchor in pdf_links:
        pdf_url = urljoin(base_url, anchor["href"])
        if pdf_url in seen:
            continue
        seen.add(pdf_url)

        title_heading = next(
            (
                heading for heading in soup.find_all(["h2", "h3", "h4"])
                if re.search(
                    r"Procedimento\s+de\s+recrutamento\s+para",
                    _clean(heading.get_text(" ", strip=True)),
                    re.I,
                )
            ),
            None,
        )
        if title_heading is None:
            raise RuntimeError("NOVA School of Law recruitment title not found")
        page_title = _clean(title_heading.get_text(" ", strip=True))
        page_text = _clean(soup.get_text(" ", strip=True))
        page_date_match = re.search(
            rf"Prazo\s+de\s+candidatura\s*:\s*(\d{{1,2}}\s+de\s+(?:{MONTH_PATTERN})\s+de\s+20\d{{2}})",
            page_text,
            re.I,
        )
        if not page_date_match:
            raise RuntimeError("NOVA School of Law application deadline missing from listing")
        page_deadline = first_date(page_date_match.group(1))
        if not page_deadline:
            raise RuntimeError("NOVA School of Law application deadline is not parseable")

        try:
            notice_text = pdf_extractor(pdf_fetcher(pdf_url))
        except Exception as exc:
            raise RuntimeError(
                f"NOVA School of Law official edital unavailable ({type(exc).__name__})"
            ) from exc
        metadata = parse_notice_text(notice_text)
        if not metadata["deadline"]:
            raise RuntimeError("NOVA School of Law edital has no computable statutory deadline")
        if metadata["deadline"] != page_deadline:
            raise RuntimeError(
                "NOVA School of Law page deadline and statutory edital deadline disagree: "
                f"{page_deadline} != {metadata['deadline']}"
            )
        if metadata["deadline"] < today.isoformat():
            continue

        notice_number = metadata["notice_number"]
        title = page_title
        if notice_number and notice_number not in title:
            title = f"{title} (Edital {notice_number})"
        offers.append(Offer(
            source="nova-law",
            kind="position",
            title=title,
            url=pdf_url,
            institution="Universidade NOVA de Lisboa – NOVA School of Law",
            region="Lisboa",
            position_type="Assistente de Investigação",
            deadline=metadata["deadline"],
            n_posts=1,
            notes=(
                f"Prazo calculado a partir da publicação no Diário da República "
                f"({metadata['publication_date']}) e dos {metadata['period_days']} dias úteis "
                "previstos no edital; coincide com o prazo publicado pela faculdade."
            ),
            extra={
                "notice_number": notice_number,
                "publication_date": metadata["publication_date"],
                "deadline_basis": "DRE publication + statutory working days",
                "listing_url": base_url,
            },
        ))

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("NOVA School of Law: %d current recruitment calls", len(offers))
    return offers
