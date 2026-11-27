"""Offline tests for the INESC-ID positions source."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources.inesc_id import LIST_URL, parse_listing, scrape

TODAY = dt.date(2026, 11, 27)

SAMPLE_HTML = """
<html>
<body>
  <div class="position-panels">
    <div class="position-panel open">
      <h3>Researcher in Distributed Systems</h3>
      <span class="position-type">PhD Researcher</span>
      <p>Reference: INESC-ID-2026-01</p>
      <p class="deadline">Application deadline: 15/12/2026</p>
      <a href="https://euraxess.ec.europa.eu/jobs/123456">Euraxess</a>
      <a href="https://example.com/other">Other</a>
    </div>
    <div class="position-panel open">
      <h3>Research Grant (BI) in Machine Learning</h3>
      <p>Ref.: BI-ML-2026</p>
      <p>Deadline: 30/11/2026</p>
    </div>
    <div class="position-panel closed">
      <h3>Expired Position</h3>
      <p>Reference: EXP-2026-01</p>
      <p>Deadline: 26/11/2026</p>
      <a href="https://www.inesc-id.pt/jobs/expired">Details</a>
    </div>
    <div class="position-panel open">
      <h3>DR Linked Position</h3>
      <p>Reference: DR-2026-99</p>
      <p>Deadline: 01/12/2026</p>
      <a href="https://diariodarepublica.pt/dr/detalhe/aviso/999">DR</a>
    </div>
  </div>
</body>
</html>
"""


class InescIdTests(unittest.TestCase):
    def test_parses_active_positions_and_filters_expired(self):
        offers = parse_listing(SAMPLE_HTML, today=TODAY)
        self.assertEqual(len(offers), 3)

        first = offers[0]
        self.assertEqual(first.source, "inesc-id")
        self.assertEqual(first.kind, "position")
        self.assertEqual(first.title, "Researcher in Distributed Systems")
        self.assertEqual(first.position_type, "PhD Researcher")
        self.assertEqual(first.url, "https://euraxess.ec.europa.eu/jobs/123456")
        self.assertEqual(first.institution, "INESC-ID")
        self.assertEqual(first.region, "Lisboa")
        self.assertEqual(first.deadline, "2026-12-15")
        self.assertEqual(first.extra["reference"], "INESC-ID-2026-01")

        second = offers[1]
        self.assertEqual(second.title, "Research Grant (BI) in Machine Learning")
        self.assertEqual(second.url, f"{LIST_URL}#BI-ML-2026")
        self.assertEqual(second.deadline, "2026-11-30")
        self.assertEqual(second.extra["reference"], "BI-ML-2026")

        third = offers[2]
        self.assertEqual(third.url, "https://diariodarepublica.pt/dr/detalhe/aviso/999")
        self.assertEqual(third.deadline, "2026-12-01")

    def test_empty_html_returns_empty_list(self):
        self.assertEqual(parse_listing("", today=TODAY), [])
        self.assertEqual(parse_listing("<html><body></body></html>", today=TODAY), [])

    @patch("academic_offers.sources.inesc_id.fetch", return_value=SAMPLE_HTML)
    def test_scrape_uses_fetch(self, mock_fetch):
        offers = scrape(today=TODAY)
        mock_fetch.assert_called_once_with(LIST_URL)
        self.assertEqual(len(offers), 3)

    @patch("academic_offers.sources.inesc_id.fetch", side_effect=RuntimeError("network error"))
    def test_scrape_handles_fetch_error(self, mock_fetch):
        self.assertEqual(scrape(today=TODAY), [])
        mock_fetch.assert_called_once_with(LIST_URL)


if __name__ == "__main__":
    unittest.main()
