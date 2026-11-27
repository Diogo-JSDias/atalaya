"""NOVA University Rectorate non-academic recruitment.

The official page groups active recruitment procedures under an explicit
'A Decorrer' heading and provides an application date range for each call.
Only entries in that section with a parseable closing date are emitted.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.unl.pt/quero-trabalhar-na-nova/reitoria/nao-docentes/"
REF_RE = re.compile(
    r"\b(?:CT\s*[-–]\s*\d{1,2}/20\d{2}(?:[-–][A-Z0-9-]+)?|"
    r"TS-[A-Z0-9-]+/20\d{2})\b",
    re.I,
)
DEADLINE_RE = re.compile(
    r"Prazo\s+(?:de\s+)?candidaturas?\s*:\s*(.+?)(?=(?:Prazo|$))",
    re.I,
)
MONTHS = (
    "janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|"
    "setembro|outubro|novembro|dezembro"
)
WRITTEN_DATE = re.compile(
    rf"(\d{{1,2}})\s+de\s+(?:{MONTHS})\s+(?:de\s+)?20\d{{2}}",
    re.I,
)
NUMERIC_DATE = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]20\d{2}")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _last_date(value: str) -> str | None:
    """Extract the closing date from the official application window."""
    matches = list(WRITTEN_DATE.finditer(value)) + list(NUMERIC_DATE.finditer(value))
    if not matches:
        return first_date(value)
    match = max(matches, key=lambda item: item.start())
    return first_date(match.group(0))


def _active_section(soup: BeautifulSoup):
    heading = next(
        (
            node for node in soup.find_all(["h1", "h2", "h3", "h4", "strong"])
            if re.search(
                r"Procedimentos\s+de\s+Recrutamento\s*[-–]\s*A\s+Decorrer",
                _clean(node.get_text(" ", strip=True)),
                re.I,
            )
        ),
        None,
    )
    if heading is None:
        raise RuntimeError(
            "NOVA Rectorate active recruitment heading not found; page structure changed"
        )
    return heading


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse only current Rectorate calls and filter expired closing dates."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    heading = _active_section(soup)

    # Work with text nodes after the active heading, never the older completed
    # or management-appointment sections lower down the page.
    strings = []
    for node in heading.find_all_next(string=True):
        value = _clean(str(node))
        if not value:
            continue
        if re.search(r"^(?:Dirigentes|Procedimentos de Recrutamento\s*[-–]\s*Concluídos)$", value, re.I):
            break
        strings.append((node, value))

    offers: list[Offer] = []
    seen: set[str] = set()
    for index, (node, value) in enumerate(strings):
        ref_match = REF_RE.search(value)
        if not ref_match:
            continue
        reference = ref_match.group(0).strip()
        if reference in seen:
            continue

        parent_text = _clean(node.parent.get_text(" ", strip=True)) if node.parent else value
        title = parent_text if len(parent_text) >= len(value) else value
        if not re.search(r"procedimento\s+de\s+recrutamento", title, re.I):
            # Some CMS layouts split the reference and the description across
            # sibling nodes. Find the nearest compact parent with the full call.
            for parent in node.parents:
                candidate = _clean(parent.get_text(" ", strip=True))
                if len(candidate) > 900:
                    break
                if REF_RE.search(candidate) and re.search(
                    r"procedimento\s+de\s+recrutamento", candidate, re.I
                ):
                    title = candidate
                    break

        nearby = [value]
        for _node, next_value in strings[index + 1:index + 12]:
            if REF_RE.search(next_value):
                break
            nearby.append(next_value)
        context = " ".join(nearby)
        deadline_match = DEADLINE_RE.search(context)
        if not deadline_match:
            # Search the neighbouring paragraphs directly, in case markup split
            # the label and its date range into separate text nodes.
            deadline_match = DEADLINE_RE.search(" ".join(nearby))
        if not deadline_match:
            raise RuntimeError(
                f"NOVA Rectorate active call {reference} has no parseable application window"
            )
        deadline_text = deadline_match.group(1).strip()
        deadline = _last_date(deadline_text)
        if not deadline:
            raise RuntimeError(
                f"NOVA Rectorate active call {reference} has an unrecognised closing date"
            )
        if deadline < today.isoformat():
            continue

        # Use the authoritative public page as the original source URL. The
        # application form is a generic page-level link, not a per-call notice.
        institution = (
            "NIMSB – NOVA Institute for Medical Systems Biology"
            if "NIMSB" in title or "NIMSB" in context
            else "Universidade NOVA de Lisboa – Reitoria"
        )
        role = (
            "Gestão de Projetos"
            if "TS-PMO" in reference
            else "Técnico Superior"
        )
        notes = f"Prazo oficial de candidatura: {deadline_text}."
        offers.append(Offer(
            source="nova-reitoria",
            kind="position",
            title=title,
            url=base_url,
            institution=institution,
            region="Lisboa",
            position_type=role,
            deadline=deadline,
            n_posts=1,
            notes=notes,
            extra={
                "recruitment_reference": reference,
                "application_window": deadline_text,
                "listing_url": base_url,
            },
        ))
        seen.add(reference)

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("NOVA Rectorate: %d current non-academic recruitment procedures", len(offers))
    return offers
