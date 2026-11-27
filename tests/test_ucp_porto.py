"""Tests for UCP Porto Regional Centre recruitment filtering."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.dates import lisbon_working_day_deadline
from academic_offers.sources.ucp_porto import (
    LIST_URL,
    parse_listing,
    parse_notice_text,
    scrape,
)


LISTING = """
<html><body>
<h2>Concursos</h2>
<h3>A decorrer</h3>
<p>Concurso de Recrutamento de Professor Auxiliar na área de Biotecnologia</p>
<p><a href="/pt-pt/asset/20001/file">Edital/0123/2026</a></p>
<p>Concurso de Recrutamento de Professor Auxiliar na área de Direito</p>
<p><a href="/pt-pt/asset/20002/file">Edital/0079/2026</a></p>
<p>Concurso de Recrutamento de Investigador sem prazo</p>
<p><a href="/pt-pt/asset/20003/file">Edital/0080/2026</a></p>
<h3>Terminados</h3>
<p>Concurso de Recrutamento de Professor Associado em Gestão</p>
<p><a href="/pt-pt/asset/20004/file">Edital/0077/2026</a></p>
</body></html>
"""

NOTICES = {
    "https://www.porto.ucp.pt/pt-pt/asset/20001/file": """
        EDITAL/0123/2026
        Encontra-se aberto, pelo prazo de 30 dias úteis, contados da data
        da publicação do presente aviso, concurso para provimento de uma vaga.
        Porto, 2 de novembro de 2026.
    """,
    "https://www.porto.ucp.pt/pt-pt/asset/20002/file": """
        EDITAL/0079/2026
        Encontra-se aberto, pelo prazo de 30 dias úteis, contados da data da
        publicação do presente aviso, concurso para uma vaga.
        Porto, 2 de junho de 2026.
    """,
    "https://www.porto.ucp.pt/pt-pt/asset/20003/file": """
        EDITAL/0080/2026
        Porto, 2 de novembro de 2026.
    """,
    "https://www.porto.ucp.pt/pt-pt/asset/20004/file": """
        EDITAL/0077/2026
        Encontra-se aberto, pelo prazo de 30 dias úteis, contados da data da
        publicação do presente aviso, concurso para uma vaga.
        Porto, 28 de maio de 2026.
    """,
}


class UCPPortoTests(unittest.TestCase):
    def test_extracts_signed_date_period_and_notice_number(self):
        details = parse_notice_text(
            NOTICES["https://www.porto.ucp.pt/pt-pt/asset/20001/file"]
        )
        self.assertEqual(details["signed_date"], "2026-11-02")
        self.assertEqual(details["period_days"], 30)
        self.assertEqual(details["notice_number"], "0123/2026")
        self.assertEqual(
            details["minimum_deadline"],
            lisbon_working_day_deadline(dt.date(2026, 11, 2), 30).isoformat(),
        )

    def test_keeps_only_valid_open_offers_and_skips_closed_or_invalid(self):
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
        self.assertEqual(offer.source, "ucp-porto")
        self.assertEqual(offer.region, "Porto")
        self.assertIn("Biotecnologia", offer.title)
        self.assertIn("Edital 0123/2026", offer.title)
        self.assertEqual(offer.url, "https://www.porto.ucp.pt/pt-pt/asset/20001/file")
        self.assertEqual(offer.extra["notice_number"], "0123/2026")
        self.assertEqual(offer.extra["signed_date"], "2026-11-02")
        self.assertIsNone(offer.deadline)
        self.assertIn("data efetiva de publicação não consta", offer.notes)
        self.assertEqual(len(calls), 3)  # closed section is never fetched

    def test_requires_official_pdf_link_and_ongoing_section(self):
        html = """
        <h3>A decorrer</h3>
        <p>Professor Auxiliar</p>
        <a href="https://example.org/pt-pt/asset/20001/file">Edital/0123/2026</a>
        <h3>Terminados</h3>
        <p>Professor Auxiliar</p>
        <a href="/pt-pt/asset/20001/file">Edital/0123/2026</a>
        """
        offers = parse_listing(
            html,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"pdf",
            pdf_extractor=lambda _data: NOTICES[
                "https://www.porto.ucp.pt/pt-pt/asset/20001/file"
            ],
        )
        self.assertEqual(offers, [])

    def test_handles_empty_or_unexpected_html_and_pdf_errors_gracefully(self):
        self.assertEqual(parse_listing("", today=dt.date(2026, 11, 27)), [])
        self.assertEqual(
            parse_listing("<div><p>Sem concursos</p></div>", today=dt.date(2026, 11, 27)),
            [],
        )

        broken_html = """
        <h3>A decorrer</h3>
        <p>Professor Auxiliar</p>
        <a href="/pt-pt/asset/20001/file">Edital/0123/2026</a>
        """
        offers = parse_listing(
            broken_html,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: (_ for _ in ()).throw(RuntimeError("network error")),
        )
        self.assertEqual(offers, [])

    def test_scrape_uses_fetch_and_fetch_bytes_mocks(self):
        with patch("academic_offers.sources.ucp_porto.fetch", return_value=LISTING) as mock_fetch, \
             patch("academic_offers.sources.ucp_porto.fetch_bytes", side_effect=lambda u: u.encode("utf-8")) as mock_fetch_bytes, \
             patch("academic_offers.sources.ucp_porto.extract_pdf_text", side_effect=lambda b: NOTICES[b.decode("utf-8")]):
            offers = scrape(today=dt.date(2026, 11, 27))

        mock_fetch.assert_called_once_with(LIST_URL)
        self.assertEqual(mock_fetch_bytes.call_count, 3)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].url, "https://www.porto.ucp.pt/pt-pt/asset/20001/file")


if __name__ == "__main__":
    unittest.main()
