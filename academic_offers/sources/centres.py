"""Research centres' job boards: CNIC, ICFO, CRG, CNIO, IRB Barcelona.

Not covered: BSC (its site sits behind an anti-bot challenge, which we don't try to get past),
CSIC's own job board (rendered client-side; CSIC posts published in the BOE are still included).
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..dates import date_after
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

CNIC_LIST = "https://www.cnic.es/es/empleo/ofertas-empleo"
ICFO_LIST = "https://jobs.icfo.eu/"


def cnic() -> list[Offer]:
    soup = BeautifulSoup(fetch(CNIC_LIST), "html.parser")
    offers = []
    for tr in soup.select("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        a = tr.find("a", href=True)
        if len(cells) < 4 or not a:
            continue  # header row
        title, ref, end, status = cells[:4]
        if "presentación de solicitudes" not in status.lower():
            continue  # closed, or already in evaluation
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", end)
        offers.append(Offer(
            source="cnic", kind="position", title=title, url=urljoin(CNIC_LIST, a["href"]),
            institution="CNIC – Centro Nacional de Investigaciones Cardiovasculares", region="Madrid",
            deadline=f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None,
            notes=f"Ref. {ref} · {status}", area_raw="Cardiovascular research",
        ))
    return offers


def icfo() -> list[Offer]:
    soup = BeautifulSoup(fetch(ICFO_LIST), "html.parser")
    offers, seen = [], set()
    for li in soup.select("li.job"):
        a = li.find("a", href=True)
        if not a:
            continue
        url = urljoin(ICFO_LIST, a["href"])
        if url in seen:
            continue
        seen.add(url)
        text = li.get_text(" ", strip=True)
        group, _, title = text.partition(": ")
        if not title:  # general calls have no "Group: " prefix
            group, title = "", text
        offers.append(Offer(
            source="icfo", kind="position", title=title, url=url,
            institution="ICFO – The Institute of Photonic Sciences", region="Cataluña",
            area_raw=f"Photonics{(' – ' + group) if group else ''}",
        ))
    return offers


CRG_LIST = "https://www.crg.eu/en/content/careers/job-opportunities"
CNIO_LIST = "https://www.cnio.es/acerca-del-cnio/ofertas-de-empleo/"
IRB_LIST = "https://recruitment.irbbarcelona.org/"
DEADLINE_WORDS = r"deadline|fin de la oferta|plazo de presentaci[óo]n|fecha l[íi]mite|submit your application by"


def _detail(url: str) -> tuple[str, str]:
    """(full title, page text) of a job detail page."""
    soup = BeautifulSoup(fetch(url), "html.parser")
    h1 = soup.find("h1")
    for t in soup(["script", "style", "nav", "footer"]):
        t.decompose()
    return (h1.get_text(" ", strip=True) if h1 else ""), " ".join(soup.get_text(" ").split())


def _from_links(source: str, list_url: str, selector: str, institution: str, region: str,
                area: str) -> list[Offer]:
    soup = BeautifulSoup(fetch(list_url), "html.parser")
    offers, seen = [], set()
    for a in soup.select(selector):
        url = urljoin(list_url, a["href"])
        if url in seen or "/apply" in url or "general-application" in url:
            continue
        seen.add(url)
        try:
            title, text = _detail(url)
        except Exception as e:
            log.info("%s detail %s: %s", source, url, e)
            title, text = "", ""
        offers.append(Offer(
            source=source, kind="position", title=title or a.get_text(" ", strip=True), url=url,
            institution=institution, region=region, area_raw=area,
            deadline=date_after(text, DEADLINE_WORDS),
        ))
    return offers


def crg() -> list[Offer]:
    return _from_links("crg", CRG_LIST, 'a[href*="/content/jobs/position/"]',
                       "CRG – Centre for Genomic Regulation", "Cataluña", "Genomics & biomedicine")


def cnio() -> list[Offer]:
    return _from_links("cnio", CNIO_LIST, 'a[href*="cnio.es/empleo/"]',
                       "CNIO – Centro Nacional de Investigaciones Oncológicas", "Madrid", "Cancer research")


def irb() -> list[Offer]:
    return _from_links("irb", IRB_LIST, 'a[href*="recruitment.irbbarcelona.org/jobs/"]',
                       "IRB Barcelona – Institute for Research in Biomedicine", "Cataluña", "Biomedicine")


ALL = (cnic, icfo, crg, cnio, irb)


def scrape() -> list[Offer]:
    offers = []
    for fn in ALL:
        try:
            offers.extend(fn())
        except Exception:
            log.exception("centre source %s failed", fn.__name__)
    return offers
