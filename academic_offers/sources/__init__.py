"""Active sources for the Portuguese Atalaia edition.

The original Spanish adapters remain in the repository as reusable code, but
are not scheduled by this edition. Only Portuguese national sources and
European funding calls are active here.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

from ..models import Offer
from . import calls, dr, fct, uc_apply, ualg, ulisboa, uporto, uminho_eeg, novafct_investigadores, ubi_docentes, ubi_investigadores, nova_ims, nova_fcsh, portugal_targets


@dataclass
class Source:
    key: str
    name: str
    run: Callable[[dt.date, int], list[Offer]]
    may_be_empty: bool = False


SOURCES: list[Source] = [
    Source("dr", "Diário da República – 2.ª Série (RSS, avisos de recrutamento/investigação)",
           lambda today, _d: dr.scrape(today), may_be_empty=True),
    Source("fct", "FCT – concursos abertos (bolsas, emprego científico e projetos)",
           lambda today, _d: fct.scrape(today), may_be_empty=True),
    Source("ulisboa", "Universidade de Lisboa – recrutamento académico e científico",
           lambda today, _d: ulisboa.scrape(today), may_be_empty=True),
    Source("uporto", "Universidade do Porto – arquivo de oportunidades abertas",
           lambda today, _d: uporto.scrape(today), may_be_empty=True),
    Source("ualg", "Universidade do Algarve – procedimentos concursais (docentes e investigadores)",
           lambda today, _d: ualg.scrape(today), may_be_empty=True),
    Source("uc-apply", "Universidade de Coimbra – UC Apply (bolsas, docentes e investigadores)",
           lambda today, _d: uc_apply.scrape(today), may_be_empty=True),
    Source("uminho-eeg", "Universidade do Minho – Escola de Economia, Gestão e Ciência Política (docentes/investigadores)",
           lambda today, _d: uminho_eeg.scrape(today), may_be_empty=True),
    Source("novafct-investigadores", "NOVA FCT – concursos de investigadores (apenas pessoal investigador)",
           lambda today, _d: novafct_investigadores.scrape(today), may_be_empty=True),
    Source("ubi-docentes", "Universidade da Beira Interior – concursos para docentes",
           lambda today, _d: ubi_docentes.scrape(today), may_be_empty=True),
    Source("ubi-investigadores", "Universidade da Beira Interior – concursos para investigadores",
           lambda today, _d: ubi_investigadores.scrape(today), may_be_empty=True),
    Source("nova-ims", "NOVA IMS – recrutamento académico e bolsas de investigação",
           lambda today, _d: nova_ims.scrape(today), may_be_empty=True),
    Source("nova-fcsh", "NOVA FCSH – concursos para investigadores",
           lambda today, _d: nova_fcsh.scrape(today), may_be_empty=True),
    Source("gimm", "GIMM – Gulbenkian Institute for Molecular Medicine (recrutamento)", lambda today, _d: portugal_targets.gimm(today), may_be_empty=True),
    Source("inl", "INL – International Iberian Nanotechnology Laboratory (recrutamento)", lambda today, _d: portugal_targets.inl(today), may_be_empty=True),
    Source("iscte", "Iscte – concursos docentes, técnicos, investigação e bolsas", lambda today, _d: portugal_targets.iscte(today), may_be_empty=True),
    Source("lip", "LIP – Laboratório de Instrumentação e Física Experimental de Partículas", lambda today, _d: portugal_targets.lip(today), may_be_empty=True),
    Source("ua-investigacao", "Universidade de Aveiro – concursos de pessoal investigador", lambda today, _d: portugal_targets.ua_research(today), may_be_empty=True),
    Source("ua-docentes", "Universidade de Aveiro – concursos de pessoal docente", lambda today, _d: portugal_targets.ua_teaching(today), may_be_empty=True),
    Source("ua-tecnico", "Universidade de Aveiro – portal JobsUA (pessoal técnico, administrativo e de gestão)", lambda today, _d: portugal_targets.ua_technical(today), may_be_empty=True),
    Source("ucp-clsbe", "Universidade Católica Portuguesa – Católica-Lisbon (docência/investigação/bolsas)", lambda today, _d: portugal_targets.uc_portuguesa(today), may_be_empty=True),
    Source("eu-ft", "EU Funding & Tenders – concursos ERC e MSCA",
           lambda today, _d: calls.eu_calls(today), may_be_empty=True),
]
