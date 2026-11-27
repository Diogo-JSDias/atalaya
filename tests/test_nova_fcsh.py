"""Tests for the NOVA FCSH DRE-extract recruitment feed."""
import datetime as dt
import unittest

from academic_offers.sources.nova_fcsh import parse_listing, parse_notice_text


LISTING = """
<html><body>
<h1>CONCURSOS PARA INVESTIGADORES</h1>
<p>1 vaga de Investigador(a) Doutorado(a)</p>
<a href="/static/documentos/concursos/investigadores/Aviso%20%28extrato%29%20n.%C2%BA%2027999_2026_2.pdf">
  Aviso (Extrato) n.º 25498/2026/2
</a>
<a href="/static/documentos/concursos/investigadores/Aviso%20Integral%2025498.pdf">
  Aviso integral
</a>
<a href="https://example.org/Aviso%20%28extrato%29%20n.%C2%BA%2025555_2026_2.pdf">
  External extract
</a>
</body></html>
"""

EXPIRED_NOTICE = """
Aviso (extrato) n.º 25498/2026/2
15-10-2026
N.º 200
2.ª série
UNIVERSIDADE NOVA DE LISBOA
Faculdade de Ciências Sociais e Humanas
Sumário: Reabertura de procedimento concursal de seleção internacional para a contratação
de um/a investigador/a doutorado/a no âmbito do projeto estratégico do Centro de Estudos em Música.
Em cumprimento do disposto no artigo 11.º do Decreto-Lei n.º 57/2016, torna-se público que
se encontra aberto, pelo prazo de 10 dias úteis, a contar do dia útil imediato ao da presente
publicação, o procedimento concursal para contratação de 1 (um/a) Investigador/a Doutorado/a.
"""

FUTURE_NOTICE = """
Aviso (extrato) n.º 27999/2026/2
25-11-2026
N.º 228
2.ª série
UNIVERSIDADE NOVA DE LISBOA
Faculdade de Ciências Sociais e Humanas
Sumário: Abertura de procedimento concursal para contratação de Investigador Doutorado no
âmbito do projeto de investigação em Humanidades Digitais.
Em cumprimento do disposto no artigo 11.º do Decreto-Lei n.º 57/2016, torna-se público que
se encontra aberto, pelo prazo de 5 dias úteis, a contar do dia útil imediato ao da presente
publicação, o procedimento concursal para contratação de 2 (dois/duas) Investigadores/as Doutorados/as.
"""


class NOVAFCSHTests(unittest.TestCase):
    def test_extracts_publication_date_deadline_title_and_count(self):
        details = parse_notice_text(EXPIRED_NOTICE)
        self.assertEqual(details["publication_date"], "2026-10-15")
        self.assertEqual(details["deadline"], "2026-10-29")
        self.assertEqual(details["deadline_days"], 10)
        self.assertEqual(details["notice_number"], "25498/2026/2")
        self.assertIn("Centro de Estudos em Música", details["title"])
        self.assertEqual(details["vacancy_count"], 1)

    def test_current_offer_is_kept_until_deadline(self):
        pdf = b"future-notice"
        def fetcher(url):
            return pdf
        def extractor(data):
            self.assertEqual(data, pdf)
            return FUTURE_NOTICE

        offers = parse_listing(
            LISTING,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=fetcher,
            pdf_extractor=extractor,
        )
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer.source, "nova-fcsh")
        self.assertEqual(offer.deadline, "2026-12-03")
        self.assertEqual(offer.n_posts, 2)
        self.assertEqual(offer.extra["notice_number"], "27999/2026/2")
        self.assertEqual(
            offer.url,
            "https://www.fcsh.unl.pt/static/documentos/concursos/investigadores/Aviso%20%28extrato%29%20n.%C2%BA%2027999_2026_2.pdf",
        )

    def test_stale_faculty_listing_does_not_resurface_expired_call(self):
        offers = parse_listing(
            LISTING,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"old",
            pdf_extractor=lambda _data: EXPIRED_NOTICE,
        )
        self.assertEqual(offers, [])

    def test_does_not_infer_deadline_without_publication_date_or_period(self):
        incomplete = """
        Aviso (extrato) n.º 28000/2026/2
        Sumário: Concurso para Investigador Doutorado.
        Encontra-se aberto o concurso.
        """
        details = parse_notice_text(incomplete)
        self.assertIsNone(details["deadline"])
        offers = parse_listing(
            LISTING,
            today=dt.date(2026, 11, 27),
            pdf_fetcher=lambda _url: b"incomplete",
            pdf_extractor=lambda _data: incomplete,
        )
        self.assertEqual(offers, [])

    def test_official_extract_links_are_required(self):
        html = """
        <h1>Concursos para investigadores</h1>
        <a href="https://example.org/Aviso%20%28extrato%29.pdf">Extract</a>
        <a href="/static/documentos/concursos/investigadores/aviso-integral.pdf">Integral</a>
        """
        self.assertEqual(
            parse_listing(
                html,
                today=dt.date(2026, 11, 27),
                pdf_fetcher=lambda _url: b"",
                pdf_extractor=lambda _data: FUTURE_NOTICE,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
