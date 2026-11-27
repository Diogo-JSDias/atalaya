"""Offline tests for the ITQB NOVA open positions source."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import itqb_nova

SAMPLE_HTML = """
<html>
  <body>
    <div id="all-open-positions" class="open-positions positions-table">
      <table>
        <thead>
          <tr>
            <th>Position</th>
            <th>Department</th>
            <th>Application period</th>
            <th>More info</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Postdoctoral Researcher in Structural Biology</td>
            <td>Biological Chemistry</td>
            <td>01/11/2026 - 15/12/2026</td>
            <td><a href="/jobs/postdoc-structural-biology">More info</a></td>
          </tr>
          <tr>
            <td>Research Technician (Biochemistry)</td>
            <td>Microbiology</td>
            <td>10 de novembro de 2026 a 27 de novembro de 2026</td>
            <td><a href="https://diariodarepublica.pt/dr/detalhe/aviso-12345">More info</a></td>
          </tr>
          <tr>
            <td>PhD Fellowship in Plant Sciences</td>
            <td>Plant Biology</td>
            <td>Open until filled</td>
            <td><a href="https://www.unl.pt/en/jobs/phd-plant">More info</a></td>
          </tr>
          <tr>
            <td>Expired Research Fellow</td>
            <td>Chemistry</td>
            <td>01/10/2026 - 20/10/2026</td>
            <td><a href="https://www.itqb.unl.pt/jobs/expired">More info</a></td>
          </tr>
          <tr>
            <td>Untrusted External Position</td>
            <td>External</td>
            <td>01/11/2026 - 20/12/2026</td>
            <td><a href="https://example.com/jobs/external">More info</a></td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


class ITQBNovaTests(unittest.TestCase):
    def test_parse_listing_extracts_valid_active_offers(self):
        offers = itqb_nova.parse_listing(SAMPLE_HTML, today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 3)

        first = offers[0]
        self.assertEqual(first.source, "itqb-nova")
        self.assertEqual(first.kind, "position")
        self.assertEqual(first.institution, "ITQB NOVA")
        self.assertEqual(first.region, "Lisboa")
        self.assertEqual(first.title, "Postdoctoral Researcher in Structural Biology")
        self.assertEqual(first.area_raw, "Biological Chemistry")
        self.assertEqual(first.deadline, "2026-12-15")
        self.assertEqual(first.url, "https://www.itqb.unl.pt/jobs/postdoc-structural-biology")

        second = offers[1]
        self.assertEqual(second.deadline, "2026-11-27")
        self.assertEqual(second.url, "https://diariodarepublica.pt/dr/detalhe/aviso-12345")

        third = offers[2]
        self.assertIsNone(third.deadline)
        self.assertEqual(third.url, "https://www.unl.pt/en/jobs/phd-plant")

    def test_parse_listing_returns_empty_when_table_missing(self):
        self.assertEqual(itqb_nova.parse_listing("<html><body></body></html>", today=dt.date(2026, 11, 27)), [])

    def test_scrape_uses_fetch_and_parses(self):
        with patch.object(itqb_nova, "fetch", return_value=SAMPLE_HTML) as mock_fetch:
            offers = itqb_nova.scrape(today=dt.date(2026, 11, 27))
        mock_fetch.assert_called_once_with(itqb_nova.LIST_URL)
        self.assertEqual(len(offers), 3)


if __name__ == "__main__":
    unittest.main()
