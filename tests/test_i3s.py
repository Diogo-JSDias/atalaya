"""Offline tests for the official i3S recruitment adapter."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import i3s


def _card(title, reference, deadline, *, area="Life Sciences - Life Sciences", extra=""):
    return f"""
    <article class="job-opportunity">
      <h3>{title}</h3>
      <p>Area: {area}</p>
      <p>Salary Range: € 1.090,98</p>
      <p>Reference: {reference}</p>
      <p>Institution: Instituto de Investigação e Inovação em Saúde - Universidade do Porto</p>
      <p>Submission Open: 26.11.16</p>
      <p>Submission Deadline: {deadline}</p>
      {extra}
      <a href="https://dozer.i3s.up.pt/fileupload/downloadfile/viewpdfnewtab/en-{reference}">Job Description [EN]</a>
      <a href="https://dozer.i3s.up.pt/fileupload/downloadfile/viewpdfnewtab/pt-{reference}">Edital [PT]</a>
      <a href="https://dozer.i3s.up.pt/applicationmanagement/">Apply</a>
    </article>
    """


class I3SSourceTests(unittest.TestCase):
    def test_keeps_open_calls_and_uses_the_specific_english_notice(self):
        html = f"""
        <main>
          <h1>Job Opportunities</h1>
          <h2>Open Positions</h2>
          {_card(
              "BOLSA DE INVESTIGAÇÃO<br>Bolseiro/Fellow",
              "Fellow_BI/COM_Proj2025/i3S/16112711/2026",
              "26.11.27",
          )}
          {_card(
              "Junior Researcher",
              "Researcher/COMPETE2030/i3S/1611/2026",
              "26.11.29",
              area="Neurosciences - Neurobiology",
          )}
          {_card(
              "Research Technician",
              "Researcher/OLD/i3S/0111/2026",
              "26.11.26",
          )}
          {_card(
              "Research Technician",
              "Researcher/CLOSED/i3S/0111/2026",
              "26.12.09",
              extra="<p>Call closed</p>",
          )}
        </main>
        """
        offers = i3s.parse(html, today=dt.date(2026, 11, 27))

        self.assertEqual(len(offers), 2)
        fellowship, researcher = offers
        self.assertEqual(fellowship.kind, "call")
        self.assertEqual(fellowship.title, "Bolsa de Investigação – Bolseiro/Fellow")
        self.assertEqual(fellowship.deadline, "2026-11-27")
        self.assertEqual(fellowship.extra["submission_open"], "2026-11-16")
        self.assertIn("/en-Fellow_BI/", fellowship.url)
        self.assertEqual(fellowship.extra["reference"], "Fellow_BI/COM_Proj2025/i3S/16112711/2026")

        self.assertEqual(researcher.kind, "position")
        self.assertEqual(researcher.title, "Junior Researcher")
        self.assertEqual(researcher.area_raw, "Neurosciences - Neurobiology")
        self.assertEqual(researcher.deadline, "2026-11-29")
        self.assertEqual(researcher.institution, "i3S – Instituto de Investigação e Inovação em Saúde da Universidade do Porto")

    def test_expired_deadlines_are_excluded_but_deadline_today_is_included(self):
        html = f"""
        <main>
          {_card("Research Technician", "Ref/Today/2026", "26.11.27")}
          {_card("Research Technician", "Ref/Past/2026", "26.11.26")}
        </main>
        """
        offers = i3s.parse(html, today=dt.date(2026, 11, 27))
        self.assertEqual([offer.extra["reference"] for offer in offers], ["Ref/Today/2026"])

    def test_missing_deadline_on_a_vacancy_fails_visibly(self):
        html = """
        <main>
          <article>
            <h3>Junior Researcher</h3>
            <p>Reference: Researcher/MISSING/i3S/2026</p>
            <p>Submission Deadline: to be announced</p>
            <a href="https://dozer.i3s.up.pt/fileupload/downloadfile/viewpdfnewtab/missing">Job Description [EN]</a>
          </article>
        </main>
        """
        with self.assertRaisesRegex(RuntimeError, "application deadline"):
            i3s.parse(html, today=dt.date(2026, 11, 27))

    def test_metadata_without_official_notice_link_fails_visibly(self):
        html = """
        <main>
          <h2>Open Positions</h2>
          <p>Reference: Researcher/NO-PDF/i3S/2026</p>
          <p>Submission Deadline: 26.12.04</p>
        </main>
        """
        with self.assertRaisesRegex(RuntimeError, "no official PDF links"):
            i3s.parse(html, today=dt.date(2026, 11, 27))

    def test_empty_open_positions_page_is_valid(self):
        self.assertEqual(
            i3s.parse("<main><h1>Job Opportunities</h1><h2>Open Positions</h2></main>"),
            [],
        )

    @patch("academic_offers.sources.i3s.fetch")
    def test_scrape_fetches_the_official_listing(self, fetch_mock):
        fetch_mock.return_value = _card(
            "Junior Researcher", "Researcher/TEST/i3S/2026", "26.12.04"
        )
        offers = i3s.scrape(today=dt.date(2026, 11, 27))
        fetch_mock.assert_called_once_with(i3s.LIST_URL)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].source, "i3s")


if __name__ == "__main__":
    unittest.main()
