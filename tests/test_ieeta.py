"""Offline tests for the IEETA source adapter."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import ieeta

SAMPLE_HTML = """
<html>
  <body>
    <article id="job-101" class="ieeta-jobcard">
      <h2 class="ieeta-jobcard__title">
        <a href="https://www.ieeta.pt/jobs/research-fellow-ai/">Research Fellow in AI</a>
      </h2>
      <dl>
        <dt>Application Deadline</dt>
        <dd>15/12/2026</dd>
      </dl>
    </article>
    <article id="job-102" class="ieeta-jobcard">
      <h2 class="ieeta-jobcard__title">
        <a href="/jobs/expired-position/">Expired Position</a>
      </h2>
      <dl>
        <dt>Application Deadline</dt>
        <dd>01/11/2026</dd>
      </dl>
    </article>
    <article id="job-103" class="ieeta-jobcard">
      <h2 class="ieeta-jobcard__title">
        <a href="https://example.com/external-job">External Host Job</a>
      </h2>
      <dl>
        <dt>Application Deadline</dt>
        <dd>2026-12-20</dd>
      </dl>
    </article>
    <article id="job-104" class="ieeta-jobcard">
      <h2 class="ieeta-jobcard__title">
        <a href="https://www.ua.pt/pt/noticias/concurso-ieeta">Assistant Researcher (UA)</a>
      </h2>
      <dl>
        <dt>Application Deadline:</dt>
        <dd>10/12/2026</dd>
      </dl>
    </article>
  </body>
</html>
"""


class IeetaTests(unittest.TestCase):
    def test_parse_listing_filters_expired_and_unofficial_urls(self):
        offers = ieeta.parse_listing(SAMPLE_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 2)

        first, second = offers
        self.assertEqual(first.source, "ieeta")
        self.assertEqual(first.title, "Research Fellow in AI")
        self.assertEqual(first.url, "https://www.ieeta.pt/jobs/research-fellow-ai/")
        self.assertEqual(first.institution, "IEETA – Universidade de Aveiro")
        self.assertEqual(first.region, "Centro")
        self.assertEqual(first.deadline, "2026-12-15")

        self.assertEqual(second.title, "Assistant Researcher (UA)")
        self.assertEqual(second.url, "https://www.ua.pt/pt/noticias/concurso-ieeta")
        self.assertEqual(second.deadline, "2026-12-10")

    def test_parse_listing_empty_html(self):
        self.assertEqual(ieeta.parse_listing("", today=dt.date(2026, 11, 27)), [])

    @patch("academic_offers.sources.ieeta.fetch", return_value=SAMPLE_HTML)
    def test_scrape_uses_fetch(self, mock_fetch):
        offers = ieeta.scrape(today=dt.date(2026, 11, 27))
        mock_fetch.assert_called_once_with(ieeta.LIST_URL)
        self.assertEqual(len(offers), 2)


if __name__ == "__main__":
    unittest.main()
