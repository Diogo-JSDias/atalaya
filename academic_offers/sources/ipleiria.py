"""Universidade de Leiria e Oeste (ex-IPLeiria) research calls.

The former IPLeiria I&D+i calls page now identifies the institution as the
Universidade de Leiria e Oeste (ULO). The adapter retains the requested
ipleiria source key for compatibility but attributes offers to the current
institution name, preserving the direct application link from its official
recruitment portal.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..dates import first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

LIST_URL = "https://www.ipleiria.pt/investigar/bolsas-idi/concursos-abertos/"
APPLICATION_HOSTS = {"recrutamento.ipleiria.pt", "www.recrutamento.ipleiria.pt"}
PERIOD_RE = re.compile(r"Prazo\s+de\s+candidatura\s*:\s*([^.;]+)", re.I)
DATE_RE = re.compile(
    r"\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|marco|abril|maio|junho|julho|"
    r"agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?20\d{2}|"
    r"\d{1,2}[/.-]\d{1,2}[/.-]20\d{2}",
    re.I,
)
PROJECT_RE = re.compile(
    r"T[ií]tulo\s+do\s+projeto\s*:\s*(.*?)(?=\s*(?:Destinat[aá]rios|Dura[cç][ãa]o|"
    r"Prazo\s+de\s+candidatura|Link\s+Candidatura|$))",
    re.I,
)
COUNT_RE = re.compile(r"\b(\d{1,3})\s+Bolsa(?:s)?\s+de\s+Investiga[cç][ãa]o\b", re.I)
REF_RE = re.compile(r"\b(?:BI[.-][A-Z0-9.-]+|BI\d{3,})\b", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _last_date(value: str) -> str | None:
    matches = list(DATE_RE.finditer(value))
    if not matches:
        return first_date(value)
    return first_date(matches[-1].group(0))


def _is_application_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and host in APPLICATION_HOSTS
    )


def _card_for_link(anchor):
    """Find the smallest card with one deadline and one application link."""
    best = None
    for parent in anchor.parents:
        if parent.name in {"body", "html", "[document]", "main", "article"}:
            break
        text = _clean(parent.get_text(" ", strip=True))
        if text.count("Prazo de candidatura") > 1:
            break
        if len(text) > 4000:
            break
        if (
            "Prazo de candidatura" in text
            and "Bolsa de Investigação" in text
            and PROJECT_RE.search(text)
        ):
            best = parent
    return best


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse official I&D+i fellowship opportunities and filter expired deadlines."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()
    candidate_links = [
        anchor for anchor in soup.find_all("a", href=True)
        if _is_application_url(urljoin(base_url, anchor["href"]))
    ]

    for anchor in candidate_links:
        card = _card_for_link(anchor)
        if card is None:
            raise RuntimeError(
                "IPLeiria official application link found but its vacancy card or deadline was not recognized"
            )
        card_text = _clean(card.get_text(" ", strip=True))
        period = PERIOD_RE.search(card_text)
        if not period:
            raise RuntimeError("IPLeiria active research call has no application deadline")
        deadline_text = period.group(1).strip()
        deadline = _last_date(deadline_text)
        if not deadline:
            raise RuntimeError(
                f"IPLeiria application deadline is not parseable: {deadline_text}"
            )
        if deadline < today.isoformat():
            continue

        project_match = PROJECT_RE.search(card_text)
        project = _clean(project_match.group(1)).strip(" .;:") if project_match else ""
        count_match = COUNT_RE.search(card_text)
        n_posts = int(count_match.group(1)) if count_match else 1
        ref_match = REF_RE.search(card_text)
        reference = ref_match.group(0) if ref_match else ""
        heading = ""
        for element in card.find_all(["h2", "h3", "h4", "strong"]):
            candidate = _clean(element.get_text(" ", strip=True))
            if COUNT_RE.search(candidate):
                heading = candidate
                break
        if not heading:
            heading = f"{n_posts} Bolsa(s) de Investigação"
        title = heading
        if project:
            title += f" — {project}"
        if reference and reference not in title:
            title += f" ({reference})"

        url = urljoin(base_url, anchor["href"])
        if url in seen:
            continue
        seen.add(url)

        offers.append(Offer(
            source="ipleiria",
            kind="call",
            title=title,
            url=url,
            institution="Universidade de Leiria e Oeste (ex-IPLeiria)",
            region="Leiria",
            position_type="Bolsa de investigação",
            deadline=deadline,
            n_posts=n_posts,
            notes=f"Prazo de candidatura indicado no aviso/listagem: {deadline_text}.",
            extra={
                "application_reference": reference or None,
                "application_period": deadline_text,
                "listing_url": base_url,
            },
        ))

    # The portal's active-call list uses direct links on recrutamento.ipleiria.pt.
    # If it changes its host or markup, fail visibly instead of silently publishing
    # zero opportunities while the page still advertises open calls.
    if not candidate_links and re.search(r"Concursos\s+abertos", soup.get_text(" ", strip=True), re.I):
        raise RuntimeError(
            "IPLeiria page advertises open calls but no official application links were found"
        )
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("IPLeiria/ULO: %d current research fellowships", len(offers))
    return offers
