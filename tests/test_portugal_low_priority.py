"""Regression tests for LASIGE, IPLeiria and UNIPS recruitment adapters."""
import datetime as dt
import unittest

from academic_offers.sources.lasige import parse_application_period, parse_listing as parse_lasige
from academic_offers.sources.ipleiria import parse_listing as parse_ipleiria
from academic_offers.sources.ips import parse_listing as parse_ips


LASIGE_HTML = """
<html><body><main>
<article><div class="position-card">
<p>LASIGE, ref. UID/00408/2025 – LASIGE, has an open call for 1 BI fellowship</p>
<p>Type: BI (1090,98€/month)</p>
<p>Admission Requirements: BSc completed.</p>
<p>Duration: 3 months, potentially renewed for 3 months.</p>
<p>Application period: November 2-16, 2026</p>
<p>Announcement link: <a href="https://www.euraxess.pt/jobs/476266">EURAXESS</a></p>
</div></article>
<article><div class="position-card">
<p>GoalballXR project, reference No. 912, has an open call for 2 BI fellowship</p>
<p>Type: BI (1359,64€/month)</p>
<p>Admission Requirements: Master’s degree in Computer Sciences.</p>
<p>Duration: 3 months.</p>
<p>Application period: November 28 to December 5, 2026</p>
<p>Announcement link: <a href="https://euraxess.pt/jobs/477777">EURAXESS</a></p>
</div></article>
<article><div class="position-card">
<p>CEREBRA-AI project has an open call for 1 BI fellowship</p>
<p>Type: BI (1090,98€/month)</p>
<p>Admission Requirements: Bachelor’s degree.</p>
<p>Duration: 3 months.</p>
<p>Application period: October 21-29, 2026</p>
</div></article>
</main></body></html>
"""

IPLEIRIA_HTML = """
<html><body><main>
<article><div class="call-card">
<h3>1 Bolsa de Investigação (BI-202299)</h3>
<p>Título do projeto: Scale UP – Scaling up Pulmonary Rehabilitation uptake and adherence</p>
<p>Destinatários: Alunos Mestres em Design inscritos em doutoramento.</p>
<p>Duração: 12 meses.</p>
<p>Prazo de candidatura: 27 de novembro de 2026 a 15 de dezembro de 2026.</p>
<p>Link Candidatura: <a href="https://recrutamento.ipleiria.pt/offer/BI-202299">Candidatura</a></p>
</div></article>
<article><div class="call-card">
<h3>1 Bolsa de Investigação (BI-203001)</h3>
<p>Título do projeto: BioFREE – Revestimento antimicrobiano à base de MgO</p>
<p>Destinatários: Mestres em Engenharia Biomédica.</p>
<p>Duração: 6 meses.</p>
<p>Prazo de candidatura: 26 de novembro de 2026 a 11 de dezembro de 2026.</p>
<p>Link Candidatura: <a href="https://recrutamento.ipleiria.pt/offer/BI-203001">Candidatura</a></p>
</div></article>
<article><div class="call-card">
<h3>1 Bolsa de Investigação (BI-OLD)</h3>
<p>Título do projeto: Bolsa antiga.</p>
<p>Destinatários: Estudantes inscritos.</p>
<p>Prazo de candidatura: 01 de novembro de 2026 a 24 de novembro de 2026.</p>
<p><a href="https://recrutamento.ipleiria.pt/offer/BI-OLD">Candidatura</a></p>
</div></article>
</main></body></html>
"""

IPS_HTML = """
<html><body><main>
<h1>Candidaturas Abertas</h1>
<section><div class="vacancy-card">
<p>Pessoal técnico, especialista e de gestão | Procedimento Concursal</p>
<h3>1 Vaga | Assistente Operacional</h3>
<p>Área de limpeza e manutenção de instalações</p>
<p>Aviso Abertura Integral <a href="https://unips.pt/wp-content/uploads/2026/11/Aviso-29177-2026.pdf">Aviso</a></p>
<p>Aviso n. 29177/2026/2</p>
<p>OE202611/0977 – Detalhe publicação BEP</p>
<p>Candidaturas: Até 10 de dezembro de 2026</p>
<p>Publicado a 24 de novembro de 2026</p>
</div></section>
<section><div class="vacancy-card">
<p>Pessoal técnico, especialista e de gestão | Mobilidade Interna</p>
<h3>1 Vaga | Técnico/a Superior</h3>
<p>Área Financeira e de Aprovisionamento</p>
<p><a href="https://www.bep.gov.pt/pages/oferta/Oferta_Detalhes.aspx?CodOferta=12345">Detalhe BEP</a></p>
<p>OE202611/0372</p>
<p>Candidaturas: Até 30 de novembro de 2026</p>
<p>Publicado a 9 de novembro de 2026</p>
</div></section>
<section><div class="vacancy-card">
<p>Pessoal técnico, especialista e de gestão | Mobilidade Interna</p>
<h3>1 Vaga | Técnico de Sistemas e Tecnologias de Informação</h3>
<p>Candidaturas: Até 9 de novembro de 2026</p>
<p>Publicado a 26 de outubro de 2026</p>
</div></section>
</main></body></html>
"""


class LASIGETests(unittest.TestCase):
    def test_application_period_parser_supports_same_and_cross_month_ranges(self):
        self.assertEqual(
            parse_application_period("Application period: November 2-16, 2026"),
            ("2026-11-02", "2026-11-16"),
        )
        self.assertEqual(
            parse_application_period("Application period: November 28 to December 5, 2026"),
            ("2026-11-28", "2026-12-05"),
        )

    def test_filters_expired_archived_calls_and_keeps_future_call(self):
        offers = parse_lasige(LASIGE_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "lasige")
        self.assertEqual(offer.deadline, "2026-12-05")
        self.assertEqual(offer.extra["application_start"], "2026-11-28")
        self.assertEqual(offer.institution, "LASIGE – Faculdade de Ciências, Universidade de Lisboa")
        self.assertEqual(offer.url, "https://euraxess.pt/jobs/477777")

    def test_fails_closed_when_application_period_is_not_parseable(self):
        html = """
        <article><div><p>LASIGE has an open call for one researcher</p>
        <p>Admission Requirements: PhD.</p><p>Application period: To be announced</p></div></article>
        """
        with self.assertRaises(RuntimeError):
            parse_lasige(html, today=dt.date(2026, 11, 27))

    def test_rejects_untrusted_announcement_links_and_uses_official_listing(self):
        html = """
        <article><div><p>LASIGE has an open call for 1 BI fellowship</p>
        <p>Type: BI</p><p>Admission Requirements: BSc.</p><p>Duration: 3 months.</p>
        <p>Application period: November 28 to December 5, 2026</p>
        <a href="https://evil.example/call">Notice</a></div></article>
        """
        offer = parse_lasige(html, today=dt.date(2026, 11, 27))[0]
        self.assertEqual(offer.url, "https://lasige.pt/positions/")


class IPLeiriaTests(unittest.TestCase):
    def test_keeps_future_research_scholarships_and_direct_application_links(self):
        offers = parse_ipleiria(IPLEIRIA_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 2)
        first = offers[0]
        self.assertEqual(first.source, "ipleiria")
        self.assertIn("Scale UP", first.title)
        self.assertEqual(first.deadline, "2026-12-15")
        self.assertEqual(first.extra["application_reference"], "BI-202299")
        self.assertEqual(first.url, "https://recrutamento.ipleiria.pt/offer/BI-202299")
        self.assertEqual(first.institution, "Universidade de Leiria e Oeste (ex-IPLeiria)")

    def test_filters_expired_calls(self):
        expired = """
        <article><div class="call-card">
        <h3>1 Bolsa de Investigação (BI-OLD)</h3>
        <p>Título do projeto: Bolsa antiga.</p><p>Destinatários: Estudantes.</p>
        <p>Prazo de candidatura: 01 de novembro de 2026 a 24 de novembro de 2026.</p>
        <a href="https://recrutamento.ipleiria.pt/offer/BI-OLD">Candidatura</a>
        </div></article>
        """
        self.assertEqual(parse_ipleiria(expired, today=dt.date(2026, 11, 27)), [])

    def test_rejects_external_application_links(self):
        html = """
        <h2>Concursos abertos</h2><a href="https://evil.example/offer">Research fellowship</a>
        """
        with self.assertRaises(RuntimeError):
            parse_ipleiria(html, today=dt.date(2026, 11, 27))

    def test_fails_closed_on_missing_deadline_in_application_card(self):
        html = """
        <article><div class="call-card">
        <h3>1 Bolsa de Investigação (BI-X)</h3>
        <p>Título do projeto: Projeto X.</p>
        <a href="https://recrutamento.ipleiria.pt/offer/BI-X">Candidatura</a>
        </div></article>
        """
        with self.assertRaises(RuntimeError):
            parse_ipleiria(html, today=dt.date(2026, 11, 27))


class IPSTests(unittest.TestCase):
    def test_extracts_only_current_applications_from_central_register(self):
        offers = parse_ips(IPS_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 2)
        first = offers[0]
        self.assertEqual(first.source, "ips")
        self.assertIn("Assistente Operacional", first.title)
        self.assertEqual(first.deadline, "2026-12-10")
        self.assertEqual(first.published, "2026-11-24")
        self.assertEqual(first.url, "https://unips.pt/wp-content/uploads/2026/11/Aviso-29177-2026.pdf")
        self.assertEqual(first.institution, "Universidade Politécnica de Setúbal (UNIPS; antigo IPS)")
        self.assertIn("Técnico/a Superior", offers[1].title)
        self.assertEqual(offers[1].deadline, "2026-11-30")
        self.assertIn("bep.gov.pt", offers[1].url)

    def test_filters_expired_application_windows(self):
        old = """
        <h1>Candidaturas Abertas</h1><div class="vacancy-card">
        <h3>1 Vaga | Técnico Superior</h3>
        <p>Candidaturas: Até 9 de novembro de 2026</p>
        <p>Publicado a 26 de outubro de 2026</p></div>
        """
        self.assertEqual(parse_ips(old, today=dt.date(2026, 11, 27)), [])

    def test_empty_open_register_is_valid(self):
        self.assertEqual(
            parse_ips("<h1>Candidaturas Abertas</h1><p>Não existem candidaturas.</p>"),
            [],
        )

    def test_rejects_external_notice_links_and_falls_back_to_listing_page(self):
        html = """
        <h1>Candidaturas Abertas</h1><div class="vacancy-card">
        <h3>1 Vaga | Técnico Superior</h3>
        <p>Candidaturas: Até 10 de dezembro de 2026</p>
        <p>Publicado a 24 de novembro de 2026</p>
        <a href="https://evil.example/notices/1.pdf">Aviso</a></div>
        """
        offer = parse_ips(html, today=dt.date(2026, 11, 27))[0]
        self.assertEqual(offer.url, "https://unips.pt/conhecer/organizacao/gestao-pessoas/recrutamento/candidaturas-abertas/")

    def test_fails_closed_when_a_current_vacancy_has_unparseable_deadline(self):
        html = """
        <h1>Candidaturas Abertas</h1><div class="vacancy-card">
        <h3>1 Vaga | Técnico Superior</h3><p>Candidaturas: Até data a anunciar</p>
        </div>
        """
        with self.assertRaises(RuntimeError):
            parse_ips(html, today=dt.date(2026, 11, 27))


if __name__ == "__main__":
    unittest.main()
