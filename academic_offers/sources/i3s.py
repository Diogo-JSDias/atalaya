"""Official i3S job-opportunities feed.

The public listing contains one PDF link per vacancy, but its visible "Apply"
buttons all point to the same generic application-management page. We retain
the vacancy-specific official PDF as the offer URL instead.
"""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ..dates import first_date
from ..http import fetch
from ..models import Offer

LIST_URL = "https://www.i3s.up.pt/job-opportunities"
DETAIL_HOST = "dozer.i3s.up.pt"
DETAIL_PATH = "/fileupload/downloadfile/viewpdfnewtab/"

REFERENCE_RE = re.compile(
    r"\bReference\s*:\s*([A-Za-z0-9][A-Za-z0-9._/-]*)", re.I
)
DEADLINE_LABEL_RE = re.compile(
    r"(?:Submission\s+Deadline|Application\s+Deadline|Deadline|"
    r"Prazo\s+(?:de\s+)?candidatura|Candidaturas\s+até)\s*:?\s*", re.I
)
CLOSED_RE = re.compile(
    r"\b(?:call\s+closed|closed|candidaturas\s+encerradas?|"
    r"recruitment\s+process\s+closed)\b", re.I
)
SHORT_DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{2})\b")
FULL_DATE_RE = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}\b")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _detail_url(href: str) -> str | None:
    url = urljoin(LIST_URL, href)
    parsed = urlparse(url)
    if (
        parsed.scheme == "https"
        and parsed.netloc.lower() == DETAIL_HOST
        and parsed.path.startswith(DETAIL_PATH)
    ):
        return url
    return None


def _card_for_anchor(anchor: Tag) -> Tag | None:
    """Find the smallest ancestor containing one reference and its deadline."""
    for parent in anchor.parents:
        if not isinstance(parent, Tag) or parent.name in {"body", "html"}:
            break
        text = _clean(parent.get_text(" ", strip=True))
        references = REFERENCE_RE.findall(text)
        if len(references) == 1 and DEADLINE_LABEL_RE.search(text):
            return parent
        # Once an ancestor contains multiple offers, higher ancestors cannot
        # restore the per-offer boundary.
        if len(references) > 1:
            break
    return None


def _date_after_label(text: str, label: re.Pattern[str]) -> str | None:
    match = label.search(text)
    if not match:
        return None
    fragment = text[match.end():match.end() + 120]
    short = SHORT_DATE_RE.search(fragment)
    if short:
        year, month, day = (int(value) for value in short.groups())
        try:
            return dt.date(2000 + year, month, day).isoformat()
        except ValueError:
            return None
    full = FULL_DATE_RE.search(fragment)
    if full:
        return first_date(full.group(0))
    return first_date(fragment)


def _title(card: Tag) -> str:
    lines = [_clean(line) for line in card.get_text("\n", strip=True).splitlines()]
    lines = [line for line in lines if line]
    ignored = re.compile(
        r"^(?:open positions|job description(?:\s*\[.*\])?|edital(?:\s*\[.*\])?|"
        r"apply|area\s*:|salary range\s*:|reference\s*:|institution\s*:|"
        r"project\s*:|submission open\s*:|submission deadline\s*:|"
        r"application deadline\s*:)", re.I,
    )
    candidates = [line for line in lines if not ignored.search(line)]
    if not candidates:
        return ""

    first = candidates[0]
    if first.casefold() == "bolsa de investigação" and len(candidates) > 1:
        return f"Bolsa de Investigação – {candidates[1]}"
    return first


def _preferred_pdf(card: Tag, fallback: Tag) -> str:
    candidates: list[tuple[int, str]] = []
    for anchor in card.find_all("a", href=True):
        url = _detail_url(anchor.get("href", ""))
        if not url:
            continue
        label = _clean(anchor.get_text(" ", strip=True)).casefold()
        if "job description" in label and "en" in label:
            rank = 0
        elif "edital" in label or "job description" in label:
            rank = 1
        else:
            rank = 2
        candidates.append((rank, url))
    if candidates:
        return sorted(candidates)[0][1]
    return _detail_url(fallback.get("href", "")) or LIST_URL


def parse(html: str, today: dt.date | None = None) -> list[Offer]:
    """Parse current i3S vacancies and discard calls whose deadline has passed."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    page_text = _clean(soup.get_text(" ", strip=True))
    pdf_anchors = [
        anchor for anchor in soup.find_all("a", href=True)
        if _detail_url(anchor.get("href", ""))
    ]

    if not pdf_anchors:
        # A truly empty Open Positions section is valid. If offer metadata is
        # still present, however, the source markup changed and should alert us.
        if REFERENCE_RE.search(page_text) and DEADLINE_LABEL_RE.search(page_text):
            raise RuntimeError("i3S listing contains vacancy metadata but no official PDF links")
        return []

    offers: list[Offer] = []
    seen: set[str] = set()
    for anchor in pdf_anchors:
        card = _card_for_anchor(anchor)
        if card is None:
            raise RuntimeError("Could not isolate an i3S vacancy card from its official PDF link")

        context = _clean(card.get_text(" ", strip=True))
        reference_match = REFERENCE_RE.search(context)
        if not reference_match:
            raise RuntimeError("i3S vacancy card is missing its reference")

        reference = reference_match.group(1)
        if reference in seen:
            continue
        seen.add(reference)

        if CLOSED_RE.search(context):
            continue

        deadline = _date_after_label(context, DEADLINE_LABEL_RE)
        if not deadline:
            raise RuntimeError(f"Could not parse the application deadline for i3S vacancy {reference}")
        if deadline < today.isoformat():
            continue

        title = _title(card)
        if not title:
            raise RuntimeError(f"Could not parse the title for i3S vacancy {reference}")

        kind = "call" if re.search(
            r"\b(?:bolsa|fellow|fellowship|scholarship|grant)\b", title, re.I
        ) else "position"
        area_match = re.search(
            r"\bArea\s*:\s*(.+?)(?=\s+(?:Salary\s+Range|Reference|Institution|Project)\s*:|$)",
            context, re.I,
        )
        salary_match = re.search(r"\bSalary\s+Range\s*:\s*(.+?)(?=\s+Reference\s*:|$)", context, re.I)
        open_date = _date_after_label(
            context, re.compile(r"Submission\s+Open\s*:?\s*", re.I)
        )

        offers.append(Offer(
            source="i3s",
            kind=kind,
            title=title,
            url=_preferred_pdf(card, anchor),
            institution="i3S – Instituto de Investigação e Inovação em Saúde da Universidade do Porto",
            region="Porto",
            position_type="Bolsa de Investigação" if kind == "call" else title,
            area_raw=_clean(area_match.group(1)) if area_match else "",
            deadline=deadline,
            extra={
                "reference": reference,
                "submission_open": open_date,
                "salary_range": _clean(salary_match.group(1)) if salary_match else "",
                "listing_url": LIST_URL,
            },
        ))

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch and parse the official i3S open-positions page."""
    return parse(fetch(LIST_URL), today=today)
