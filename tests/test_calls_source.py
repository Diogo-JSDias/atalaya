"""Offline unit tests for academic_offers.sources.calls."""
import unittest
from unittest.mock import patch

from academic_offers.sources.calls import (
    AEI_LIST,
    ICREA_CALLS,
    _en_date,
    aei_calls,
    icrea_calls,
)


AEI_LISTING_HTML = """
<html><body>
<ul>
  <li>
    <div class="views-field-title"><a href="/convocatorias/ryc-2026">Ramón y Cajal 2026</a></div>
    <span>Abierta</span>
  </li>
  <li>
    <div class="views-field-title"><a href="/convocatorias/fpu-2025">FPU 2025</a></div>
    <span>Cerrada</span>
  </li>
</ul>
</body></html>
"""

AEI_DETAIL_HTML = """
<html><body>
<h1>Ramón y Cajal 2026</h1>
<p>Plazos de solicitud: presentación desde el 10/01/2026 hasta el 15/02/2026.</p>
<p>Duración y ejecución del proyecto: fecha fin del proyecto 31/12/2028.</p>
</body></html>
"""


class CallsSourceTests(unittest.TestCase):
    def test_aei_calls_extracts_application_deadline_and_skips_closed(self):
        detail_url = "https://www.aei.gob.es/convocatorias/ryc-2026"
        pages = {
            AEI_LIST: AEI_LISTING_HTML,
            detail_url: AEI_DETAIL_HTML,
        }

        with patch("academic_offers.sources.calls.fetch", side_effect=lambda u: pages[u]) as mock_fetch:
            offers = aei_calls()

        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "aei")
        self.assertEqual(offer.title, "Ramón y Cajal 2026")
        self.assertEqual(offer.url, detail_url)
        self.assertEqual(offer.deadline, "2026-02-15")
        self.assertEqual(offer.notes, "Estado: Abierta")

    def test_aei_calls_handles_empty_html_and_detail_errors(self):
        with patch("academic_offers.sources.calls.fetch", return_value=""):
            self.assertEqual(aei_calls(), [])

        detail_url = "https://www.aei.gob.es/convocatorias/ryc-2026"

        def fake_fetch(url):
            if url == AEI_LIST:
                return AEI_LISTING_HTML
            raise RuntimeError("network error")

        with patch("academic_offers.sources.calls.fetch", side_effect=fake_fetch):
            offers = aei_calls()

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].url, detail_url)
        self.assertIsNone(offers[0].deadline)

    def test_en_date_parses_valid_and_rejects_invalid_dates(self):
        self.assertEqual(_en_date("Deadline: 10th September 2026"), "2026-09-10")
        self.assertEqual(_en_date("Submit by November 30th, 2026"), "2026-11-30")
        self.assertIsNone(_en_date("31st September 2026"))
        self.assertIsNone(_en_date("no date here"))

    def test_icrea_calls_with_year_and_fallback_when_years_empty(self):
        open_with_year = (
            "<html><body>"
            "<p>ICREA Call Rules 2026. Application deadline: 15th April 2026.</p>"
            "</body></html>"
        )
        with patch("academic_offers.sources.calls.fetch", return_value=open_with_year) as mock_fetch:
            offers = icrea_calls()

        mock_fetch.assert_called_once_with(ICREA_CALLS)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].title, "ICREA Research Professors call 2026")
        self.assertEqual(offers[0].deadline, "2026-04-15")

        open_without_year = "<html><body><p>Applications are currently open.</p></body></html>"
        with patch("academic_offers.sources.calls.fetch", return_value=open_without_year):
            fallback_offers = icrea_calls()

        self.assertEqual(len(fallback_offers), 1)
        self.assertEqual(fallback_offers[0].title, "ICREA Research Professors call")
        self.assertIsNone(fallback_offers[0].deadline)

    def test_icrea_calls_closed_states(self):
        closed_with_next = (
            "<html><body>"
            "<p>ICREA Call 2025 IS CLOSED. The next ICREA call will open in January 2027.</p>"
            "</body></html>"
        )
        with patch("academic_offers.sources.calls.fetch", return_value=closed_with_next):
            offers = icrea_calls()

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].title, "ICREA Research Professors call 2026 (upcoming)")
        self.assertEqual(offers[0].notes, "Next call will open in January 2027.")

        closed_only = "<html><body><p>ICREA Call 2025 IS CLOSED.</p></body></html>"
        with patch("academic_offers.sources.calls.fetch", return_value=closed_only):
            self.assertEqual(icrea_calls(), [])


if __name__ == "__main__":
    unittest.main()
