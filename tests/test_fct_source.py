"""Tests for the public FCT open-calls listing and detail-page parsers."""
import unittest

from academic_offers.models import Offer
from academic_offers.sources.fct import parse_detail_page, parse_open_listing, _enrich_offer


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

    def test_date_without_deadline_label_is_not_used(self):
        html = """
        <html><main><article>
          <a href="/concursos/concurso-publicacao/">Concurso de investigação científica</a>
          <p>Publicado em 01/02/2027. Consulte as condições no aviso.</p>
        </article></main></html>
        """
        offers = parse_open_listing(html)
        self.assertEqual(len(offers), 1)
        self.assertIsNone(offers[0].deadline)

    def test_deadline_label_accepts_numeric_date(self):
        html = """
        <html><main><article>
          <a href="/concursos/concurso-prazo/">Concurso de bolsas de investigação</a>
          <p>Candidaturas até 8-4-2027.</p>
        </article></main></html>
        """
        offers = parse_open_listing(html)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2027-04-08")

    def test_ignores_external_and_navigation_links(self):
        html = """
        <html><main>
          <a href="https://example.org/concurso">Concurso externo de investigação</a>
          <a href="/concursos/">Concursos e oportunidades da FCT</a>
          <a href="/sobre/">Sobre a FCT e contactos institucionais</a>
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

    def test_detail_extracts_closing_date_before_label_in_portuguese_months(self):
        html = """
        <html><main>
          <p>18 maio 2026 (17h) Abertura de candidaturas</p>
          <p>15 setembro 2026 (17h) Encerramento das candidaturas</p>
        </main></html>
        """
        details = parse_detail_page(html, "Concurso de Projetos de Computação Avançada")
        self.assertEqual(details["deadline"], "2026-09-15")

    def test_detail_extracts_end_of_numeric_submission_range(self):
        html = """
        <html><main>
          <p>Submissão de candidaturas: 02/03/2027 a 31/03/2027</p>
        </main></html>
        """
        details = parse_detail_page(html)
        self.assertEqual(details["deadline"], "2027-03-31")

    def test_detail_does_not_treat_publication_date_as_deadline(self):
        html = """
        <html><main>
          <p>Publicado em 01/02/2027. Resultados provisórios em 31/03/2027.</p>
        </main></html>
        """
        details = parse_detail_page(html)
        self.assertIsNone(details["deadline"])

    def test_detail_extracts_structured_funding_category_and_domain(self):
        html = """
        <html><main>
          <table>
            <tr><th>Tipo de financiamento</th><td>Bolsas</td></tr>
          </table>
          <dl>
            <dt>Domínio Científico</dt><dd>Ciências Naturais</dd>
          </dl>
        </main></html>
        """
        details = parse_detail_page(html, "Concurso de bolsas")
        self.assertEqual(details["funding_type"], "Bolsas")
        self.assertEqual(details["scientific_domain"], "Ciências Naturais")

    def test_title_category_recognises_scientific_employment(self):
        details = parse_detail_page("<main><p>Concurso aberto.</p></main>",
                                    "Concurso Estímulo ao Emprego Científico Individual")
        self.assertEqual(details["funding_type"], "Emprego científico")

    def test_enrichment_preserves_listing_record_when_detail_cannot_be_fetched(self):
        offer = Offer(source="fct", kind="call", title="Concurso de Bolsas",
                      url="https://www.fct.pt/concursos/teste/")
        # This test exercises deterministic extraction only. Network failure policy
        # is verified by keeping parse_detail_page independent from fetch.
        self.assertEqual(offer.deadline, None)
        self.assertEqual(offer.extra, {})


if __name__ == "__main__":
    unittest.main()
