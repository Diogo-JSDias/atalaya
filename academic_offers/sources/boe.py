"""BOE (Boletín Oficial del Estado) open data: section II.B, university faculty posts and CSIC research posts.

API docs: https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from collections import Counter

from .. import llm
from ..http import fetch, fetch_bytes
from ..models import Offer
from ..spain import add_days, to_int, university

log = logging.getLogger(__name__)

SUMMARY_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{:%Y%m%d}"

# Titles we keep: calls for faculty posts / research posts.
KEEP = re.compile(
    r"convoca.*(cuerpos docentes|Profesor[ae]?s? (Permanente|Titular|Contratad)|Catedr[áa]tic|"
    r"personal docente e investigador|Cient[íi]fic[oa]s? Titulares|Investigador[ae]s? Cient|"
    r"Profesor[ae]s? de Investigaci)",
    re.I,
)
# Titles we drop even if they match: corrections, modifications, results.
DROP = re.compile(r"corrigen? errores|modifica|desiert|concluido|aspirantes|nombra|lista|comisi[óo]n", re.I)

CATEGORIES = [
    (re.compile(r"Catedr[áa]tic", re.I), "Catedrático/a de Universidad"),
    (re.compile(r"Titular(es)? de Universidad", re.I), "Profesor/a Titular de Universidad"),
    (re.compile(r"Permanente Laboral", re.I), "Profesor/a Permanente Laboral"),
    (re.compile(r"Ayudante Doctor", re.I), "Profesor/a Ayudante Doctor/a"),
    (re.compile(r"Cient[íi]fic[oa]s? Titular", re.I), "Científico/a Titular (CSIC)"),
    (re.compile(r"Investigador[ae]s? Cient[íi]fic", re.I), "Investigador/a Científico/a (CSIC)"),
    (re.compile(r"Profesor[ae]s? de Investigaci", re.I), "Profesor/a de Investigación (CSIC)"),
]

AREA_PATTERNS = [
    # "Área de conocimiento: «Física Aplicada»." / "Área/especialidad de conocimiento: Física Aplicada."
    re.compile(r"[ÁA]rea(?:/especialidad)? de [Cc]onocimiento:?\s*«?\s*([^.»]{3,120}?)\s*»?\s*[.;]"),
    # Granada-style table rows: "Profesor Titular de Universidad. Bioquímica y Biología Molecular."
    re.compile(r"(?:Profesor(?:a)? Titular de Universidad|Catedr[áa]tic[oa] de Universidad)\.\s+([A-ZÁÉÍÓÚ][^.]{3,120}?)\."),
]

DEADLINE = re.compile(
    r"plazo[^.]{0,160}?\b(\d+|un|una|dos|tres|cinco|diez|quince|veinte|veinticinco|treinta)\s+(días|meses)"
    r"(\s+(?:hábiles|naturales))?",
    re.I,
)


def _text(xml: str) -> str:
    body = xml.split("<texto>", 1)[-1]
    return " ".join(re.sub(r"<[^>]+>", " ", body).split())


def _category_before(text: str, pos: int, fallback: str, csic: bool) -> str:
    window = text[:pos]  # the latest category heading before this area applies
    best, best_pos = fallback, -1
    for pat, name in CATEGORIES:
        if ("CSIC" in name) != csic:
            continue
        for m in pat.finditer(window):
            if m.start() > best_pos:
                best, best_pos = name, m.start()
    return best


def _looks_like_area(area: str) -> bool:
    """Reject boilerplate captured by the area regex ("y Departamento, así como…", "actual: …")."""
    return (
        area[:1].isupper()
        and ":" not in area
        and not re.search(r"\d", area)  # post codes like "G032/D13262"
        and not re.search(r"Asistencial|destino|^Universi", area, re.I)  # "^Universi": committee members' affiliations  # healthcare-side half of "plazas vinculadas"
        and not re.search(r"\b(Departamento|convocatoria|anexo|plaza|Presidente|Presidenta|Secretari[oa]|Vocal|Suplente)\b", area, re.I)
        and len(area.split()) <= 12
    )


def _deadline(text: str, published: dt.date, region: str = "") -> str | None:
    m = DEADLINE.search(text)
    if not m:
        return None
    n = to_int(m.group(1))
    if not n:
        return None
    if m.group(2).lower() == "meses":
        return (published + dt.timedelta(days=30 * n)).isoformat()
    business = not (m.group(3) and "natural" in m.group(3).lower())  # Ley 39/2015: "días" = hábiles
    return add_days(published, n, business, region).isoformat()


def parse_notice(item: dict, published: dt.date, department: str) -> list[Offer]:
    title = item["titulo"]
    text = _text(fetch(item["url_xml"]))
    # The selection-committee annex repeats every area; only read the list of posts.
    posts_part = re.split(r"ANEXO I{1,2}\s*(?:Comisi|Composici|Tribunal)", text)[0]
    institution, region = university(title)
    if not institution and "Consejo Superior de Investigaciones" in title:
        institution, region = "CSIC", ""
    title_cat = next((name for pat, name in CATEGORIES if pat.search(title)), "")
    deadline = _deadline(text, published, region)
    url = item["url_html"]

    csic = institution == "CSIC"
    found: list[tuple[str, str]] = []
    for pat in AREA_PATTERNS:
        for m in pat.finditer(posts_part):
            area = m.group(1).strip(" «»")
            if _looks_like_area(area):
                found.append((area, _category_before(posts_part, m.end(), title_cat, csic)))
        if found:
            break

    common = dict(
        source="boe", kind="position", url=url, institution=institution, region=region,
        deadline=deadline, deadline_estimated=deadline is not None, published=published.isoformat(),
        extra={"boe_id": item["identificador"], "pdf": item["url_pdf"]["texto"], "boe_title": title},
    )
    if found:
        return [
            Offer(title=f"{cat or 'Plaza'} – {area}", position_type=cat, area_raw=area, n_posts=count, **common)
            for (area, cat), count in Counter(found).items()
        ]

    # The regexes found nothing: the posts are in a table layout we don't parse, or in a PDF annex
    # on the university's website. Ask the model (optional, cached), giving it any linked annexes.
    posts = llm.extract_posts(item["identificador"], title, text, _annex_pdfs(text))
    if posts:
        merged: Counter = Counter()
        for p in posts:
            area = p["area"].strip(" «».")
            if area:
                merged[(area, _normalise_category(p["category"]) or title_cat)] += max(int(p["n_posts"] or 1), 1)
        if merged:
            common["notes"] = "Extraído con IA del anexo: compruébalo en la convocatoria."
            return [
                Offer(title=f"{cat or 'Plaza'} – {area}", position_type=cat, area_raw=area, n_posts=n, **common)
                for (area, cat), n in merged.items()
            ]

    # Keep the notice as one entry pointing to the original.
    return [Offer(title=title, position_type=title_cat or "Plaza docente/investigadora",
                  notes="Áreas y número de plazas: ver convocatoria.", **common)]


ANNEX_LINK = re.compile(r"https?://[^\s«»\"<>]+?\.pdf", re.I)


def _annex_pdfs(text: str, limit: int = 2) -> list[bytes]:
    """PDF annexes the notice links to (e.g. 'Anexo II … https://www.ual.es/…/ANEXO_II.pdf')."""
    if not llm.enabled():
        return []
    pdfs = []
    for url in dict.fromkeys(ANNEX_LINK.findall(text)):
        if "boe.es" in url or len(pdfs) >= limit:
            continue
        try:
            pdfs.append(fetch_bytes(url))
        except Exception as e:  # dead link, robots.txt, timeout: the text alone may still be enough
            log.info("annex %s: %s", url, e)
    return pdfs


def _normalise_category(cat: str) -> str:
    return next((name for pat, name in CATEGORIES if pat.search(cat or "")), (cat or "").strip())


def _as_list(x):
    return x if isinstance(x, list) else ([x] if x else [])


def scrape(days: int = 21, today: dt.date | None = None) -> list[Offer]:
    today = today or dt.date.today()
    offers: list[Offer] = []
    for i in range(days):
        day = today - dt.timedelta(days=i)
        if day.weekday() == 6:  # no BOE on Sundays
            continue
        try:
            summary = json.loads(fetch(SUMMARY_URL.format(day), headers={"Accept": "application/json"}))
        except Exception as e:  # 404 on days without BOE
            log.info("BOE %s: %s", day, e)
            continue
        for diario in _as_list(summary["data"]["sumario"]["diario"]):
            for sec in _as_list(diario["seccion"]):
                if sec["codigo"] != "2B":
                    continue
                for dep in _as_list(sec.get("departamento")):
                    for ep in _as_list(dep.get("epigrafe")):
                        for item in _as_list(ep.get("item")):
                            t = item["titulo"]
                            relevant_dep = dep["nombre"] == "UNIVERSIDADES" or "Investigaciones Científicas" in t
                            if relevant_dep and KEEP.search(t) and not DROP.search(t):
                                try:
                                    offers.extend(parse_notice(item, day, dep["nombre"]))
                                except Exception:
                                    log.exception("BOE item %s", item.get("identificador"))
    return offers
