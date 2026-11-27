"""Offline unit tests for the Instituto Superior Técnico (IST) source."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import ist

TODAY = dt.date(2026, 11, 27)

BOLSEIROS_HTML = """
<table>
  <tr>
    <th>Nº vagas</th><th>Tipo de bolsa</th><th>Responsável</th>
    <th>Área / Projeto</th><th colspan="2">Edital</th>
    <th>Data abertura</th><th>Prazo limite</th>
  </tr>
  <tr><th>PT</th><th>EN</th></tr>
  <tr>
    <td>2</td>
    <td>Iniciação à Investigação</td>
    <td>Prof. Miguel Mendes</td>
    <td>Carbonização de resíduos</td>
    <td></td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/ist-2026-bl249.pdf">IST 2026 BL249</a></td>
    <td>27.11.2026</td>
    <td>04.12.2026</td>
  </tr>
  <tr>
    <td>1</td>
    <td>Investigação</td>
    <td>Prof. Expired</td>
    <td>Projeto antigo</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/ist-old.pdf">IST OLD</a></td>
    <td></td>
    <td>01.10.2026</td>
    <td>15.10.2026</td>
  </tr>
  <tr>
    <td>1</td>
    <td>Investigação</td>
    <td>Prof. External</td>
    <td>Link externo inválido</td>
    <td><a href="https://evil.example.com/edital.pdf">EXT</a></td>
    <td></td>
    <td>27.11.2026</td>
    <td>10.12.2026</td>
  </tr>
</table>
"""

DOCENTES_HTML = """
<table>
  <tr>
    <th>Posição</th><th>Dep.</th><th>Área(s) disciplinar(es)</th>
    <th>Edital DR</th><th>Data pub.</th><th>Prazo limite</th><th>Mais info</th>
  </tr>
  <tr>
    <td>1 Professor associado</td>
    <td>DM</td>
    <td>Física-matemática</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/edital_1416_2026.pdf">1416 (PDF)</a></td>
    <td>06.11.2026</td>
    <td>22.12.2026</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/info_concs_doc_v2.pdf">mais info</a></td>
  </tr>
  <tr>
    <td>1 Professor associado</td>
    <td>DEQ</td>
    <td>Síntese Química</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/edital-1208.pdf">1208</a></td>
    <td>08.07.2026</td>
    <td>Despacho n.º 212/2026, Cessação do concurso</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/associate-professor-deq/">mais info</a></td>
  </tr>
</table>
<table>
  <tr>
    <td>1 Professor auxiliar</td>
    <td>DEI</td>
    <td>Inteligência artificial</td>
    <td><a href="https://diariodarepublica.pt/dr/detalhe/edital/999-2026">999</a></td>
    <td>20.11.2026</td>
    <td>Em aberto</td>
    <td></td>
  </tr>
</table>
"""

RESEARCHER_HTML = """
<table>
  <tr>
    <th>Vagas</th><th>Deptº</th><th>Área disciplinar</th>
    <th>Categoria</th><th colspan="2">Edital nº</th>
    <th>Prazo limite</th><th>Submissão de candidatura</th>
  </tr>
  <tr><th>PT</th><th>EN</th></tr>
  <tr>
    <td>3</td>
    <td>DECN</td>
    <td>Tecnologias nucleares</td>
    <td>Investigador auxiliar</td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/aviso_9260_2026.pdf">9260</a></td>
    <td><a href="https://drh.tecnico.ulisboa.pt/files/sites/45/en_9260.pdf">9260_EN</a></td>
    <td>15.12.2026</td>
    <td><a href="https://dot.tecnico.ulisboa.pt/admissions/contest/1416136616837346">submeter candidatura</a></td>
  </tr>
</table>
"""


class IstSourceTests(unittest.TestCase):
    def test_parse_bolseiros_filters_expired_and_unofficial_urls(self):
        offers = ist.parse_listing(BOLSEIROS_HTML, TODAY, base_url=ist.BOLSEIROS_URL)
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "ist")
        self.assertEqual(offer.kind, "position")
        self.assertEqual(offer.institution, "Instituto Superior Técnico – ULisboa")
        self.assertEqual(offer.region, "Lisboa")
        self.assertEqual(offer.n_posts, 2)
        self.assertEqual(offer.deadline, "2026-12-04")
        self.assertEqual(offer.published, "2026-11-27")
        self.assertEqual(
            offer.url,
            "https://drh.tecnico.ulisboa.pt/files/sites/45/ist-2026-bl249.pdf",
        )
        self.assertIn("Carbonização de resíduos", offer.title)

    def test_parse_docentes_skips_closed_and_keeps_headerless_table_without_inventing_date(self):
        offers = ist.parse_listing(DOCENTES_HTML, TODAY, base_url=ist.DOCENTES_URL)
        self.assertEqual(len(offers), 2)

        first, second = offers
        self.assertEqual(first.position_type, "Professor associado")
        self.assertEqual(first.deadline, "2026-12-22")
        self.assertEqual(
            first.url,
            "https://drh.tecnico.ulisboa.pt/files/sites/45/edital_1416_2026.pdf",
        )

        self.assertEqual(second.position_type, "Professor auxiliar")
        self.assertIsNone(second.deadline)
        self.assertEqual(second.url, "https://diariodarepublica.pt/dr/detalhe/edital/999-2026")

    def test_parse_researcher_prefers_dot_tecnico_contest_url(self):
        offers = ist.parse_listing(RESEARCHER_HTML, TODAY, base_url=ist.RESEARCHER_URL)
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.n_posts, 3)
        self.assertEqual(offer.position_type, "Investigador auxiliar")
        self.assertEqual(offer.area_raw, "Tecnologias nucleares")
        self.assertEqual(offer.deadline, "2026-12-15")
        self.assertEqual(
            offer.url,
            "https://dot.tecnico.ulisboa.pt/admissions/contest/1416136616837346",
        )

    def test_scrape_continues_when_one_page_fails(self):
        def fake_fetch(url: str) -> str:
            if url == ist.BOLSEIROS_URL:
                raise RuntimeError("timeout")
            if url == ist.DOCENTES_URL:
                return DOCENTES_HTML
            if url == ist.RESEARCHER_URL:
                return RESEARCHER_HTML
            return "<html><body><p>Sem concursos abertos.</p></body></html>"

        with patch("academic_offers.sources.ist.fetch", side_effect=fake_fetch):
            offers = ist.scrape(today=TODAY)

        self.assertEqual(len(offers), 3)
        self.assertTrue(all(o.source == "ist" for o in offers))


if __name__ == "__main__":
    unittest.main()
