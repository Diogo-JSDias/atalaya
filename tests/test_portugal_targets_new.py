"""Offline unit tests for the new portugal_targets scrapers: ipatimup, inescc, cintesis."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources.portugal_targets import ipatimup, inescc, cintesis

TODAY = dt.date(2026, 11, 27)
TODAY_ISO = TODAY.isoformat()

# ---------------------------------------------------------------------------
# Shared HTML helpers
# ---------------------------------------------------------------------------

def _html_with_links(links: list[tuple[str, str, str]]) -> str:
    """Build a minimal HTML page with academic job links.

    links: list of (href, link_text, surrounding_context)
    """
    items = ""
    for href, text, context in links:
        items += f'<article class="call-card"><p>{context}</p><a href="{href}">{text}</a></article>\n'
    return f"<html><body>{items}</body></html>"


# ---------------------------------------------------------------------------
# IPATIMUP
# ---------------------------------------------------------------------------

IPATIMUP_HTML_OPEN = _html_with_links([
    (
        "https://www.ipatimup.pt/opportunities/postdoc-molecular-oncology/",
        "Postdoctoral Researcher – Molecular Oncology",
        "Open call. Deadline: 2027-01-15. Fellowship position.",
    ),
    (
        "https://www.ipatimup.pt/opportunities/phd-grant-2026/",
        "Bolsa de Investigação – Doutoramento em Imunologia",
        "Open. Candidaturas até 31 de dezembro de 2026.",
    ),
])

IPATIMUP_HTML_CLOSED = _html_with_links([
    (
        "https://www.ipatimup.pt/opportunities/old-call/",
        "Research Scientist – Genomics",
        "Candidaturas encerradas. Esta chamada encontra-se fechada.",
    ),
])

IPATIMUP_HTML_EXPIRED = _html_with_links([
    (
        "https://www.ipatimup.pt/opportunities/expired/",
        "Bolsa de Investigação – Proteómica",
        "Open call. Application deadline 01/01/2020. Investigador.",
    ),
])


class IpatimupTests(unittest.TestCase):

    def _run(self, html: str):
        with patch("academic_offers.sources.portugal_targets.fetch", return_value=html):
            return ipatimup(today=TODAY)

    def test_open_offers_returned(self):
        offers = self._run(IPATIMUP_HTML_OPEN)
        self.assertEqual(len(offers), 2)

    def test_offer_fields(self):
        offers = self._run(IPATIMUP_HTML_OPEN)
        titles = {o.title for o in offers}
        self.assertIn("Postdoctoral Researcher – Molecular Oncology", titles)
        bolsa_offer = next(o for o in offers if "Bolsa" in o.title)
        self.assertEqual(bolsa_offer.source, "ipatimup")
        self.assertEqual(bolsa_offer.region, "Porto")
        self.assertIn("Ipatimup", bolsa_offer.institution)
        self.assertEqual(bolsa_offer.kind, "call")  # 'bolsa' in title → call

    def test_closed_offers_excluded(self):
        offers = self._run(IPATIMUP_HTML_CLOSED)
        self.assertEqual(offers, [])

    def test_expired_deadline_excluded(self):
        offers = self._run(IPATIMUP_HTML_EXPIRED)
        self.assertEqual(offers, [])

    def test_empty_html_returns_empty(self):
        offers = self._run("")
        self.assertEqual(offers, [])

    def test_fetch_error_returns_empty(self):
        with patch(
            "academic_offers.sources.portugal_targets.fetch",
            side_effect=Exception("network error"),
        ):
            offers = ipatimup(today=TODAY)
        self.assertEqual(offers, [])


# ---------------------------------------------------------------------------
# INESC Coimbra
# ---------------------------------------------------------------------------

INESCC_HTML_OPEN = _html_with_links([
    (
        "https://www.inescc.pt/bolsas/bolsa-investigacao-bi-2026-01/",
        "Bolsa de Investigação – Redes Inteligentes de Energia",
        "Aberto. Prazo de candidatura: 15 de janeiro de 2027. Investigador.",
    ),
    (
        "https://www.inescc.pt/bolsas/bipd-2026-02/",
        "Bolsa de Investigação Pós-Doutoral – Otimização em Sistemas de Energia",
        "Open call. Deadline: 2027-02-28. Post-doc researcher position.",
    ),
])

INESCC_HTML_CLOSED = _html_with_links([
    (
        "https://www.inescc.pt/bolsas/old-bi/",
        "Bolsa de Investigação – Machine Learning",
        "Candidaturas encerradas. Prazo expirado.",
    ),
])

INESCC_HTML_NON_ACADEMIC = _html_with_links([
    (
        "https://www.inescc.pt/sobre/",
        "Sobre o INESC Coimbra",
        "Informações sobre o instituto. Missão e valores.",
    ),
])


class InescCTests(unittest.TestCase):

    def _run(self, html: str):
        with patch("academic_offers.sources.portugal_targets.fetch", return_value=html):
            return inescc(today=TODAY)

    def test_open_offers_returned(self):
        offers = self._run(INESCC_HTML_OPEN)
        self.assertEqual(len(offers), 2)

    def test_offer_fields(self):
        offers = self._run(INESCC_HTML_OPEN)
        for o in offers:
            self.assertEqual(o.source, "inescc")
            self.assertEqual(o.region, "Centro")
            self.assertIn("INESC Coimbra", o.institution)
            self.assertEqual(o.kind, "call")  # 'bolsa' in title

    def test_closed_offers_excluded(self):
        offers = self._run(INESCC_HTML_CLOSED)
        self.assertEqual(offers, [])

    def test_non_academic_links_excluded(self):
        offers = self._run(INESCC_HTML_NON_ACADEMIC)
        self.assertEqual(offers, [])

    def test_empty_html_returns_empty(self):
        offers = self._run("")
        self.assertEqual(offers, [])

    def test_fetch_error_returns_empty(self):
        with patch(
            "academic_offers.sources.portugal_targets.fetch",
            side_effect=Exception("network error"),
        ):
            offers = inescc(today=TODAY)
        self.assertEqual(offers, [])


# ---------------------------------------------------------------------------
# CINTESIS
# ---------------------------------------------------------------------------

CINTESIS_HTML_OPEN = _html_with_links([
    (
        "https://cintesis.eu/en/calls/research-fellowship-aging-2026/",
        "Research Fellowship – Aging and Dementia",
        "Open. Deadline 2027-01-31. Investigador / researcher.",
    ),
    (
        "https://cintesis.eu/en/calls/bolsa-doutoramento-2026/",
        "Bolsa de Doutoramento – Saúde Digital",
        "Candidaturas abertas. Prazo: 28 de fevereiro de 2027.",
    ),
])

CINTESIS_HTML_CLOSED = _html_with_links([
    (
        "https://cintesis.eu/en/calls/closed-call/",
        "Post-doctoral Researcher – Health Economics",
        "Call is closed. Recruitment process closed.",
    ),
])

CINTESIS_HTML_EXPIRED = _html_with_links([
    (
        "https://cintesis.eu/en/calls/expired-fellowship/",
        "Bolsa de Investigação – Oncologia",
        "Open. Application deadline 01/06/2019. Investigador.",
    ),
])


class CintesisTests(unittest.TestCase):

    def _run(self, html: str):
        with patch("academic_offers.sources.portugal_targets.fetch", return_value=html):
            return cintesis(today=TODAY)

    def test_open_offers_returned(self):
        offers = self._run(CINTESIS_HTML_OPEN)
        self.assertEqual(len(offers), 2)

    def test_offer_fields(self):
        offers = self._run(CINTESIS_HTML_OPEN)
        for o in offers:
            self.assertEqual(o.source, "cintesis")
            self.assertEqual(o.region, "Porto")
            self.assertIn("CINTESIS", o.institution)
        bolsa = next(o for o in offers if "Bolsa" in o.title)
        self.assertEqual(bolsa.kind, "call")

    def test_research_fellowship_is_call(self):
        offers = self._run(CINTESIS_HTML_OPEN)
        fellowship = next(o for o in offers if "Fellowship" in o.title)
        self.assertEqual(fellowship.kind, "call")

    def test_closed_offers_excluded(self):
        offers = self._run(CINTESIS_HTML_CLOSED)
        self.assertEqual(offers, [])

    def test_expired_deadline_excluded(self):
        offers = self._run(CINTESIS_HTML_EXPIRED)
        self.assertEqual(offers, [])

    def test_empty_html_returns_empty(self):
        offers = self._run("")
        self.assertEqual(offers, [])

    def test_fetch_error_returns_empty(self):
        with patch(
            "academic_offers.sources.portugal_targets.fetch",
            side_effect=Exception("connection refused"),
        ):
            offers = cintesis(today=TODAY)
        self.assertEqual(offers, [])


if __name__ == "__main__":
    unittest.main()
