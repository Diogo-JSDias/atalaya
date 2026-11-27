"""Tests for UCP Faculty of Medicine recruitment filtering."""
import datetime as dt
import unittest

from academic_offers.dates import lisbon_working_day_deadline
from academic_offers.sources.ucp_medicina import parse_listing, parse_notice_text


LISTING = """
<html><body>
<h2>Concursos</h2>
<h3>A decorrer</h3>
<p>Concurso de Recrutamento de Professor Auxiliar na área de Pediatria, com Investigação em Erros Inatos do Sistema Imunológico</p>
<p><a href="/pt-pt/asset/14866/file">Edital/0123/2026</a></p>
<p>Concurso de Recrutamento de Professor Auxiliar na área de Ciência de Dados e Inteligência Artificial em Saúde</p>
<p><a href="/pt-pt/asset/14146/file">Edital/0116/2026</a></p>
<p>Concurso de Recrutamento de Professor Auxiliar na área de Investigação Clínica em Pneumologia do Sono</p>
<p><a href="/pt-pt/asset/13236/file">Edital/0079/2026</a></p>
<h3>Terminados</h3>
<p>Concurso de Recrutamento de Professor Catedrático em Cuidados Intensivos</p>
<p><a href="/pt-pt/asset/13241/file">Edital/0077/2026</a></p>
</body></html>
"""

NOTICES = {
    "https://fm.ucp.pt/pt-pt/asset/14866/file": """
        EDITAL/0123/2026
        A Doutora Isabel Maria de Oliveira Capeloa Gil, Reitora da UCP, faz saber
        que se encontra aberto, pelo prazo de 30 dias úteis, contados da data
        da publicação do presente aviso, concurso para provimento de uma vaga.
        Lisboa, 2 de novembro de 2026.
    """,
    "https://fm.ucp.pt/pt-pt/asset/14146/file": """
        EDITAL/0116/2026
        encontra-se aberto, pelo prazo de 30 dias úteis, contados da data da
        publicação do presente aviso, concurso para uma vaga.
        Lisboa, 7 de outubro de 2026.
    """,
    "https://fm.ucp.pt/pt-pt/asset/13236/file": """
        EDITAL/0079/2026
        encontra-se aberto, pelo prazo de 30 dias úteis, contados da data da
        publicação do presente aviso, concurso para uma vaga.
        Lisboa, 2 de junho de 2026.
    """,
    "https://fm.ucp.pt/pt-pt/asset/13241/file": """
        EDITAL/0077/2026
        encontra-se aberto, pelo prazo de 30 dias úteis, contados da data da
        publicação do presente aviso, concurso para uma vaga.
        Lisboa, 28 de maio de 2026.
    """,
}


class UCPMedicinaTests(unittest.TestCase):
    def test_extracts_signed_date_period_and_notice_number(self):
        details = parse_notice_text(NOTICES["https://fm.ucp.pt/pt-pt/asset/14866/file"])
        self.assertEqual(details["signed_date"], "2026-11-02")
        self.assertEqual(details["period_days"], 30)
        self.assertEqual(details["notice_number"], "0123/2026")
        self.assertEqual(
            details["minimum_deadline"],
            lisbon_working_day_deadline(dt.date(2026, 11, 2), 30).isoformat(),
        )

    def test_keeps_only_recent_current_notice_using_conservative_bound(self):
        calls = []
        def fetcher(url):
            calls.append(url)
            return url.encode("utf-8")
        def extractor(data):
            return NOTICES[data.decode("utf-8")]

        offers = parse_listing(
            LISTING,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=fetcher,
            pdf_extractor=extractor,
        )
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "ucp-medicina")
        self.assertIn("Pediatria", offer.title)
        self.assertEqual(offer.extra["notice_number"], "0123/2026")
        self.assertEqual(offer.extra["signed_date"], "2026-11-02")
        self.assertIsNone(offer.deadline)
        self.assertIn("data efetiva de publicação não consta", offer.notes)
        self.assertEqual(len(calls), 3)  # closed section is never fetched

    def test_does_not_treat_old_edital_as_open_even_when_page_labels_it_ongoing(self):
        old_html = """
        <h3>A decorrer</h3>
        <p>Old professor competition</p>
        <a href="/pt-pt/asset/13236/file">Edital/0079/2026</a>
        """
        offers = parse_listing(
            old_html,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"old",
            pdf_extractor=lambda _data: NOTICES["https://fm.ucp.pt/pt-pt/asset/13236/file"],
        )
        self.assertEqual(offers, [])

    def test_requires_official_pdf_link_and_current_section(self):
        html = """
        <h3>A decorrer</h3>
        <p>Professor Auxiliar</p>
        <a href="https://example.org/edital.pdf">Edital/0123/2026</a>
        <h3>Terminados</h3>
        <p>Other Assistant Professor</p>
        <a href="/pt-pt/asset/14866/file">Edital/0123/2026</a>
        """
        self.assertEqual(parse_listing(html), [])

    def test_no_assumed_deadline_without_publication_based_period(self):
        incomplete = """
        EDITAL/0123/2026
        Lisboa, 2 de novembro de 2026.
        """
        details = parse_notice_text(incomplete)
        self.assertIsNone(details["minimum_deadline"])
        self.assertIsNone(details["period_days"])


if __name__ == "__main__":
    unittest.main()
