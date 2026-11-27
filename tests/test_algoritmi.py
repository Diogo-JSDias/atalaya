"""Offline tests for the Centro ALGORITMI open positions adapter."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources.algoritmi import LIST_URL, parse_listing, scrape


SAMPLE_HTML = """
<html><body>
  <div class="elementor-tabs" role="tablist">
    <div class="elementor-tabs-wrapper">
      <div id="elementor-tab-title-1" class="elementor-tab-title elementor-tab-desktop-title"
           data-tab="1" role="tab" aria-controls="elementor-tab-content-1">
        <a href="">Open</a>
      </div>
      <div id="elementor-tab-title-2" class="elementor-tab-title elementor-tab-desktop-title"
           data-tab="2" role="tab" aria-controls="elementor-tab-content-2">
        <a href="">Closed</a>
      </div>
    </div>
    <div class="elementor-tabs-content-wrapper">
      <div class="elementor-tab-title elementor-tab-mobile-title" data-tab="1" role="tab">Open</div>
      <div class="elementor-tab-content elementor-clearfix" data-tab="1" role="tabpanel"
           aria-labelledby="elementor-tab-title-1">
        <div class="col-md-4">
          <div class="news-card">
            <div class="news-card-header">
              <p class="news-title">Bolsa de Investigação para Mestre em Engenharia Eletrónica Industrial e Computadores</p>
              <p class="news-date">27/11/2026 - 15/12/2026</p>
            </div>
            <div class="news-card-content">
              <p class="positions-reference"><strong>Referência</strong>:CALG_EXOCARE_BI_2026_02</p>
              <p class="news-description">Concurso para atribuição de 1 bolsa de investigação.</p>
            </div>
            <div class="news-card-footer">
              <a href="https://algoritmi.uminho.pt/open_positions/calg_exocare_bi_2026_02/">See more</a>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="news-card">
            <div class="news-card-header">
              <p class="news-title">Bolsa de Investigação Expirada</p>
              <p class="news-date">01/10/2026 - 15/10/2026</p>
            </div>
            <div class="news-card-footer">
              <a href="https://algoritmi.uminho.pt/open_positions/expirada/">See more</a>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="news-card">
            <div class="news-card-header">
              <p class="news-title">Oferta Sem Prazo Definido</p>
              <p class="news-date"></p>
            </div>
            <div class="news-card-footer">
              <a href="/open_positions/sem-prazo/">See more</a>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="news-card">
            <div class="news-card-header">
              <p class="news-title">Oferta Externa Não Oficial</p>
              <p class="news-date">27/11/2026 - 20/12/2026</p>
            </div>
            <div class="news-card-footer">
              <a href="https://example.com/jobs/123">See more</a>
            </div>
          </div>
        </div>
      </div>

      <div class="elementor-tab-title elementor-tab-mobile-title" data-tab="2" role="tab">Closed</div>
      <div class="elementor-tab-content elementor-clearfix" data-tab="2" role="tabpanel"
           aria-labelledby="elementor-tab-title-2">
        <div class="col-md-4">
          <div class="news-card">
            <div class="news-card-header">
              <p class="news-title">Bolsa no Separador Closed</p>
              <p class="news-date">20/11/2026 - 30/12/2026</p>
            </div>
            <div class="news-card-footer">
              <a href="https://algoritmi.uminho.pt/open_positions/closed-tab-item/">See more</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body></html>
"""


class AlgoritmiSourceTests(unittest.TestCase):
    def test_parses_open_offers_and_skips_closed_expired_and_unofficial(self):
        offers = parse_listing(SAMPLE_HTML, dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 2)

        first = offers[0]
        self.assertEqual(first.source, "algoritmi")
        self.assertEqual(first.kind, "position")
        self.assertEqual(
            first.title,
            "Bolsa de Investigação para Mestre em Engenharia Eletrónica Industrial e Computadores",
        )
        self.assertEqual(
            first.url,
            "https://algoritmi.uminho.pt/open_positions/calg_exocare_bi_2026_02/",
        )
        self.assertEqual(first.institution, "Centro ALGORITMI – Universidade do Minho")
        self.assertEqual(first.region, "Norte")
        self.assertEqual(first.published, "2026-11-27")
        self.assertEqual(first.deadline, "2026-12-15")
        self.assertEqual(first.notes, "Concurso para atribuição de 1 bolsa de investigação.")
        self.assertEqual(first.extra.get("algoritmi_ref"), "CALG_EXOCARE_BI_2026_02")

        second = offers[1]
        self.assertEqual(second.title, "Oferta Sem Prazo Definido")
        self.assertEqual(second.url, "https://algoritmi.uminho.pt/open_positions/sem-prazo/")
        self.assertIsNone(second.published)
        self.assertIsNone(second.deadline)

    def test_empty_html_returns_empty_list(self):
        self.assertEqual(parse_listing("", dt.date(2026, 11, 27)), [])
        self.assertEqual(parse_listing("<html><body></body></html>", dt.date(2026, 11, 27)), [])

    def test_accepts_other_official_hosts(self):
        html = """
        <div class="elementor-tab-title" data-tab="1">Open</div>
        <div class="elementor-tab-content" data-tab="1">
          <div class="news-card">
            <p class="news-title">Edital DRE</p>
            <p class="news-date">27/11/2026 - 10/12/2026</p>
            <a href="https://diariodarepublica.pt/dr/detalhe/aviso/12345">Ver</a>
          </div>
        </div>
        """
        offers = parse_listing(html, dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].url, "https://diariodarepublica.pt/dr/detalhe/aviso/12345")

    @patch("academic_offers.sources.algoritmi.fetch")
    def test_scrape_uses_fetch_and_filters_by_today(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_HTML
        offers = scrape(dt.date(2026, 11, 27))
        mock_fetch.assert_called_once_with(LIST_URL)
        self.assertEqual(len(offers), 2)
        self.assertEqual(offers[0].deadline, "2026-12-15")


if __name__ == "__main__":
    unittest.main()
