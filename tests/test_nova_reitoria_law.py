"""Tests for NOVA Rectorate and NOVA School of Law recruitment."""
import datetime as dt
import unittest

from academic_offers.sources.nova_reitoria import parse_listing as parse_reitoria
from academic_offers.sources.nova_law import (
    parse_listing as parse_law,
    parse_notice_text,
)


REITORIA_HTML = """
<html><body>
<h2>Não docentes</h2>
<h3>Procedimentos de Recrutamento – A Decorrer</h3>
<p>Formulário de candidatura a Procedimentos de Recrutamento</p>
<p>CT – 27/2026-URR-DRH-DRHGD – Procedimento de recrutamento de um(a) técnico(a) superior – Grau 3, em regime de contrato de trabalho sem termo, para exercer funções na Unidade de Remunerações e Reportes (URR) da Reitoria da Universidade NOVA de Lisboa.</p>
<p>Prazo de candidaturas: 27 de novembro a 15 de dezembro de 2026</p>
<p>TS-PMO/2026 – GESTÃO DE PROJETOS – Procedimento de recrutamento de um/a técnico/a superior, em regime de contrato de trabalho a termo resolutivo incerto, para o exercício de funções na área de Gestão de Projetos (PMO) no Nova Institute for Medical Systems Biology (NIMSB).</p>
<p>Prazo de candidaturas: 23 de novembro a 07 de dezembro de 2026</p>
<h3>Dirigentes</h3>
<p>RUNL-DIR-08/2026 – Procedimento de recrutamento interno para contratação de um dirigente.</p>
<p>Prazo de candidaturas: 21 a 29 de outubro de 2026</p>
<h3>Procedimentos de Recrutamento – Concluídos</h3>
<p>CT-23/2026 – DAJ – Procedimento de recrutamento de um técnico superior.</p>
<p>Prazo de candidaturas: 13 a 27 de outubro de 2026</p>
</body></html>
"""

LAW_HTML = """
<html><body>
<h1>Abertura de Procedimento de Recrutamento</h1>
<h3>Prazo de candidatura: 14 de dezembro de 2026</h3>
<h3>Procedimento de recrutamento para Assistente de Investigação</h3>
<p>Procedimento de recrutamento com vista à contratação de um/a Assistente de Investigação,
na área de Direito Privado (Direito da Família e das Crianças).</p>
<a href="/wp-content/uploads/2026/11/Edital-JUST-Listen.pdf">Edital (referência nº 1477/2026)</a>
<a href="https://novalaw.unl.pt/wp-content/uploads/2025/09/Formulario-Docentes-PT.pdf">Formulário de candidatura</a>
</body></html>
"""

LAW_NOTICE = """
Edital n.º 1477/2026
19-11-2026
N.º 225
2.ª série
UNIVERSIDADE NOVA DE LISBOA
Faculdade de Direito
Sumário: Abertura de concurso documental internacional para recrutamento de um/a assistente de investigação.
Abertura de concurso documental internacional para recrutamento de um/a Assistente de Investigação na área de Direito Privado (Direito da Família e das Crianças),
está aberto pelo prazo de 15 dias úteis, a contar do dia imediato da publicação do Aviso,
concurso documental internacional.
XI — Apresentação de candidaturas:
As candidaturas devem ser apresentadas até ao 15.º dia útil, contado a partir do dia seguinte
ao da publicação do Aviso (extrato) no Diário da República.
"""


class NOVAReitoriaTests(unittest.TestCase):
    def test_extracts_only_current_section_and_closing_dates(self):
        offers = parse_reitoria(REITORIA_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 2)
        by_ref = {o.extra["recruitment_reference"]: o for o in offers}
        self.assertEqual(
            by_ref["CT – 27/2026-URR-DRH-DRHGD"].deadline,
            "2026-12-15",
        )
        self.assertEqual(by_ref["CT – 27/2026-URR-DRH-DRHGD"].institution,
                         "Universidade NOVA de Lisboa – Reitoria")
        self.assertEqual(by_ref["TS-PMO/2026"].deadline, "2026-12-07")
        self.assertEqual(by_ref["TS-PMO/2026"].institution,
                         "NIMSB – NOVA Institute for Medical Systems Biology")
        self.assertTrue(all(o.url == "https://www.unl.pt/quero-trabalhar-na-nova/reitoria/nao-docentes/" for o in offers))

    def test_filters_expired_open_section_calls(self):
        html = REITORIA_HTML.replace(
            "27 de novembro a 15 de dezembro de 2026",
            "27 de setembro a 15 de outubro de 2026",
        ).replace(
            "23 de novembro a 07 de dezembro de 2026",
            "23 de setembro a 07 de outubro de 2026",
        )
        self.assertEqual(parse_reitoria(html, today=dt.date(2026, 11, 27)), [])

    def test_fails_closed_when_current_section_heading_disappears(self):
        with self.assertRaises(RuntimeError):
            parse_reitoria("<h2>Não docentes</h2><p>CT-27/2026 offer</p>")


class NOVALawTests(unittest.TestCase):
    def test_extracts_dre_publication_and_working_day_deadline(self):
        details = parse_notice_text(LAW_NOTICE)
        self.assertEqual(details["publication_date"], "2026-11-19")
        self.assertEqual(details["period_days"], 15)
        self.assertEqual(details["deadline"], "2026-12-14")
        self.assertEqual(details["notice_number"], "1477/2026")

    def test_keeps_current_research_assistant_call_and_official_pdf(self):
        offers = parse_law(
            LAW_HTML,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"official-notice",
            pdf_extractor=lambda _data: LAW_NOTICE,
        )
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "nova-law")
        self.assertEqual(offer.deadline, "2026-12-14")
        self.assertIn("Assistente de Investigação", offer.title)
        self.assertEqual(offer.extra["notice_number"], "1477/2026")
        self.assertEqual(
            offer.url,
            "https://novalaw.unl.pt/wp-content/uploads/2026/11/Edital-JUST-Listen.pdf",
        )

    def test_rejects_mismatch_between_page_and_pdf_deadline(self):
        wrong = LAW_HTML.replace("14 de dezembro de 2026", "13 de dezembro de 2026")
        with self.assertRaises(RuntimeError):
            parse_law(
                wrong,
                today=dt.date(2026, 11, 27),
                pdf_fetcher=lambda _url: b"official-notice",
                pdf_extractor=lambda _data: LAW_NOTICE,
            )

    def test_filters_expired_offer(self):
        old = LAW_HTML.replace("14 de dezembro de 2026", "14 de outubro de 2026")
        notice = LAW_NOTICE.replace("19-11-2026", "19-09-2026")
        offers = parse_law(
            old,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"official-notice",
            pdf_extractor=lambda _data: notice,
        )
        # The listing and PDF date differ, so the parser refuses to create a record.
        self.assertEqual(offers, [])

    def test_rejects_external_pdf_links(self):
        html = LAW_HTML.replace(
            "/wp-content/uploads/2026/11/Edital-JUST-Listen.pdf",
            "https://evil.example/edital.pdf",
        )
        self.assertEqual(parse_law(html, today=dt.date(2026, 11, 27)), [])


if __name__ == "__main__":
    unittest.main()
