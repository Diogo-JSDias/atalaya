"""Diário da República (Portugal): second-series official RSS index.

The feed URL is published by the Diário da República RSS subscription page.
Only public RSS items are consumed. We keep the original act URL and do not
attempt to access private APIs or bypass access controls.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import logging
import re
import xml.etree.ElementTree as ET

from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

# Official "2.ª Série — Todas as partes — HTML" RSS link.
RSS_URL = "https://files.diariodarepublica.pt/rss/serie2-html.xml"

# Deliberately broad at first: titles vary between institutions and notice types.
RECRUITMENT = re.compile(
    r"concurso|procedimento concursal|recrutamento|contrata[cç][ãa]o|"
    r"abertura de procedimento|bolsa(?:s)? de investiga[cç][ãa]o|"
    r"investigador(?:a|es|as)?|pessoal docente|docente|professor(?:a|es|as)?|"
    r"carreira de investiga[cç][ãa]o|emprego cient[ií]fico|"
    r"est[uú]mulo [àa] investiga[cç][ãa]o",
    re.I,
)
# Drop outcomes and procedural follow-ups that are not new opportunities.
NOT_NEW = re.compile(
    r"lista (?:unit[aá]ria|de ordena[cç][ãa]o)|homologa[cç][ãa]o|"
    r"projeto de lista|lista provis[oó]ria|lista definitiva|"
    r"resultados?|candidato(?:s|as)? admitido|exclus[aã]o|"
    r"anula[cç][ãa]o|retifica[cç][ãa]o|cessa[cç][ãa]o",
    re.I,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(item: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in item.iter():
        if _local_name(child.tag) in wanted and child.text:
            return " ".join(child.text.split())
    return ""


def _published(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def parse_feed(xml_text: str, today: dt.date | None = None) -> list[Offer]:
    """Parse RSS/Atom items, keeping likely new academic/research recruitment notices."""
    today = today or dt.date.today()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        log.exception("Invalid Diário da República RSS XML")
        return []

    offers: list[Offer] = []
    seen: set[str] = set()
    for item in root.iter():
        if _local_name(item.tag) not in {"item", "entry"}:
            continue
        title = _child_text(item, "title")
        if not title or not RECRUITMENT.search(title) or NOT_NEW.search(title):
            continue

        url = _child_text(item, "link", "guid", "id")
        # Atom uses href attribute on link instead of element text.
        if not url:
            for child in item.iter():
                if _local_name(child.tag) == "link" and child.attrib.get("href"):
                    url = child.attrib["href"]
                    break
        if not url.startswith(("https://", "http://")) or url in seen:
            continue
        seen.add(url)

        description = _child_text(item, "description", "summary", "content", "encoded")
        published = _published(_child_text(item, "pubdate", "published", "updated", "date"))
        offers.append(Offer(
            source="dr", kind="position", title=title, url=url,
            institution="", region="Portugal",
            position_type="Aviso de recrutamento / investigação",
            published=published,
            notes="Aviso identificado automaticamente no RSS da 2.ª Série. "
                  "Confirma requisitos, entidade, prazo e natureza do vínculo no anúncio original.",
            extra={"rss_description": description[:1500]} if description else {},
        ))
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch the official second-series RSS index and parse relevant notices."""
    xml_text = fetch(RSS_URL)
    offers = parse_feed(xml_text, today)
    log.info("Diário da República RSS: %d possible recruitment notices", len(offers))
    return offers
