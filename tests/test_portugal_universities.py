import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import portugal, universities


class TestPortugal(unittest.TestCase):
    def test_scrape_bep_valid_and_filtering(self):
        listing_html = """
        <html><body>
          <table>
            <tr><th>Código</th><th>Título</th><th>Carreira</th><th>Entidade</th></tr>
            <tr>
              <td>OE202605/0001</td>
              <td><a href="/Pages/Oferta/Oferta_Detalhes.aspx?CodOferta=1">Investigador Auxiliar</a></td>
              <td>Investigação Científica</td>
              <td>Universidade do Porto</td>
            </tr>
            <tr>
              <td>OE202605/0001</td>
              <td><a href="/Pages/Oferta/Oferta_Detalhes.aspx?CodOferta=1">Investigador Auxiliar</a></td>
              <td>Investigação Científica</td>
              <td>Universidade do Porto</td>
            </tr>
            <tr>
              <td>OE202605/0002</td>
              <td><a href="/Pages/Oferta/Oferta_Detalhes.aspx?CodOferta=2">Técnico Administrativo</a></td>
              <td>Assistente Técnico</td>
              <td>Câmara Municipal</td>
            </tr>
            <tr>
              <td>OE202605/0003</td>
              <td><a href="/Pages/Oferta/Outro.aspx?Cod=3">Docente Universitário</a></td>
              <td>Docente</td>
              <td>Universidade de Lisboa</td>
            </tr>
            <tr><td>only</td><td>two</td></tr>
          </table>
        </body></html>
        """
        detail_html = """
        <html><body>
          <h1>Concurso para Investigador Auxiliar em Física</h1>
          <p>Data limite de candidatura: 2026-06-15</p>
        </body></html>
        """

        def fake_fetch(url):
            if url == portugal.BEP_HOME:
                return listing_html
            if "CodOferta=1" in url:
                return detail_html
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("academic_offers.sources.portugal.fetch", side_effect=fake_fetch):
            offers = portugal.scrape_bep(today=dt.date(2026, 5, 20))

        self.assertEqual(len(offers), 1)
        o = offers[0]
        self.assertEqual(o.source, "bep")
        self.assertEqual(o.kind, "position")
        self.assertEqual(o.title, "Concurso para Investigador Auxiliar em Física")
        self.assertEqual(o.institution, "Universidade do Porto")
        self.assertEqual(o.region, "Portugal")
        self.assertEqual(o.position_type, "Investigação Científica")
        self.assertEqual(o.deadline, "2026-06-15")
        self.assertEqual(o.notes, "Código BEP: OE202605/0001")
        self.assertEqual(o.extra, {"bep_code": "OE202605/0001"})

    def test_scrape_bep_detail_failure_falls_back_to_row(self):
        listing_html = """
        <table>
          <tr>
            <td>OE202605/0099</td>
            <td><a href="/Pages/Oferta/Oferta_Detalhes.aspx?CodOferta=99">Bolseiro de Investigação</a></td>
            <td>Bolseiro</td>
            <td>FCT</td>
            <td>2026-07-01</td>
          </tr>
        </table>
        """

        def fake_fetch(url):
            if url == portugal.BEP_HOME:
                return listing_html
            raise RuntimeError("network error")

        with patch("academic_offers.sources.portugal.fetch", side_effect=fake_fetch):
            offers = portugal.scrape_bep()

        self.assertEqual(len(offers), 1)
        self.assertIn("Bolseiro de Investigação", offers[0].title)
        self.assertEqual(offers[0].deadline, "2026-07-01")

    def test_scrape_bep_empty_html(self):
        with patch("academic_offers.sources.portugal.fetch", return_value="<html><body></body></html>"):
            self.assertEqual(portugal.scrape_bep(), [])


class TestUniversities(unittest.TestCase):
    def test_href_date(self):
        self.assertEqual(universities._href_date("15-05-2026/index.html"), "2026-05-15")
        self.assertIsNone(universities._href_date("no-date/index.html"))

    def test_scrape_page_text_date_and_cutoff(self):
        page = universities.Page(
            key="ucm-ad",
            institution="UCM",
            region="Madrid",
            url="https://www.ucm.es/profesor-ayudante-doctor",
            position_type="Profesor/a Ayudante Doctor/a",
            link=r"Convocatoria publicada en el BOUC",
            date_from="text",
            title="Profesor/a Ayudante Doctor/a",
        )
        html = """
        <html><body>
          <nav><a href="/nav">Convocatoria publicada en el BOUC 10/05/2026</a></nav>
          <a href="/call-recent">Convocatoria publicada en el BOUC 10/05/2026</a>
          <a href="/call-recent">Convocatoria publicada en el BOUC 10/05/2026</a>
          <a href="/call-old">Convocatoria publicada en el BOUC 01/01/2026</a>
        </body></html>
        """
        with patch("academic_offers.sources.universities.fetch", return_value=html):
            offers = universities.scrape_page(page, today=dt.date(2026, 5, 20))

        self.assertEqual(len(offers), 1)
        o = offers[0]
        self.assertEqual(o.source, "uni:ucm-ad")
        self.assertEqual(o.published, "2026-05-10")
        self.assertEqual(o.title, "Profesor/a Ayudante Doctor/a – convocatoria del 10/05/2026")
        self.assertEqual(o.url, "https://www.ucm.es/call-recent")

    def test_scrape_page_href_date(self):
        page = universities.Page(
            key="ugr-ad",
            institution="UGR",
            region="Andalucía",
            url="https://serviciopdi.ugr.es/contratado/concursopublico/ayudantedoctor/index.html",
            position_type="Profesor/a Ayudante Doctor/a",
            link=r"\d{2}-\d{2}-20\d\d/index\.html",
            date_from="href",
            title="Profesor/a Ayudante Doctor/a",
        )
        html = '<a href="12-05-2026/index.html">Convocatoria</a>'
        with patch("academic_offers.sources.universities.fetch", return_value=html):
            offers = universities.scrape_page(page, today=dt.date(2026, 5, 20))

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].published, "2026-05-12")

    def test_scrape_page_detail_date(self):
        page = universities.Page(
            key="uc3m-pdi",
            institution="UC3M",
            region="Madrid",
            url="https://www.uc3m.es/empleo/pdi",
            position_type="",
            link=r"CONVOCATORIA .*20\d\d/",
            date_from="detail",
        )
        listing_html = """
        <a href="/empleo/c1">CONVOCATORIA Ayudante Doctor 2026/1</a>
        <a href="/empleo/c2">CONVOCATORIA 2024/9</a>
        <a href="/empleo/c3">CONVOCATORIA Sin Plazo 2026/2</a>
        """
        detail_ok = "<p>El plazo de presentación finaliza el 30/05/2026.</p>"
        detail_no_date = "<p>Información general.</p>"

        def fake_fetch(url):
            if url == page.url:
                return listing_html
            if url.endswith("/c1"):
                return detail_ok
            if url.endswith("/c3"):
                return detail_no_date
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("academic_offers.sources.universities.fetch", side_effect=fake_fetch):
            offers = universities.scrape_page(page, today=dt.date(2026, 5, 20))

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-05-30")
        self.assertEqual(offers[0].position_type, "Profesor/a Ayudante Doctor/a")

    def test_scrape_page_empty_html(self):
        page = universities.PAGES[0]
        with patch("academic_offers.sources.universities.fetch", return_value="<html></html>"):
            self.assertEqual(universities.scrape_page(page, today=dt.date(2026, 5, 20)), [])

    def test_scrape_aggregates_and_ignores_failing_page(self):
        p1 = universities.PAGES[0]
        p2 = universities.PAGES[3]

        def fake_fetch(url):
            if url == p1.url:
                return '<a href="/ok">Convocatoria publicada en el BOUC 15/05/2026</a>'
            raise RuntimeError("boom")

        with patch("academic_offers.sources.universities.PAGES", [p1, p2]), \
             patch("academic_offers.sources.universities.fetch", side_effect=fake_fetch):
            offers = universities.scrape(today=dt.date(2026, 5, 20))

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].source, "uni:ucm-ad")


if __name__ == "__main__":
    unittest.main()
