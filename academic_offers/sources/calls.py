"""Funding calls: EU Funding & Tenders (MSCA, ERC), AEI (Ramón y Cajal, Juan de la Cierva, FPU…), ICREA, Ikerbasque."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..dates import date_after
from ..http import fetch, post_json
from ..models import Offer

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- EU Funding & Tenders
EU_SEARCH = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_TOPIC = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{}"
EU_QUERY = {"bool": {"must": [
    {"terms": {"type": ["1", "2", "8"]}},                  # calls for proposals / topics
    {"terms": {"status": ["31094501", "31094502"]}},      # forthcoming, open
]}}


def eu_calls(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers, seen = [], set()
    for text, programme in (("MSCA", "Marie Skłodowska-Curie Actions"), ("ERC", "European Research Council")):
        # The API wants the query as JSON file parts, not form fields.
        files = {
            "query": ("q.json", json.dumps(EU_QUERY), "application/json"),
            "languages": ("l.json", '["en"]', "application/json"),
        }
        data = post_json(
            EU_SEARCH,
            params={"apiKey": "SEDIA", "text": text, "pageSize": 100, "pageNumber": 1},
            files=files,
            timeout=60,
        )
        for r in data.get("results", []):
            m = r["metadata"]
            ident = (m.get("identifier") or [""])[0]
            if not ident or ident in seen or text not in ident:
                continue
            seen.add(ident)
            deadlines = sorted(d[:10] for d in m.get("deadlineDate") or [])
            if deadlines and deadlines[-1] < today.isoformat():
                continue  # the status field is sometimes stale; trust the date
            title = (m.get("title") or [r.get("title") or ident])[0]
            offers.append(Offer(
                source="eu-ft", kind="call", title=title, url=EU_TOPIC.format(ident),
                institution=programme, region="Europe", position_type="EU call",
                deadline=deadlines[-1] if deadlines else None,
                published=((m.get("startDate") or [""])[0][:10] or None),
                notes=ident, extra={"identifier": ident},
            ))
    return offers


# ---------------------------------------------------------------- AEI
AEI_LIST = "https://www.aei.gob.es/convocatorias/buscador-convocatorias"
AEI_DEADLINE_WORDS = r"(?:Plazos?\s+de\s+solicitud|Plazo)[^.]{0,120}?(?:hasta|fin(?:al)?)|Plazos?\s+de\s+solicitud|Plazo"


def aei_calls() -> list[Offer]:
    soup = BeautifulSoup(fetch(AEI_LIST), "html.parser")
    offers = []
    for field in soup.select("div.views-field-title"):
        li = field.find_parent("li")
        a = field.find("a", href=True)
        if not li or not a:
            continue
        parts = li.get_text(" | ", strip=True).split(" | ")
        status = parts[-1] if len(parts) > 1 else ""
        if status.lower().startswith("cerrad"):
            continue
        url = urljoin(AEI_LIST, a["href"])
        deadline = None
        try:
            text = " ".join(BeautifulSoup(fetch(url), "html.parser").get_text(" ").split())
            deadline = date_after(text, AEI_DEADLINE_WORDS, window=240)
        except Exception:
            log.exception("AEI detail %s", url)
        offers.append(Offer(
            source="aei", kind="call", title=a.get_text(" ", strip=True), url=url,
            institution="Agencia Estatal de Investigación", region="España",
            position_type="National call", deadline=deadline, notes=f"Estado: {status}",
        ))
    return offers


# ---------------------------------------------------------------- Ikerbasque
IKB_LIST = "https://www.ikerbasque.net/en/calls"
MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
_MONTH = "(" + "|".join(MONTHS) + ")"
EN_DATE_DMY = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+" + _MONTH + r",?\s+(20\d\d)", re.I)   # 10th September 2026
EN_DATE_MDY = re.compile(_MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)", re.I)          # November 30th 2026
CLOSED = re.compile(r"call is (?:now )?closed|applications were screened|were selected|"
                    r"final resolution|resolution has been published", re.I)


def _en_date(text: str) -> str | None:
    try:
        m = EN_DATE_DMY.search(text)
        if m:
            return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
        m = EN_DATE_MDY.search(text)
        if m:
            return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()
    except ValueError:
        return None
    return None


def ikerbasque_calls() -> list[Offer]:
    soup = BeautifulSoup(fetch(IKB_LIST), "html.parser")
    offers, seen = [], set()
    for a in soup.select("div.columns a[href^='/en/calls/']"):
        url = urljoin(IKB_LIST, a["href"])
        title = a.get_text(" ", strip=True)
        if url in seen or len(title) < 8 or title.lower() in {"evaluation", "results", "resolution"}:
            continue
        seen.add(url)
        page = " ".join(BeautifulSoup(fetch(url), "html.parser").get_text(" ").split())
        if CLOSED.search(page):
            continue
        dl = re.search(r"deadline(?: is)?:?\s*([^.]{0,40})", page, re.I)
        offers.append(Offer(
            source="ikerbasque", kind="call", title=title, url=url,
            institution="Ikerbasque", region="País Vasco", position_type="Regional call",
            deadline=_en_date(dl.group(1)) if dl else None,
        ))
    return offers


# ---------------------------------------------------------------- ICREA
ICREA_CALLS = "https://www.icrea.cat/en/calls"


def icrea_calls() -> list[Offer]:
    text = " ".join(BeautifulSoup(fetch(ICREA_CALLS), "html.parser").get_text(" ").split())
    closed = re.search(r"ICREA Call (20\d\d) IS CLOSED", text, re.I)
    nxt = re.search(r"The next ICREA call will open ([^.]+)\.", text)
    if closed and nxt:
        # Between calls: list the upcoming one, with ICREA's own wording about dates.
        year = int(closed.group(1)) + 1
        return [Offer(
            source="icrea", kind="call", title=f"ICREA Research Professors call {year} (upcoming)",
            url=ICREA_CALLS, institution="ICREA", region="Cataluña", position_type="Regional call",
            notes=f"Next call will open {nxt.group(1).strip()}.",
        )]
    if closed:
        return []
    years = re.findall(r"ICREA Call (?:Rules )?(20\d\d)", text)
    title = f"ICREA Research Professors call {max(years)}" if years else "ICREA Research Professors call"
    return [Offer(
        source="icrea", kind="call", title=title,
        url=ICREA_CALLS, institution="ICREA", region="Cataluña", position_type="Regional call",
        deadline=_en_date(text[text.lower().find("deadline"):][:80]) if "deadline" in text.lower() else None,
    )]


def scrape(today: dt.date | None = None) -> list[Offer]:
    offers = []
    for fn in (lambda: eu_calls(today), aei_calls, ikerbasque_calls, icrea_calls):
        try:
            offers.extend(fn())
        except Exception:
            log.exception("calls source failed")
    return offers
