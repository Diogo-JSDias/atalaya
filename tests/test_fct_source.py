"""Tests for the public FCT open-calls listing parser."""
import unittest

from academic_offers.sources.fct import parse_open_listing


class FCTSourceTests(unittest.TestCase):
    def test_extracts_detail_link_and_explicit_deadline(self):
        html = """
        <html><main><article>
          <a href="/concursos/concurso-exemplo/">Concurso de Bolsas de Doutoramento</a>
          <p>Data limite: 31/03/2027. Candidaturas abertas.</p>
        </article></main></html>
        """
        offers = parse_open_listing(html)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].source, "fct")
        self.assertEqual(offers[0].kind, "call")
        self.assertEqual(offers[0].url, "https://www.fct.pt/concursos/concurso-exemplo/")
        self.assertEqual(offers[0].deadline, "2027-03-31")

    def test_month_year_is_not_guessed_as_exact_deadline(self):
        html = """
        <html><main><article>
          <a href="/concursos/concurso-previsto/">Concurso de Projetos de Investigação</a>
          <p>Data Limite jan 2027</p>
        </article></main></html>
        """
        offers = parse_open_listing(html)
        self.assertEqual(len(offers), 1)
        self.assertIsNone(offers[0].deadline)

    def test_ignores_external_and_navigation_links(self):
        html = """
        <html><main>
          <a href="https://example.org/concurso">Concurso externo de investigação</a>
          <a href="/concursos/">Concursos e oportunidades da FCT</a>
          <a href="/sobre/">Concurso institucional sem detalhe</a>
        </main></html>
        """
        self.assertEqual(parse_open_listing(html), [])

    def test_deduplicates_detail_urls(self):
        html = """
        <html><main><article>
          <a href="/concursos/um/">Concurso de investigação científica</a>
          <p>Candidaturas abertas</p>
          <a href="/concursos/um/">Concurso de investigação científica</a>
        </article></main></html>
        """
        self.assertEqual(len(parse_open_listing(html)), 1)


if __name__ == "__main__":
    unittest.main()
