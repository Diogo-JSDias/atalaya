"""Additional Portuguese university and research-employer recruitment feeds.

Each adapter is deliberately scoped to an official vacancy listing. The parser
fails closed on closed calls, preserves the detail URL, and never invents a
deadline. Dynamic/iframe-only boards are documented as gaps rather than scraped
through undocumented endpoints.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..dates import date_after, first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

GIMM_URL = "https://gimm.pt/jobs/?status=open"
INL_URL = "https://jobs.jobvite.com/inl/jobs"
ISCTE_URL = "https://recrutamento.iscte-iul.pt/jobs"
ISCTE_KNOWLEDGE_URL = "https://recrutamento.conhecimentoinovacao.iscte-iul.pt/jobs"
LIP_URL = "https://candidaturas.lip.pt/calls/current_calls"
UA_RESEARCH_URL = "https://www.ua.pt/pt/sgrh/pessoal-investigador-novos-concursos-e-ofertas"
UA_TEACHING_URL = "https://www.ua.pt/pt/sgrh/pessoal-docente-novos-concursos-e-ofertas"
UA_TAG_URL = "https://jobs.ua.pt/"
UCP_CLSBE_URL = "https://clsbe.lisboa.ucp.pt/pt-pt/investigacao/posicoes-investigacao"

CLOSED = re.compile(
    r"candidaturas? encerrad[ao]s?|call (?:is )?closed|this call is now closed|"
    r"recruitment process .*closed|prazo (?:terminou|encerrado)|estado\s*:?\s*fechado",
    re.I,
)
OPEN = re.compile(r"\b(open|aberto|aberta|a decorrer|accepting applications|current)\b", re.I)
ACADEMIC = re.compile(
    r"investigador|research|professor|docente|post.?doc|fellowship|bolsa|"
    r"scientist|phd|doutorad|assistant researcher|research assistant|"
    r"technician|técnic[oa]|engineer|engenheir",
    re.I,
)
DEADLINE = r"deadline|application ends|closes|prazo(?: de candidatura)?|candidaturas? até|até ao dia|até "

def _clean(value: str) -> str:
    return " ".join(value.split())


def _last_date(value: str) -> str | None:
    """Return the final date in a date-range cell (usually the closing date)."""
    patterns = (
        r"\d{1,2}[/.-]\d{1,2}[/.-]20\d{2}",
        r"\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?20\d{2}",
    )
    matches = []
    for pattern in patterns:
        matches.extend(re.finditer(pattern, value, re.I))
    if not matches:
        return first_date(value)
    match = max(matches, key=lambda item: item.start())
    return first_date(match.group(0))


def _card(node):
    card = node
    for _ in range(6):
        parent = card.parent
        if parent is None or parent.name in {"body", "html", "[document]", "main"}:
            break
        card = parent
        classes = " ".join(card.get("class", []))
        if card.name in {"article", "li", "tr"} or re.search(
            r"job|vacan|offer|opportun|career|call|card|views-row", classes, re.I
        ):
            break
    return card


def _allowed_host(url: str, domains: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return parsed.scheme in {"http", "https"} and any(
        host == domain or host.endswith("." + domain) for domain in domains
    )


def parse_link_board(
    html: str,
    *,
    base_url: str,
    source: str,
    institution: str,
    region: str,
    href_pattern: str,
    domains: tuple[str, ...],
    open_listing: bool = False,
    require_open_marker: bool = False,
) -> list[Offer]:
    """Parse linked vacancies from a known official board."""
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not re.search(href_pattern, href, re.I):
            continue
        title = _clean(anchor.get_text(" ", strip=True))
        if not title or title.casefold() in {"apply", "ver mais", "read more", "learn more"}:
            continue
        url = urljoin(base_url, href)
        if not _allowed_host(url, domains) or url in seen:
            continue
        card = _card(anchor)
        context = _clean(card.get_text(" ", strip=True))
        if CLOSED.search(context):
            continue
        if require_open_marker and not OPEN.search(context):
            continue
        if not ACADEMIC.search(title + " " + context):
            continue
        deadline = date_after(context, DEADLINE) or first_date(context)
        seen.add(url)
        kind = "call" if re.search(r"bolsa|fellowship|scholarship|grant", title, re.I) else "position"
        offers.append(Offer(
            source=source, kind=kind, title=title, url=url,
            institution=institution, region=region,
            position_type="Bolsa" if kind == "call" else "Recrutamento académico/científico",
            deadline=deadline,
            notes="Prazo não identificado na listagem; consultar o anúncio oficial." if not deadline else "",
            extra={"listing_url": base_url},
        ))
    return offers


def gimm(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_link_board(
        fetch(GIMM_URL), base_url=GIMM_URL, source="gimm",
        institution="GIMM – Gulbenkian Institute for Molecular Medicine",
        region="Lisboa", href_pattern=r"^/jobs/[^/?#]+/?$",
        domains=("gimm.pt",), open_listing=True,
    )
    return [o for o in offers if not o.deadline or o.deadline >= today.isoformat()]


def inl(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_link_board(
        fetch(INL_URL), base_url=INL_URL, source="inl",
        institution="INL – International Iberian Nanotechnology Laboratory",
        region="Braga", href_pattern=r"/inl/job/",
        domains=("jobvite.com",), open_listing=True,
    )
    return [o for o in offers if not o.deadline or o.deadline >= today.isoformat()]


def iscte(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = []
    boards = (
        (ISCTE_URL, "iscte", "Iscte – Instituto Universitário de Lisboa"),
        (ISCTE_KNOWLEDGE_URL, "iscte-ki", "Iscte Conhecimento e Inovação"),
    )
    for url, source, institution in boards:
        offers.extend(parse_link_board(
            fetch(url), base_url=url, source=source, institution=institution,
            region="Lisboa", href_pattern=r"/jobs/\d+",
            domains=("iscte-iul.pt",), open_listing=False,
        ))
    return [o for o in offers if not o.deadline or o.deadline >= today.isoformat()]


def lip(today: dt.date | None = None) -> list[Offer]:
    """The public 'current calls' route resolves to the currently featured open call."""
    today = today or dt.date.today()
    html = fetch(LIP_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = _clean(soup.get_text(" ", strip=True))
    heading = soup.find("h1")
    title = _clean(heading.get_text(" ", strip=True)) if heading else ""
    if not title or not re.search(
        r"open\s*[-–]\s*(?:applications?|candidaturas?)|candidaturas? abertas|accepting applications",
        text, re.I,
    ):
        return []
    if CLOSED.search(text):
        return []
    deadline = date_after(text, DEADLINE)
    if deadline and deadline < today.isoformat():
        return []
    return [Offer(
        source="lip", kind="position", title=title, url=LIP_URL,
        institution="LIP – Laboratório de Instrumentação e Física Experimental de Partículas",
        region="Portugal", position_type="Recrutamento científico",
        deadline=deadline,
        notes="Prazo não identificado na página pública; consultar o aviso oficial." if not deadline else "",
        extra={"listing_url": LIP_URL},
    )]


def _ua_board(url: str, source: str, today: dt.date) -> list[Offer]:
    offers = parse_link_board(
        fetch(url), base_url=url, source=source,
        institution="Universidade de Aveiro", region="Aveiro",
        href_pattern=r"(?:jobs\.ua\.pt/Home/Detail/\d+|api-portal\.ua\.pt/api/v1/file/\d+)",
        domains=("ua.pt",), open_listing=False,
    )
    return [o for o in offers if not o.deadline or o.deadline >= today.isoformat()]


def ua_research(today: dt.date | None = None) -> list[Offer]:
    return _ua_board(UA_RESEARCH_URL, "ua-investigacao", today or dt.date.today())


def ua_teaching(today: dt.date | None = None) -> list[Offer]:
    return _ua_board(UA_TEACHING_URL, "ua-docentes", today or dt.date.today())


def ua_technical(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = parse_link_board(
        fetch(UA_TAG_URL), base_url=UA_TAG_URL, source="ua-tecnico",
        institution="Universidade de Aveiro", region="Aveiro",
        href_pattern=r"/Home/Detail/\d+", domains=("ua.pt",),
    )
    return [o for o in offers if not o.deadline or o.deadline >= today.isoformat()]


def uc_portuguesa(today: dt.date | None = None) -> list[Offer]:
    """Católica-Lisbon research and faculty opportunities published in its table."""
    today = today or dt.date.today()
    soup = BeautifulSoup(fetch(UCP_CLSBE_URL), "html.parser")
    offers = []
    seen: set[str] = set()
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 3 or any(c.name == "th" for c in cells):
            continue
        row_text = _clean(row.get_text(" ", strip=True))
        if CLOSED.search(row_text) or re.search(r"fechado", row_text, re.I) or not OPEN.search(row_text):
            continue
        link = row.find("a", href=True)
        if not link:
            continue
        title = _clean(link.get_text(" ", strip=True))
        if not title or not ACADEMIC.search(title + " " + row_text):
            continue
        url = urljoin(UCP_CLSBE_URL, link["href"])
        if not _allowed_host(url, ("ucp.pt",)) or url in seen:
            continue
        deadline = _last_date(_clean(cells[-2].get_text(" ", strip=True)))
        if deadline and deadline < today.isoformat():
            continue
        seen.add(url)
        kind = "call" if re.search(r"bolsa|fellowship", title, re.I) else "position"
        offers.append(Offer(
            source="ucp-clsbe", kind=kind, title=title, url=url,
            institution="Universidade Católica Portuguesa – Católica-Lisbon",
            region="Lisboa", position_type="Bolsa" if kind == "call" else "Docência/Investigação",
            deadline=deadline,
            notes="Prazo não identificado na listagem; consultar o anúncio oficial." if not deadline else "",
            extra={"listing_url": UCP_CLSBE_URL},
        ))
    return offers
