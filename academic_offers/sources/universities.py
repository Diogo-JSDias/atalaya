"""Universities' own pages for contracted faculty (Ayudante Doctor, Permanente Laboral, Asociado…).

These calls usually don't go through the BOE. Each university lists them differently, so every page
is one config entry: where the list is, which links are calls, and where the date comes from.
Adding a university = adding an entry to PAGES (and checking it once by hand).
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..dates import date_after, first_date
from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

MAX_AGE_DAYS = 30  # when only the publication date is known, hide calls older than this


@dataclass
class Page:
    key: str
    institution: str
    region: str
    url: str
    position_type: str
    link: str               # regex a link's text or href must match
    date_from: str          # "text": publication date in link text · "href": in URL · "detail": deadline on detail page
    title: str = ""         # fixed title prefix; default: the link text


UCM, UGR, UC3M = "Universidad Complutense de Madrid", "Universidad de Granada", "Universidad Carlos III de Madrid"
PAGES = [
    Page("ucm-ad", UCM, "Madrid", "https://www.ucm.es/profesor-ayudante-doctor", "Profesor/a Ayudante Doctor/a",
         r"Convocatoria publicada en el BOUC", "text", "Profesor/a Ayudante Doctor/a"),
    Page("ucm-ppl", UCM, "Madrid", "https://www.ucm.es/profesor-a-permanente-laboral", "Profesor/a Permanente Laboral",
         r"Convocatoria publicada en el BOUC", "text", "Profesor/a Permanente Laboral"),
    Page("ucm-asoc", UCM, "Madrid", "https://www.ucm.es/profesor-asociado", "Profesor/a Asociado/a",
         r"Convocatoria publicada en el BOUC", "text", "Profesor/a Asociado/a"),
    Page("ugr-ad", UGR, "Andalucía", "https://serviciopdi.ugr.es/contratado/concursopublico/ayudantedoctor/index.html",
         "Profesor/a Ayudante Doctor/a", r"\d{2}-\d{2}-20\d\d/index\.html", "href", "Profesor/a Ayudante Doctor/a"),
    Page("ugr-ppl", UGR, "Andalucía", "https://serviciopdi.ugr.es/contratado/concursopublico/permanentelaboral/index.html",
         "Profesor/a Permanente Laboral", r"\d{2}-\d{2}-20\d\d/index\.html", "href", "Profesor/a Permanente Laboral"),
    Page("ugr-asoc", UGR, "Andalucía", "https://serviciopdi.ugr.es/contratado/concursopublico/asociado/index.html",
         "Profesor/a Asociado/a", r"\d{2}-\d{2}-20\d\d/index\.html", "href", "Profesor/a Asociado/a"),
    Page("uc3m-pdi", UC3M, "Madrid", "https://www.uc3m.es/empleo/pdi", "",
         r"CONVOCATORIA .*20\d\d/", "detail"),
]

DEADLINE_WORDS = r"plazo de presentaci[óo]n[^.]{0,80}?(?:hasta|finaliza|:)|fecha l[íi]mite|fin del plazo|hasta el d[íi]a"


def _href_date(href: str) -> str | None:
    m = re.search(r"(\d{2})-(\d{2})-(20\d\d)", href)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def scrape_page(p: Page, today: dt.date) -> list[Offer]:
    soup = BeautifulSoup(fetch(p.url), "html.parser")
    for t in soup(["nav", "header", "footer", "script", "style"]):
        t.decompose()
    cutoff = (today - dt.timedelta(days=MAX_AGE_DAYS)).isoformat()
    year = str(today.year)
    offers, seen = [], set()
    for a in soup.find_all("a", href=True):
        text, href = a.get_text(" ", strip=True), a["href"]
        if not re.search(p.link, f"{text} {href}") or href in seen:
            continue
        seen.add(href)
        url = urljoin(p.url, href)
        published = deadline = None
        if p.date_from == "text":
            published = first_date(text)
        elif p.date_from == "href":
            published = _href_date(href)
        else:
            if year not in text and str(today.year + 1) not in text:
                continue  # don't fetch detail pages of calls from earlier years
            try:
                detail = " ".join(BeautifulSoup(fetch(url), "html.parser").get_text(" ").split())
            except Exception as e:
                log.info("%s detail %s: %s", p.key, url, e)
                continue
            deadline = date_after(detail, DEADLINE_WORDS)
            if not deadline:
                continue  # can't tell whether it's still open
        if published and published < cutoff:
            continue
        stage = p.position_type or ("Profesor/a Ayudante Doctor/a" if "Ayudante" in text else "")
        if p.title:
            when = dt.date.fromisoformat(published).strftime("%d/%m/%Y") if published else ""
            title = f"{p.title} – convocatoria del {when}" if when else p.title
        else:
            title = text
        offers.append(Offer(
            source=f"uni:{p.key}", kind="position", title=title, url=url, institution=p.institution,
            region=p.region, position_type=stage, published=published, deadline=deadline,
            notes="Varias áreas: ver convocatoria." if p.title else "",
        ))
    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers = []
    for p in PAGES:
        try:
            offers.extend(scrape_page(p, today))
        except Exception:
            log.exception("university page %s failed", p.key)
    return offers
