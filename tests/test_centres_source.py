"""Offline unit tests for academic_offers.sources.centres."""
import unittest
from unittest.mock import patch

from academic_offers.sources.centres import _from_links


LIST_URL = "https://example.org/jobs"
SELECTOR = 'a[href*="/position/"]'

LISTING_HTML = """
<html><body>
  <a href="/position/1">Postdoc Short</a>
  <a href="/position/1">Duplicate Postdoc</a>
  <a href="/position/2"></a>
  <a href="/position/3">Senior Researcher</a>
  <a href="/position/4/apply">Apply now</a>
  <a href="/position/general-application">General application</a>
</body></html>
"""

DETAIL_PAGES = {
    LIST_URL: LISTING_HTML,
    "https://example.org/position/1": (
        "<html><body><h1>Postdoctoral Researcher in Genomics</h1>"
        "<p>Submit your application by 20/05/2026.</p></body></html>"
    ),
    "https://example.org/position/2": (
        "<html><body><p>No heading and empty anchor text.</p></body></html>"
    ),
    "https://example.org/position/3": (
        "<html><body><p>Deadline: 15 de junio de 2026.</p></body></html>"
    ),
}


class CentresSourceTests(unittest.TestCase):
    def test_from_links_extracts_valid_offers_and_skips_empty_titles(self):
        with patch("academic_offers.sources.centres.fetch", side_effect=lambda u: DETAIL_PAGES[u]) as mock_fetch:
            offers = _from_links(
                "crg",
                LIST_URL,
                SELECTOR,
                "CRG",
                "Cataluña",
                "Genomics & biomedicine",
            )

        self.assertEqual(mock_fetch.call_count, 4)
        self.assertEqual(len(offers), 2)

        self.assertEqual(offers[0].source, "crg")
        self.assertEqual(offers[0].title, "Postdoctoral Researcher in Genomics")
        self.assertEqual(offers[0].url, "https://example.org/position/1")
        self.assertEqual(offers[0].deadline, "2026-05-20")

        self.assertEqual(offers[1].title, "Senior Researcher")
        self.assertEqual(offers[1].url, "https://example.org/position/3")
        self.assertEqual(offers[1].deadline, "2026-06-15")

    def test_from_links_handles_empty_html(self):
        with patch("academic_offers.sources.centres.fetch", return_value=""):
            offers = _from_links(
                "crg",
                LIST_URL,
                SELECTOR,
                "CRG",
                "Cataluña",
                "Genomics & biomedicine",
            )
        self.assertEqual(offers, [])

    def test_from_links_handles_detail_fetch_error_gracefully(self):
        def fake_fetch(url):
            if url == LIST_URL:
                return '<a href="/position/1">Fallback Title</a><a href="/position/2"></a>'
            raise RuntimeError("network error")

        with patch("academic_offers.sources.centres.fetch", side_effect=fake_fetch):
            offers = _from_links(
                "crg",
                LIST_URL,
                SELECTOR,
                "CRG",
                "Cataluña",
                "Genomics & biomedicine",
            )

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].title, "Fallback Title")
        self.assertIsNone(offers[0].deadline)


if __name__ == "__main__":
    unittest.main()
