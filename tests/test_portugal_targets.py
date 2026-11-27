"""Offline regression tests for new Portuguese university and centre adapters."""
import unittest
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
        <main><section class="job-list">
          <a href="/inl/job/JR123">Postdoctoral Researcher – Nanophotonics</a>
          <span>Braga, Portugal</span>
          <a href="/inl/job/JR124">Finance Assistant</a>
        </section></main>"""
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
          <span>Open - Jury Selection</span></div>
          <div class="call"><a href="/calls/call/4">Postdoctoral Researcher</a>
          <span>Closed</span></div>
        </main>"""
        offers = pt.parse_link_board(
            html, base_url=pt.LIP_URL, source="lip", institution="LIP",
            region="Portugal", href_pattern=r"/calls/call/\d+",
            domains=("lip.pt",), open_listing=True, require_open_marker=True,
        )
        self.assertEqual([o.title for o in offers], ["Assistant Researcher Hiring"])

    def test_foreign_or_untrusted_links_are_rejected(self):
        html = '<main><div class="job"><a href="https://evil.example/jobs/1">Researcher</a></div></main>'
        offers = pt.parse_link_board(
            html, base_url=pt.GIMM_URL, source="gimm", institution="GIMM",
            region="Lisboa", href_pattern=r"/jobs/", domains=("gimm.pt",),
        )
        self.assertEqual(offers, [])


if __name__ == "__main__":
    unittest.main()
