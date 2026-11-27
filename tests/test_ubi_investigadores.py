"""Tests for UBI researcher recruitment competitions."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources.ubi_investigadores import parse_listing, scrape


HTML = """
<html><body>
<h2>Concursos para Investigadores</h2>
<h3>Estatuto da Carreira de Investigação Científica</h3>
<h3>Candidaturas a decorrer:</h3>
<p>As candidaturas são submetidas nos termos indicados no edital.</p>
<table>
<thead><tr>
<th>Investigador / researcher</th>
<th>Área Científica do Concurso / Scientific area of the contest</th>
<th>Postos de Trabalho / Vacant post</th>
<th>BEP Anúncios / Announcements</th>
<th>Edital / Public notice</th>
<th>Data Limite / Application Deadline</th>
<th>Registo / Registration</th>
</tr></thead>
<tbody>
<tr>
<td>Principal / Principal</td>
<td>Engenharia Biomédica / Biomedical Engineering</td>
<td>2</td><td>BEP</td>
<td><a href="/Ficheiros/Sites/53/Investigadores/Edital%20n%C2%BA%20112-2026.pdf">Edital nº 112/2026</a></td>
<td>30/12/2026</td>
<td><a href="https://forms.cloud.microsoft/example">Registo de Candidatura</a></td>
</tr>
<tr>
<td>Auxiliar / Assistant</td>
<td>Biomedicina / Biomedicine</td>
<td>1</td><td>BEP</td>
<td><a href="https://files.diariodarepublica.pt/2s/2026/11/227000000/0023100241.pdf">Edital nº 113/2026</a></td>
<td>2026-12-05</td><td></td>
</tr>
</tbody>
</table>
<h3>Candidaturas encerradas:</h3>
<table>
<tr>
<th>Investigador / researcher</th><th>Área Científica</th><th>Postos</th>
<th>BEP</th><th>Edital</th><th>Data Limite</th><th>Registo</th>
</tr>
<tr>
<td>Principal</td><td>Física</td><td>1</td><td>BEP</td>
<td><a href="/old.pdf">Edital nº 99/2025</a></td><td>11/09/2025</td><td></td>
</tr>
</table>
</body></html>
"""


class UBIInvestigadoresTests(unittest.TestCase):
    def test_extracts_only_open_researcher_table(self):
        offers = parse_listing(HTML)
        self.assertEqual(len(offers), 2)
        first = offers[0]
        self.assertEqual(first.title, "Principal / Principal — Engenharia Biomédica / Biomedical Engineering")
        self.assertEqual(first.position_type, "Principal / Principal")
        self.assertEqual(first.deadline, "2026-12-30")
        self.assertEqual(first.n_posts, 2)
        self.assertEqual(first.extra["ubi_notice"], "112/2026")
        self.assertEqual(
            first.url,
            "https://www.ubi.pt/Ficheiros/Sites/53/Investigadores/Edital%20n%C2%BA%20112-2026.pdf",
        )
        self.assertEqual(
            first.extra["application_url"],
            "https://forms.cloud.microsoft/example",
        )
        self.assertEqual(first.institution, "Universidade da Beira Interior")

    def test_supports_iso_deadline_and_dre_notice(self):
        offer = parse_listing(HTML)[1]
        self.assertEqual(offer.deadline, "2026-12-05")
        self.assertEqual(offer.url, "https://files.diariodarepublica.pt/2s/2026/11/227000000/0023100241.pdf")
        self.assertEqual(offer.extra["ubi_notice"], "113/2026")

    def test_empty_open_table_is_valid_and_closed_table_is_ignored(self):
        empty = """
        <h2>Concursos para Investigadores</h2>
        <h3>Candidaturas a decorrer:</h3>
        <table><tr>
          <th>Investigador / researcher</th><th>Área Científica</th>
          <th>Postos</th><th>BEP</th><th>Edital</th>
          <th>Data Limite</th><th>Registo</th>
        </tr></table>
        <h3>Candidaturas encerradas:</h3>
        <table><tr>
          <th>Investigador / researcher</th><th>Área Científica</th>
          <th>Postos</th><th>BEP</th><th>Edital</th>
          <th>Data Limite</th><th>Registo</th>
        </tr><tr>
          <td>Principal</td><td>Física</td><td>1</td><td>BEP</td>
          <td><a href="/old.pdf">Edital nº 99/2025</a></td>
          <td>11/09/2025</td><td></td>
        </tr></table>
        """
        self.assertEqual(parse_listing(empty), [])

    def test_scrape_filters_expired_deadlines(self):
        with patch(
            "academic_offers.sources.ubi_investigadores.fetch",
            return_value=HTML,
        ) as mock_fetch:
            offers = scrape(dt.date(2026, 12, 10))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-12-30")
        mock_fetch.assert_called_once_with(
            "https://www.ubi.pt/Sites/Academicos/pt/Pagina/recrutamento"
        )

    def test_fails_closed_when_open_table_disappears(self):
        changed = """
        <h2>Concursos para Investigadores</h2>
        <h3>Candidaturas a decorrer:</h3>
        <h3>Candidaturas encerradas:</h3>
        <table><tr><th>Investigador</th><th>Área Científica</th>
        <th>Postos</th><th>BEP</th><th>Edital</th>
        <th>Data Limite</th><th>Registo</th></tr></table>
        """
        with self.assertRaises(RuntimeError):
            parse_listing(changed)

    def test_fails_closed_when_open_row_has_no_official_notice(self):
        changed = HTML.replace(
            '<a href="/Ficheiros/Sites/53/Investigadores/Edital%20n%C2%BA%20112-2026.pdf">Edital nº 112/2026</a>',
            '<a href="https://example.org/edital.pdf">Edital nº 112/2026</a>',
        )
        with self.assertRaises(RuntimeError):
            parse_listing(changed)


if __name__ == "__main__":
    unittest.main()
