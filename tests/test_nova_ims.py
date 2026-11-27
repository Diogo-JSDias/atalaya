"""Tests for the NOVA IMS PDF-backed recruitment board."""
import datetime as dt
import unittest
from unittest.mock import patch

from academic_offers.sources import nova_ims as nova


HTML = """
<main>
<section class="job">
  <h3>Bolsa de Investigação para dois Alunos de Doutoramento - IMS_BOLSA_CHOICE_2026_02</h3>
  <ul>
    <li>Instituição: NOVA IMS</li>
    <li>Função a desempenhar: Bolsa de Investigação para dois Alunos de Doutoramento - IMS_BOLSA_CHOICE_2026_02</li>
    <li>Descrição das funções: Vide Edital</li>
    <li>Ficheiro(s) para consulta, relativos à oferta:
      <a href="/media/choice.pdf">IMS_BOLSA_CHOICE_2026_02</a>
    </li>
  </ul>
</section>
<section class="job">
  <h3>Professor/a Auxiliar na área disciplinar de Sistemas de Informação</h3>
  <ul>
    <li>Instituição: NOVA IMS</li>
    <li>Função a desempenhar: Professor/a Auxiliar na área disciplinar de Sistemas de Informação</li>
    <li>Descrição das funções: Vide Edital</li>
    <li>Ficheiro(s) para consulta, relativos à oferta:
      <a href="/media/edital-1419.pdf">Edital n.º 1419/2026</a>
    </li>
  </ul>
</section>
<section class="job">
  <h3>Manifestação de Interesse área disciplinar de Ciência de Dados para Marketing</h3>
  <ul>
    <li>Instituição: NOVA IMS</li>
    <li>Função a desempenhar: Professor/a Auxiliar Convidado/a em Data Science for Marketing</li>
    <li>Descrição das funções: Vide Edital</li>
    <li>Ficheiro(s) para consulta, relativos à oferta:
      <a href="/media/interest.pdf">Data Science for Marketing</a>
    </li>
  </ul>
</section>
<section class="job">
  <h3>Bolsa de Investigação antiga</h3>
  <ul>
    <li>Instituição: NOVA IMS</li>
    <li>Função a desempenhar: Bolsa de Investigação antiga</li>
    <li>Descrição das funções: Vide Edital</li>
    <li>Ficheiro(s) para consulta, relativos à oferta:
      <a href="/media/expired.pdf">Aviso antigo</a>
    </li>
  </ul>
</section>
</main>
"""


class NOVAIMSTests(unittest.TestCase):
    def _parse(self, today=dt.date(2026, 11, 27)):
        pdf_text = {
            b"choice": (
                "Aviso de Abertura do Concurso IMS_BOLSA_CHOICE_2026_02 "
                "8. Prazo de Candidatura O concurso encontra-se aberto entre "
                "o dia 20 de novembro de 2026 e as 20h00 do dia 7 de dezembro de 2026."
            ),
            b"faculty": (
                "Edital n.º 1419/2026 09-11-2026 UNIVERSIDADE NOVA DE LISBOA "
                "está aberto concurso documental pelo prazo de 30 dias úteis, "
                "a contar do dia imediato ao da publicação deste Edital no Diário da República."
            ),
            b"interest": (
                "Faculty Position Assistant Professor. Expression of interest. "
                "The position is to be filled at NOVA IMS."
            ),
            b"expired": (
                "Prazo de Candidatura O concurso encontra-se aberto entre "
                "o dia 1 de outubro de 2026 e o dia 20 de outubro de 2026."
            ),
        }
        def bytes_for(url):
            return {
                "https://novaims.unl.pt/media/choice.pdf": b"choice",
                "https://novaims.unl.pt/media/edital-1419.pdf": b"faculty",
                "https://novaims.unl.pt/media/interest.pdf": b"interest",
                "https://novaims.unl.pt/media/expired.pdf": b"expired",
            }[url]
        with patch.object(nova, "fetch_bytes", side_effect=bytes_for), patch.object(
            nova, "extract_pdf_text", side_effect=lambda data: pdf_text[data]
        ):
            return nova.parse_listing(HTML, today=today)

    def test_extracts_scholarship_explicit_deadline(self):
        offers = self._parse()
        choice = next(o for o in offers if "CHOICE" in o.title)
        self.assertEqual(choice.deadline, "2026-12-07")
        self.assertEqual(choice.kind, "call")
        self.assertEqual(choice.institution, "Universidade NOVA de Lisboa – NOVA IMS")

    def test_calculates_public_notice_working_day_deadline(self):
        offers = self._parse()
        faculty = next(o for o in offers if "Sistemas de Informação" in o.title)
        self.assertEqual(faculty.deadline, "2026-12-23")
        self.assertEqual(faculty.extra["deadline_basis"], "working-days")
        self.assertIn("Prazo calculado", faculty.notes)

    def test_keeps_rolling_expression_of_interest_without_inventing_deadline(self):
        offers = self._parse()
        interest = next(o for o in offers if "Data Science for Marketing" in o.title)
        self.assertIsNone(interest.deadline)
        self.assertIn("Manifestação de interesse", interest.notes)

    def test_filters_expired_pdf_notices(self):
        offers = self._parse(today=dt.date(2026, 11, 27))
        self.assertFalse(any("antiga" in o.title for o in offers))

    def test_business_day_count_excludes_weekends_and_lisbon_holidays(self):
        self.assertEqual(
            nova._add_business_days(dt.date(2026, 11, 10), 30),
            dt.date(2026, 12, 23),
        )

    def test_external_pdf_is_rejected(self):
        html = """
        <main><section class="job">
        <h3>Research Assistant</h3>
        <p>Instituição: NOVA IMS</p>
        <p>Função a desempenhar: Research Assistant</p>
        <a href="https://example.org/call.pdf">Notice</a>
        </section></main>
        """
        self.assertEqual(nova.parse_listing(html), [])


if __name__ == "__main__":
    unittest.main()
