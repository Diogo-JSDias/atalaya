"""Tests for the active source scope of the Portuguese edition."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from academic_offers.__main__ import build_site
from academic_offers.sources import SOURCES


class PortugalEditionTests(unittest.TestCase):
    def test_only_portuguese_and_european_sources_are_active(self):
        self.assertEqual(
            {source.key for source in SOURCES},
            {"dr", "fct", "ulisboa", "uporto", "ualg", "uc-apply", "uminho", "uminho-eeg", "novafct-investigadores", "ubi-docentes", "ubi-investigadores", "nova-ims", "nova-fcsh", "ucp-medicina", "ucp-porto", "ucp-fch", "gimm", "inl", "iscte", "lip", "ua-investigacao", "ua-docentes", "ua-tecnico", "ucp-clsbe", "inesc-tec", "algoritmi", "ieeta", "inesc-id", "itqb-nova", "eu-ft"},
        )

    @patch("academic_offers.__main__.store.last_runs", return_value={})
    @patch("academic_offers.__main__.store.current")
    def test_build_site_excludes_inactive_spanish_history(self, current, _last_runs):
        current.return_value = [
            {"source": "boe", "id": "legacy-spanish", "title": "Old Spanish offer"},
            {"source": "dr", "id": "portuguese-dr", "title": "Aviso português"},
            {"source": "fct", "id": "portuguese-fct", "title": "Concurso FCT"},
            {"source": "ulisboa", "id": "ulisboa-offer", "title": "Oferta ULisboa"},
            {"source": "uporto", "id": "uporto-offer", "title": "Oferta U.Porto"},
            {"source": "ualg", "id": "ualg-offer", "title": "Oferta UAlg"},
            {"source": "uc-apply", "id": "coimbra-offer", "title": "Bolsa UC"},
            {"source": "uminho-eeg", "id": "uminho-offer", "title": "Oferta UMinho EEG"},
            {"source": "novafct-investigadores", "id": "novafct-offer", "title": "Oferta NOVA FCT"},
            {"source": "ubi-docentes", "id": "ubi-offer", "title": "Oferta UBI"},
            {"source": "ubi-investigadores", "id": "ubi-researcher-offer", "title": "Oferta UBI Investigador"},
            {"source": "nova-ims", "id": "nova-ims-offer", "title": "Oferta NOVA IMS"},
            {"source": "nova-fcsh", "id": "nova-fcsh-offer", "title": "Oferta NOVA FCSH"},
            {"source": "ucp-medicina", "id": "ucp-medicina-offer", "title": "Oferta Medicina UCP"},
            {"source": "gimm", "id": "gimm-offer", "title": "Oferta GIMM"},
            {"source": "inl", "id": "inl-offer", "title": "Oferta INL"},
            {"source": "iscte", "id": "iscte-offer", "title": "Oferta Iscte"},
            {"source": "lip", "id": "lip-offer", "title": "Oferta LIP"},
            {"source": "ua-investigacao", "id": "ua-offer", "title": "Oferta UA"},
            {"source": "ua-docentes", "id": "ua-docente", "title": "Oferta UA Docente"},
            {"source": "ua-tecnico", "id": "ua-tag", "title": "Oferta UA TAG"},
            {"source": "ucp-clsbe", "id": "ucp-offer", "title": "Oferta Católica"},
            {"source": "uminho", "id": "uminho-central-offer", "title": "Oferta UMinho"},
            {"source": "ucp-porto", "id": "ucp-porto-offer", "title": "Oferta UCP Porto"},
            {"source": "ucp-fch", "id": "ucp-fch-offer", "title": "Oferta UCP FCH"},
            {"source": "inesc-tec", "id": "inesc-tec-offer", "title": "Oferta INESC TEC"},
            {"source": "algoritmi", "id": "algoritmi-offer", "title": "Oferta ALGORITMI"},
            {"source": "ieeta", "id": "ieeta-offer", "title": "Oferta IEETA"},
            {"source": "inesc-id", "id": "inesc-id-offer", "title": "Oferta INESC-ID"},
            {"source": "itqb-nova", "id": "itqb-nova-offer", "title": "Oferta ITQB NOVA"},
            {"source": "eu-ft", "id": "european-call", "title": "ERC call"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            count = build_site(object(), dt.date(2026, 11, 27), Path(tmp))
            rows = json.loads((Path(tmp) / "offers.json").read_text(encoding="utf-8"))
        self.assertEqual(count, 30)
        self.assertEqual(
            {row["source"] for row in rows},
            {"dr", "fct", "ulisboa", "uporto", "ualg", "uc-apply", "uminho", "uminho-eeg", "novafct-investigadores", "ubi-docentes", "ubi-investigadores", "nova-ims", "nova-fcsh", "ucp-medicina", "ucp-porto", "ucp-fch", "gimm", "inl", "iscte", "lip", "ua-investigacao", "ua-docentes", "ua-tecnico", "ucp-clsbe", "inesc-tec", "algoritmi", "ieeta", "inesc-id", "itqb-nova", "eu-ft"},
        )
        self.assertFalse(any(row["id"] == "legacy-spanish" for row in rows))


if __name__ == "__main__":
    unittest.main()
