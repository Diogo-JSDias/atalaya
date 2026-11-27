"""Offline regression tests for new Portuguese university and centre adapters."""
import datetime as dt
import unittest
from unittest.mock import patch
from academic_offers.sources import portugal_targets as pt


class PortugalTargetsTests(unittest.TestCase):
    def test_gimm_keeps_open_academic_jobs_and_deadlines(self):
        html = """
        <main><ul class="jobs">
          <li class="job"><a href="/jobs/postdoctoral-researcher/">Postdoctoral Researcher</a>
          <span>Lisbon open Opportunity closes at 02/12/2026</span></li>
          <li class="job"><a href="/jobs/closed-call/">Research Fellowship</a>
          <span>Closed Candidaturas encerradas a 20/11/2026</span></li>
          <li class="job"><a href="/jobs/admin/">Finance Officer</a><span>open</span></li>
        </ul></main>"""
        offers = pt.parse_link_board(
            html, base_url=pt.GIMM_URL, source="gimm",
            institution="GIMM", region="Lisboa",
            href_pattern=r"^/jobs/[^/?#]+/?$", domains=("gimm.pt",),
        )
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-12-02")
        self.assertEqual(offers[0].institution, "GIMM")

    def test_inl_jobvite_board_keeps_research_roles(self):
        html = """
        <main><div class="job"><a href="/inl/job/JR123">Postdoctoral Researcher – Nanophotonics</a>
          <span>Braga, Portugal</span></div>
          <div class="job"><a href="/inl/job/JR124">Finance Assistant</a></div>
        </main>"""
        offers = pt.parse_link_board(
            html, base_url=pt.INL_URL, source="inl", institution="INL",
            region="Braga", href_pattern=r"/inl/job/",
            domains=("jobvite.com",), open_listing=True,
        )
        self.assertEqual([o.title for o in offers], ["Postdoctoral Researcher – Nanophotonics"])

    def test_iscte_excludes_closed_and_keeps_open_deadline(self):
        html = """
        <main>
          <div class="job-card"><a href="/jobs/41">Investigador Doutorado</a>
          <p>Prazo de candidaturas até 04 de dezembro de 2026</p></div>
          <div class="job-card"><a href="/jobs/42">Investigador Auxiliar</a>
          <p>Candidaturas encerradas a 10 de novembro de 2026</p></div>
        </main>"""
        offers = pt.parse_link_board(
            html, base_url=pt.ISCTE_URL, source="iscte", institution="Iscte",
            region="Lisboa", href_pattern=r"/jobs/\d+",
            domains=("iscte-iul.pt",),
        )
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-12-04")

    def test_lip_requires_explicit_open_state(self):
        html = """
        <main>
          <div class="call"><a href="/calls/call/3">Assistant Researcher Hiring</a>
          <span>Open - Applications</span></div>
          <div class="call"><a href="/calls/call/4">Postdoctoral Researcher</a>
          <span>Closed</span></div>
        </main>"""
        offers = pt.parse_link_board(
            html, base_url=pt.LIP_URL, source="lip", institution="LIP",
            region="Portugal", href_pattern=r"/calls/call/\d+",
            domains=("lip.pt",), open_listing=True, require_open_marker=True,
        )
        self.assertEqual([o.title for o in offers], ["Assistant Researcher Hiring"])

    def test_lip_extracts_title_from_call_detail_and_requires_application_stage(self):
        html = "<main><h1>Call</h1><h3>Assistant Researcher Hiring</h3><p>Open - Applications</p></main>"
        with patch.object(pt, "fetch", return_value=html):
            offers = pt.lip(today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].title, "Assistant Researcher Hiring")

    def test_lip_excludes_calls_already_in_jury_selection(self):
        html = "<main><h1>Assistant Researcher Hiring</h1><p>Open - Jury Selection</p></main>"
        with patch.object(pt, "fetch", return_value=html):
            offers = pt.lip(today=dt.date(2026, 11, 27))
        self.assertEqual(offers, [])

    def test_ua_technical_portal_keeps_only_non_expired_research_support_roles(self):
        html = """
        <main><ul class="job-list">
          <li class="job"><a href="/Home/Detail/201">Contratação de Técnico Superior</a>
          <span>Candidaturas até 03-12-2026</span></li>
          <li class="job"><a href="/Home/Detail/202">Assistente Técnico</a>
          <span>Candidaturas até 03-10-2026</span></li>
        </ul></main>"""
        with patch.object(pt, "fetch", return_value=html):
            offers = pt.ua_technical(today=dt.date(2026, 11, 27))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-12-03")

    def test_ucp_table_uses_deadline_column_not_application_start(self):
        from unittest.mock import patch
        html = """
        <table><tr><th>Position</th><th>Requirements</th><th>Deadline</th><th>Status</th></tr>
        <tr><td><a href="/offer/assistant-professor">Assistant Professor in Economics</a></td>
        <td>PhD required</td><td>From 27/11/2026 to 10/12/2026 at 17:00</td><td>Open</td></tr>
        </table>"""
        with patch.object(pt, "fetch", return_value=html):
            offers = pt.uc_portuguesa(today=__import__("datetime").date(2026, 11, 27))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].deadline, "2026-12-10")

    def test_foreign_or_untrusted_links_are_rejected(self):
        html = '<main><div class="job"><a href="https://evil.example/jobs/1">Researcher</a></div></main>'
        offers = pt.parse_link_board(
            html, base_url=pt.GIMM_URL, source="gimm", institution="GIMM",
            region="Lisboa", href_pattern=r"/jobs/", domains=("gimm.pt",),
        )
        self.assertEqual(offers, [])


if __name__ == "__main__":
    unittest.main()
