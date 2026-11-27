"""Registry of every source. Each entry is scraped on its own, so one broken site never stops the rest,
and its item count is reported on the About page and checked for sudden drops to zero."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

from ..models import Offer
from . import boe, calls, centres, csic, dr, fct, ulisboa, universities


@dataclass
class Source:
    key: str
    name: str
    run: Callable[[dt.date, int], list[Offer]]   # (today, boe_days) -> offers
    may_be_empty: bool = False                     # e.g. a funder between calls


def _uni(page: universities.Page) -> Source:
    return Source(f"uni:{page.key}", f"{page.institution} – {page.position_type or 'convocatorias PDI'} (web)",
                  lambda today, _d, p=page: universities.scrape_page(p, today), may_be_empty=True)


SOURCES: list[Source] = [
    Source("dr", "Diário da República – 2.ª Série (RSS, avisos de recrutamento/investigação)",
           lambda today, _d: dr.scrape(today), may_be_empty=True),
    Source("fct", "FCT – concursos abertos (bolsas, emprego científico e projetos)",
           lambda today, _d: fct.scrape(today), may_be_empty=True),
    Source("ulisboa", "Universidade de Lisboa – recrutamento académico e científico",
           lambda today, _d: ulisboa.scrape(today), may_be_empty=True),
    Source("boe", "BOE – Boletín Oficial del Estado, sección II.B (universidades, CSIC)",
           lambda today, days: boe.scrape(days=days, today=today)),
    Source("eu-ft", "EU Funding & Tenders portal (MSCA, ERC)", lambda today, _d: calls.eu_calls(today)),
    Source("aei", "Agencia Estatal de Investigación (Ramón y Cajal, Juan de la Cierva, FPU…)",
           lambda _t, _d: calls.aei_calls(), may_be_empty=True),
    Source("ikerbasque", "Ikerbasque", lambda _t, _d: calls.ikerbasque_calls(), may_be_empty=True),
    Source("icrea", "ICREA", lambda _t, _d: calls.icrea_calls(), may_be_empty=True),
    Source("csic", "CSIC – Sede electrónica, convocatorias de personal",
           lambda today, _d: csic.scrape(today), may_be_empty=True),
    Source("cnic", "CNIC job board", lambda _t, _d: centres.cnic()),
    Source("icfo", "ICFO job board", lambda _t, _d: centres.icfo()),
    Source("crg", "CRG job board", lambda _t, _d: centres.crg()),
    Source("cnio", "CNIO job board", lambda _t, _d: centres.cnio()),
    Source("irb", "IRB Barcelona job board", lambda _t, _d: centres.irb()),
    *[_uni(p) for p in universities.PAGES],
]
