"""Tests for the Universidade do Minho central recruitment portal."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources.uminho import discover_category_urls, parse_listing, scrape


HOME_HTML = """
<html><body><main>
  <a href="/portal-recrutamento/frontoffice/concursos.xhtml?tipo=DIR">Dirigentes</a>
  <a href="/portal-recrutamento/frontoffice/concursos.xhtml?tipo=DOC">Docentes de Carreira</a>
  <a href="/portal-recrutamento/frontoffice/concursos.xhtml?tipo=INVT">Investigadores a Termo</a>
  <a href="/portal-recrutamento/frontoffice/concursos.xhtml?tipo=INV">Investigadores de Carreira</a>
  <a href="/portal-recrutamento/frontoffice/concursos.xhtml?tipo=PTAG">PTAG</a>
</main></body></html>
"""

LISTING_HTML = """
<html><body><main>
  <div class="concursos-grid-react">
    <div class="concurso-react-card">
      <div class="concurso-react-card-top">
        <div class="concurso-react-badges">
          <span class="badge badge-published">Receção de Candidaturas</span>
        </div>
        <div class="concurso-react-ref">CTI-DOC-10-26-ECUM</div>
      </div>
      <h3 class="concurso-react-title">Professor Auxiliar na área de Física</h3>
      <div class="concurso-react-meta">
        <div class="meta-item"><i class="pi pi-building"></i> <span>Escola de Ciências</span></div>
        <div class="meta-item"><i class="pi pi-map-marker"></i>Universidade do Minho</div>
        <div class="meta-item"><i class="pi pi-briefcase"></i> <span>Docentes de Carreira</span></div>
        <div class="meta-item"><i class="pi pi-users"></i> <span>2 vaga(s)</span></div>
      </div>
      <div class="concurso-react-dates">
        <span><i class="pi pi-calendar"></i> Abertura: 10/11/2026</span>
        <span><i class="pi pi-clock"></i> Fecho: 15/01/2027</span>
      </div>
      <div class="concurso-react-footer">
        <button type="button" class="concurso-react-btn"
          onclick="window.open('\\/portal\\-recrutamento\\/frontoffice\\/concurso.xhtml?id=401','_self')">Detalhes</button>
      </div>
    </div>

    <div class="concurso-react-card">
      <div class="concurso-react-card-top">
        <div class="concurso-react-badges">
          <span class="badge badge-published">Publicado</span>
        </div>
        <div class="concurso-react-ref">CTI-INVT-22-26-EEUM</div>
      </div>
      <h3 class="concurso-react-title">Investigador Doutorado</h3>
      <div class="concurso-react-meta">
        <div class="meta-item"><i class="pi pi-building"></i> <span>Escola de Engenharia</span></div>
        <div class="meta-item"><i class="pi pi-users"></i> <span>1 vaga(s)</span></div>
      </div>
      <div class="concurso-react-dates">
        <span><i class="pi pi-calendar"></i> Abertura: 01/08/2026</span>
        <span><i class="pi pi-clock"></i> Fecho: 20/08/2026</span>
      </div>
      <div class="concurso-react-footer">
        <button type="button" class="concurso-react-btn"
          onclick="window.open('\\/portal\\-recrutamento\\/frontoffice\\/concurso.xhtml?id=312','_self')">Detalhes</button>
      </div>
    </div>

    <div class="concurso-react-card">
      <div class="concurso-react-card-top">
        <div class="concurso-react-badges">
          <span class="badge badge-published">Audiência</span>
        </div>
        <div class="concurso-react-ref">CTI-INV-05-26-ICVS</div>
      </div>
      <h3 class="concurso-react-title">Investigador Principal (em audiência)</h3>
      <div class="concurso-react-dates">
        <span><i class="pi pi-calendar"></i> Abertura: 01/10/2026</span>
        <span><i class="pi pi-clock"></i> Fecho: 15/01/2027</span>
      </div>
      <div class="concurso-react-footer">
        <button type="button" class="concurso-react-btn"
          onclick="window.open('\\/portal\\-recrutamento\\/frontoffice\\/concurso.xhtml?id=350','_self')">Detalhes</button>
      </div>
    </div>
  </div>
</main></body></html>
"""


class UMinhoSourceTests(unittest.TestCase):
    def test_discovers_only_academic_category_urls(self):
        categories = discover_category_urls(HOME_HTML)
        self.assertEqual([code for code, _label, _url in categories], ["DOC", "INVT", "INV"])
        self.assertEqual(
            categories[0][2],
            "https://recrutamento.uminho.pt/portal-recrutamento/frontoffice/concursos.xhtml?tipo=DOC",
        )

    def test_extracts_open_offers_and_filters_closed_statuses(self):
        offers = parse_listing(LISTING_HTML, base_url="https://recrutamento.uminho.pt/portal-recrutamento/frontoffice/concursos.xhtml?tipo=DOC")
        self.assertEqual(len(offers), 2)
        first = offers[0]
        self.assertEqual(first.source, "uminho")
        self.assertEqual(first.title, "Professor Auxiliar na área de Física")
        self.assertEqual(
            first.url,
            "https://recrutamento.uminho.pt/portal-recrutamento/frontoffice/concurso.xhtml?id=401",
        )
        self.assertEqual(first.institution, "Universidade do Minho — Escola de Ciências")
        self.assertEqual(first.region, "Braga")
        self.assertEqual(first.position_type, "Docentes de Carreira")
        self.assertEqual(first.published, "2026-11-10")
        self.assertEqual(first.deadline, "2027-01-15")
        self.assertEqual(first.n_posts, 2)
        self.assertEqual(first.extra["uminho_ref"], "CTI-DOC-10-26-ECUM")

    def test_does_not_guess_missing_deadline(self):
        html = """
        <div class="concurso-react-card">
          <div class="concurso-react-badges"><span class="badge">Publicado</span></div>
          <h3 class="concurso-react-title">Professor Associado</h3>
          <button onclick="window.open('/portal-recrutamento/frontoffice/concurso.xhtml?id=99','_self')">Detalhes</button>
        </div>
        """
        offers = parse_listing(html)
        self.assertEqual(len(offers), 1)
        self.assertIsNone(offers[0].deadline)
        self.assertIn("Prazo não identificado", offers[0].notes)

    def test_rejects_non_official_urls(self):
        html = """
        <div class="concurso-react-card">
          <div class="concurso-react-badges"><span class="badge">Publicado</span></div>
          <h3 class="concurso-react-title">Professor Associado</h3>
          <a href="https://example.org/concurso.xhtml?id=99">Detalhes</a>
        </div>
        """
        self.assertEqual(parse_listing(html), [])

    @patch("academic_offers.sources.uminho.fetch")
    def test_scrape_filters_expired_deadlines_and_deduplicates(self, mock_fetch):
        empty_html = "<div class='empty-state'>0 processos</div>"
        mock_fetch.side_effect = [HOME_HTML, LISTING_HTML, empty_html, empty_html]
        offers = scrape(dt.date(2026, 11, 27))
        self.assertEqual([offer.deadline for offer in offers], ["2027-01-15"])
        self.assertEqual(mock_fetch.call_count, 4)


if __name__ == "__main__":
    unittest.main()
