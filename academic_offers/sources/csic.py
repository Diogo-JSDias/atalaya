"""CSIC public calls (Sede electrónica → Convocatorias de personal o empleo público).

The listing shows each call's publication date and reference. Each call's page gives its type, number of
posts and application window: either "Cerrado" or a rule such as "10 días hábiles a partir del siguiente
al 22-10-2026", which we turn into a deadline.

CSIC's "Bolsa de trabajo" application itself needs an account, so it isn't used.
Internal civil-service postings (libre designación, concurso específico) are skipped.
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
from ..spain import add_days, to_int

log = logging.getLogger(__name__)

LIST = "https://sede.csic.gob.es/tramites/convocatorias-de-personal"
MAX_AGE_DAYS = 75   # only open detail pages of calls published recently
MAX_PAGES = 3
SKIP = re.compile(r"libre designaci[óo]n|concurso espec[íi]fico|provisi[óo]n de puestos|personal funcionario", re.I)
WINDOW = re.compile(r"(\d+|[a-zé]+)\s+d[íi]as\s+(h[áa]biles|naturales)\s+a partir del siguiente al\s+"
                    r"(\d{1,2})[-/](\d{1,2})[-/](20\d\d)", re.I)

STAGE_BY_SUBTYPE = {
    "contrato predoctoral": "PhD / predoc",
    "acceso de personal investigador doctor": "Postdoc",
    "doctor fc": "Postdoc",
    "investigador distinguido": "Senior faculty / research professor",
    "investigador en prácticas": "PhD / predoc",
}


def _field(text: str, label: str, nxt: str) -> str:
    m = re.search(rf"{label}\s*:?\s*(.*?)\s+(?:{nxt})", text)
    return m.group(1).strip() if m else ""


def _deadline(window: str) -> str | None:
    m = WINDOW.search(window)
    if m:
        n = to_int(m.group(1))
        start = dt.date(int(m.group(5)), int(m.group(4)), int(m.group(3)))
        if n:
            return add_days(start, n, m.group(2).lower().startswith("h"), "Madrid").isoformat()
    return first_date(window)


def parse_detail(url: str, title: str, published: str | None) -> Offer | None:
    soup = BeautifulSoup(fetch(url), "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    text = " ".join(soup.get_text(" ").split())
    window = _field(text, "Plazo de presentación", "Descripción|Dirigido a|Contacto|Solicitudes")
    if not window or window.lower().startswith("cerrad"):
        return None
    deadline = _deadline(window)
    subtype = _field(text, "Subtipo", "Fecha de publicación|Número de plazas")
    n_posts = _field(text, "Número de plazas", "Sistema de adjudicación|Plazo")
    status = _field(text, "Estado", "Tipo")
    offer = Offer(
        source="csic", kind="position", title=re.sub(r"\s*\(Ref\.\d+\)\s*$", "", title), url=url,
        institution="CSIC – Consejo Superior de Investigaciones Científicas", region="España (varios centros)",
        position_type=subtype or "Convocatoria CSIC", published=published, deadline=deadline,
        deadline_estimated=bool(WINDOW.search(window)),
        n_posts=int(n_posts) if n_posts.isdigit() else 1,
        notes=" · ".join(x for x in (f"Estado: {status}" if status else "", f"Plazo: {window}") if x),
        extra={"ref": url.rstrip("/").rsplit("/", 1)[-1]},
    )
    offer.stage = STAGE_BY_SUBTYPE.get(subtype.lower(), "")
    return offer


def scrape(today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    cutoff = (today - dt.timedelta(days=MAX_AGE_DAYS)).isoformat()
    offers = []
    for page in range(MAX_PAGES):
        soup = BeautifulSoup(fetch(LIST + (f"?page={page}" if page else "")), "html.parser")
        rows = soup.select("div.views-row")
        too_old = False
        for row in rows:
            a = row.select_one('a[href*="/convocatoria/"]')
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            published = first_date(row.get_text(" ", strip=True))
            if published and published < cutoff:
                too_old = True
                continue
            if SKIP.search(title):
                continue
            try:
                o = parse_detail(urljoin(LIST, a["href"]), title, published)
            except Exception:
                log.exception("CSIC call %s", a["href"])
                continue
            if o:
                offers.append(o)
        if too_old or not rows:
            break
    return offers
