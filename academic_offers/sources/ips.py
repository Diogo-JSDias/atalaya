"""Universidade Politécnica de Setúbal (UNIPS; antigo IPS) recruitment.

The central "Candidaturas Abertas" page aggregates current application windows.
The separate "Procedimentos a decorrer" pages include competitions already
under evaluation, so they are intentionally not treated as open vacancies.
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

LIST_URL = "https://unips.pt/conhecer/organizacao/gestao-pessoas/recrutamento/candidaturas-abertas/"
TRUSTED_HOSTS = {
    "unips.pt", "www.unips.pt", "ips.pt", "www.ips.pt",
    "bep.gov.pt", "diariodarepublica.pt", "www.diariodarepublica.pt",
}
APPLICATION_RE = re.compile(r"Candidaturas\s*:\s*(?:Até|Ate)\s*(.+?)(?=Publicado\s+a|$)", re.I)
PUBLISHED_RE = re.compile(r"Publicado\s+a\s*(.+?)(?=\s|$)", re.I)
VACANCY_RE = re.compile(r"\b(\d{1,3})\s+Vaga(?:s)?\b", re.I)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _trusted(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return (
        parsed.scheme in {"http", "https"}
        and any(host == domain or host.endswith("." + domain) for domain in TRUSTED_HOSTS)
    )


def _card_for_deadline(node):
    """Find the smallest page card containing a vacancy title and one closing date."""
    best = None
    for parent in node.parents:
        if parent.name in {"body", "html", "[document]", "main", "article"}:
            break
        text = _clean(parent.get_text(" ", strip=True))
        if text.count("Candidaturas:") > 1:
            break
        if len(text) > 2500:
            break
        if "Candidaturas:" in text and VACANCY_RE.search(text):
            best = parent
    return best


def _role_category(text: str) -> tuple[str, str, str]:
    normal = text.casefold()
    if "bolseir" in normal or "bolsa de investigação" in normal:
        return "call", "Bolsa de investigação", "Bolsa"
    if "investigador" in normal:
        return "position", "Investigação", "Pessoal de investigação"
    if "docente" in normal or "professor" in normal:
        return "position", "Docência", "Pessoal docente"
    if "técnico" in normal or "tecnico" in normal or "gestão" in normal or "gestao" in normal:
        return "position", "Pessoal técnico, especialista e de gestão", "Pessoal técnico"
    return "position", "Recrutamento académico", "Pessoal técnico/especialista/gestão"


def parse_listing(
    html: str,
    *,
    base_url: str = LIST_URL,
    today: dt.date | None = None,
) -> list[Offer]:
    """Parse only the institution's current-application page."""
    today = today or dt.date.today()
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("main") or soup.find("article") or soup
    offers: list[Offer] = []
    seen: set[str] = set()
    deadline_nodes = [
        node for node in content.find_all(string=re.compile(r"Candidaturas\s*:\s*(?:Até|Ate)", re.I))
    ]

    for node in deadline_nodes:
        card = _card_for_deadline(node)
        if card is None:
            raise RuntimeError(
                "UNIPS open application date found without a bounded vacancy card"
            )
        card_text = _clean(card.get_text(" ", strip=True))
        deadline_match = APPLICATION_RE.search(card_text)
        if not deadline_match:
            raise RuntimeError("UNIPS application closing date not recognized")
        deadline_text = _clean(deadline_match.group(1)).strip(" .;")
        deadline = first_date(deadline_text)
        if not deadline:
            raise RuntimeError(
                f"UNIPS closing date is not parseable: {deadline_text}"
            )
        if deadline < today.isoformat():
            continue

        heading = ""
        for element in card.find_all(["h2", "h3", "h4", "strong"]):
            candidate = _clean(element.get_text(" ", strip=True))
            if VACANCY_RE.search(candidate):
                heading = candidate
                break
        if not heading:
            heading_match = VACANCY_RE.search(card_text)
            if heading_match:
                remainder = card_text[heading_match.start():]
                heading = _clean(remainder.split("Publicado a", 1)[0])
        if not heading:
            raise RuntimeError("UNIPS open vacancy title not found")

        count_match = VACANCY_RE.search(heading)
        n_posts = int(count_match.group(1)) if count_match else 1
        kind, position_type, category = _role_category(card_text)

        # Prefer the official opening notice (usually a PDF); otherwise retain
        # the official BEP detail record. Never use a generic application form.
        links = [urljoin(base_url, anchor["href"]) for anchor in card.find_all("a", href=True)]
        detail_url = next(
            (
                url for url in links
                if _trusted(url) and urlparse(url).path.lower().endswith(".pdf")
            ),
            None,
        )
        if not detail_url:
            detail_url = next(
                (
                    url for url in links
                    if _trusted(url) and "bep.gov.pt" in urlparse(url).netloc.lower()
                ),
                None,
            )
        if not detail_url:
            detail_url = next((url for url in links if _trusted(url)), base_url)
        if detail_url in seen:
            continue
        seen.add(detail_url)

        published_match = re.search(r"Publicado\\s+a\\s*(.*?)(?=\\s+Aviso|$)", card_text, re.I)
        published = first_date(published_match.group(1)) if published_match else None
        notes = f"Candidaturas até {deadline}."
        if published:
            notes += f" Publicado em {published}."
        offers.append(Offer(
            source="ips",
            kind=kind,
            title=heading,
            url=detail_url,
            institution="Universidade Politécnica de Setúbal (UNIPS; antigo IPS)",
            region="Setúbal",
            position_type=position_type,
            deadline=deadline,
            published=published,
            n_posts=n_posts,
            notes=notes,
            extra={
                "recruitment_category": category,
                "application_window": deadline_text,
                "listing_url": base_url,
            },
        ))

    # The source page is explicitly the "Candidaturas Abertas" register. If
    # the institution starts listing opportunities without a closing date,
    # surface a warning rather than quietly exposing a false open vacancy.
    if not deadline_nodes and re.search(r"Candidaturas\s+Abertas", content.get_text(" ", strip=True), re.I):
        # An empty open register is a valid state; the category pages separately
        # maintain process-stage archives that must not be interpreted as openings.
        log.info("UNIPS currently has no dated open application cards")
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_listing(fetch(LIST_URL), today=today)
    log.info("UNIPS/IPS: %d current recruitment opportunities", len(offers))
    return offers
