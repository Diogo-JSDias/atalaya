"""AI extraction path with the Anthropic client mocked: no network, no key, no cost."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from academic_offers import llm
from academic_offers.sources import boe

UNPARSEABLE = "<documento><texto><p>Se convocan las plazas que figuran en el anexo publicado en la web.</p></texto></documento>"
ITEM = {"titulo": "Resolución de 13 de noviembre de 2026, de la Universidad de Almería, por la que se convoca "
                  "concurso de acceso a plazas de cuerpos docentes universitarios.",
        "identificador": "BOE-A-LLM", "url_xml": "x", "url_html": "https://boe.es/x",
        "url_pdf": {"texto": "https://boe.es/x.pdf"}}


def fake_response(posts):
    return SimpleNamespace(
        stop_reason="end_turn", _request_id="req_test",
        content=[SimpleNamespace(type="text", text=json.dumps({"posts": posts}))],
        usage=SimpleNamespace(input_tokens=1000, output_tokens=100),
    )


class LlmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(llm, "CACHE", Path(self.tmp.name) / "cache.json"),
            mock.patch.object(llm, "_cache", None),
            mock.patch.object(llm, "_calls", 0),
            mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_fallback_turns_annex_into_offers_and_caches(self):
        posts = [{"area": "Fisioterapia", "category": "Profesor Titular de Universidad", "department": "Enfermería",
                  "n_posts": 2},
                 {"area": "Ecología", "category": "Catedrático de Universidad", "department": "Biología", "n_posts": 1}]
        client = mock.MagicMock()
        client.messages.create.return_value = fake_response(posts)
        with mock.patch("anthropic.Anthropic", return_value=client), \
             mock.patch.object(boe, "fetch", return_value=UNPARSEABLE):
            offers = boe.parse_notice(ITEM, dt.date(2026, 11, 16), "UNIVERSIDADES")
            again = boe.parse_notice(ITEM, dt.date(2026, 11, 16), "UNIVERSIDADES")

        got = {(o.area_raw, o.position_type, o.n_posts) for o in offers}
        self.assertEqual(got, {("Fisioterapia", "Profesor/a Titular de Universidad", 2),
                               ("Ecología", "Catedrático/a de Universidad", 1)})
        self.assertIn("IA", offers[0].notes)
        self.assertEqual(len(again), 2)
        client.messages.create.assert_called_once()  # second parse came from the cache
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], llm.MODEL)
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")

    def test_without_key_keeps_single_entry(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(boe, "fetch", return_value=UNPARSEABLE):
            offers = boe.parse_notice(ITEM, dt.date(2026, 11, 16), "UNIVERSIDADES")
        self.assertEqual(len(offers), 1)
        self.assertIn("ver convocatoria", offers[0].notes)

    def test_refusal_or_truncation_is_not_cached(self):
        client = mock.MagicMock()
        client.messages.create.return_value = SimpleNamespace(stop_reason="max_tokens", _request_id="r", content=[])
        with mock.patch("anthropic.Anthropic", return_value=client):
            self.assertIsNone(llm.extract_posts("K", "t", "text"))
        self.assertFalse(llm.CACHE.exists())


if __name__ == "__main__":
    unittest.main()
