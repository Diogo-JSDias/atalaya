"""Offline tests for the INESC TEC Strapi JSON source."""
import datetime as dt
import json
import unittest
from unittest.mock import patch

from academic_offers.sources.inesc_tec import (
    API_URL,
    OPPORTUNITY_BASE_URL,
    parse_opportunities,
    scrape,
)


TODAY = dt.date(2026, 11, 27)

SAMPLE_PAYLOAD = {
    "data": [
        {
            "id": 29194,
            "documentId": "liwc43o1tblpfyccaululyee",
            "iris_id": "AE2026-0305",
            "application_start": "2026-11-23",
            "application_end": "2026-12-07",
            "location": "",
            "pdf_url": "https://repositorio.inesctec.pt/editais/pt/AE2026-0305",
            "position": {
                "description": "Investigação (BI)",
                "is_grant": True,
            },
            "structure": {
                "name": "Sistemas de Computação e Comunicação",
            },
        },
        {
            "id": 29200,
            "documentId": "abc123activeposition",
            "iris_id": "AE2026-0310",
            "application_start": "2026-11-20",
            "application_end": "2026-11-27",
            "location": "Porto",
            "position": {
                "description": "Investigador Auxiliar",
                "is_grant": False,
            },
            "structure": {
                "name": "Sistemas de Energia",
            },
        },
        {
            "id": 29100,
            "documentId": "expired999docid",
            "iris_id": "AE2026-0200",
            "application_start": "2026-10-01",
            "application_end": "2026-11-26",
            "location": "Braga",
            "position": {
                "description": "Investigação (BI)",
                "is_grant": True,
            },
            "structure": {
                "name": "Robótica Industrial",
            },
        },
        {
            "id": 29101,
            "documentId": "missingtitle001",
            "application_start": "2026-11-01",
            "application_end": "2026-12-10",
            "position": {},
            "structure": {"name": "Ciência de Dados"},
        },
    ],
    "meta": {
        "pagination": {
            "page": 1,
            "pageSize": 25,
            "pageCount": 1,
            "total": 4,
        }
    },
}


class InescTecTests(unittest.TestCase):
    def test_parses_active_offers_and_skips_expired_or_incomplete(self):
        offers = parse_opportunities(SAMPLE_PAYLOAD, today=TODAY)
        self.assertEqual(len(offers), 2)

        first = offers[0]
        self.assertEqual(first.source, "inesc-tec")
        self.assertEqual(first.kind, "position")
        self.assertEqual(first.title, "Investigação (BI)")
        self.assertEqual(first.url, f"{OPPORTUNITY_BASE_URL}/liwc43o1tblpfyccaululyee")
        self.assertEqual(first.institution, "INESC TEC")
        self.assertEqual(first.region, "Norte")
        self.assertEqual(first.deadline, "2026-12-07")
        self.assertEqual(first.published, "2026-11-23")
        self.assertEqual(first.position_type, "Grant")
        self.assertEqual(first.area_raw, "Sistemas de Computação e Comunicação")
        self.assertEqual(first.extra["iris_id"], "AE2026-0305")
        self.assertEqual(
            first.extra["pdf_url"],
            "https://repositorio.inesctec.pt/editais/pt/AE2026-0305",
        )

        second = offers[1]
        self.assertEqual(second.title, "Investigador Auxiliar")
        self.assertEqual(second.region, "Porto")
        self.assertEqual(second.deadline, "2026-11-27")
        self.assertEqual(second.position_type, "Position")
        self.assertEqual(second.area_raw, "Sistemas de Energia")

    def test_skips_invalid_document_ids_and_empty_payloads(self):
        self.assertEqual(parse_opportunities({}, today=TODAY), [])
        self.assertEqual(parse_opportunities({"data": []}, today=TODAY), [])
        self.assertEqual(parse_opportunities({"data": None}, today=TODAY), [])

        bad_doc = {
            "data": [
                {
                    "documentId": "../evil",
                    "application_end": "2026-12-10",
                    "position": {"description": "Investigação (BI)", "is_grant": True},
                }
            ]
        }
        self.assertEqual(parse_opportunities(bad_doc, today=TODAY), [])

    def test_scrape_uses_fetch_and_handles_pagination(self):
        page1 = {
            "data": [SAMPLE_PAYLOAD["data"][0]],
            "meta": {"pagination": {"page": 1, "pageSize": 1, "pageCount": 2, "total": 2}},
        }
        page2 = {
            "data": [SAMPLE_PAYLOAD["data"][1]],
            "meta": {"pagination": {"page": 2, "pageSize": 1, "pageCount": 2, "total": 2}},
        }

        expected_p1 = f"{API_URL}?filters[application_end][$gte]=2026-11-27&populate=*"
        expected_p2 = f"{expected_p1}&pagination[page]=2"

        with patch(
            "academic_offers.sources.inesc_tec.fetch",
            side_effect=[json.dumps(page1), json.dumps(page2)],
        ) as mock_fetch:
            offers = scrape(today=TODAY)

        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(mock_fetch.call_args_list[0].args[0], expected_p1)
        self.assertEqual(mock_fetch.call_args_list[1].args[0], expected_p2)
        self.assertEqual(len(offers), 2)
        self.assertEqual(
            [o.url for o in offers],
            [
                f"{OPPORTUNITY_BASE_URL}/liwc43o1tblpfyccaululyee",
                f"{OPPORTUNITY_BASE_URL}/abc123activeposition",
            ],
        )

    def test_scrape_handles_invalid_json_gracefully(self):
        with patch("academic_offers.sources.inesc_tec.fetch", return_value="not json"):
            self.assertEqual(scrape(today=TODAY), [])


if __name__ == "__main__":
    unittest.main()
