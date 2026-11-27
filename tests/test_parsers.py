"""Offline tests: parsing rules on small, real-shaped snippets. No network."""
import datetime as dt
import unittest
from unittest import mock

from academic_offers.classify import classify
from academic_offers.dates import date_after, first_date
from academic_offers.models import Offer
from academic_offers.sources import boe
from academic_offers.spain import add_days, easter, university

NOTICE = """<documento><texto><p>Resolución ... El plazo de presentación de solicitudes será de quince días hábiles,
contados a partir del día siguiente a la publicación.</p><p>ANEXO I Cuerpo de Profesores Titulares de Universidad
Plaza número: 152/2026. Área/especialidad de conocimiento: Física Aplicada. Departamento: Física.
Cuerpo: Catedrático/a de Universidad. Área de conocimiento: «Filología Inglesa». Departamento: Filología.</p>
<p>ANEXO II Comisión de Selección Área de conocimiento: Física Aplicada. Presidente Titular: Don X.</p></texto></documento>"""

ITEM = {"titulo": "Resolución de 6 de noviembre de 2026, de la Universidad de Murcia, por la que se convoca "
                  "concurso de acceso a plazas de cuerpos docentes universitarios.",
        "identificador": "BOE-A-TEST", "url_xml": "x", "url_html": "https://boe.es/x",
        "url_pdf": {"texto": "https://boe.es/x.pdf"}}


ITEM_HTML_URL = "https://www.boe.es/diario_boe/txt.php?id=BOE-A-TEST"


class BoeTests(unittest.TestCase):
    def test_splits_notice_into_areas_and_ignores_committee(self):
        with mock.patch.object(boe, "fetch", return_value=NOTICE):
            offers = boe.parse_notice(ITEM, dt.date(2026, 11, 16), "UNIVERSIDADES")
        got = {(o.area_raw, o.position_type, o.n_posts) for o in offers}
        self.assertEqual(got, {("Física Aplicada", "Profesor/a Titular de Universidad", 1),
                               ("Filología Inglesa", "Catedrático/a de Universidad", 1)})
        self.assertEqual(offers[0].region, "Región de Murcia")
        self.assertEqual(offers[0].deadline, "2026-12-07")  # 15 días hábiles, skipping 6 and 8 Dec
        self.assertTrue(offers[0].deadline_estimated)

    def test_title_filter(self):
        keep = "…por la que se convoca concurso de acceso a plazas de cuerpos docentes universitarios."
        drop = "…por la que se corrigen errores en la de 4 de noviembre, por la que se convoca concurso de acceso a plazas de cuerpos docentes universitarios."
        self.assertTrue(boe.KEEP.search(keep) and not boe.DROP.search(keep))
        self.assertTrue(boe.DROP.search(drop))

    def test_rejects_boilerplate_areas(self):
        for junk in ["y Departamento, así como su número", "Presidente Titular", "G032/D13262 Profesor",
                     "Universidad de Salamanca", "Área Asistencial Categoría"]:
            self.assertFalse(boe._looks_like_area(junk), junk)
        self.assertTrue(boe._looks_like_area("Ingeniería de Sistemas y Automática"))


class RobotsTests(unittest.TestCase):
    def test_boe_notice_url_is_allowed_by_boe_robots(self):
        """BOE disallows xml.php; we must read notices through txt.php (regression: 0 BOE items on GitHub)."""
        from urllib.robotparser import RobotFileParser
        rp = RobotFileParser()
        rp.parse(["User-agent: *", "Disallow: /diario_boe/xml.php?", "Disallow: /diario_boe/txt.php?*lang=en"])
        self.assertFalse(rp.can_fetch("AtalayaBot", "https://www.boe.es/diario_boe/xml.php?id=BOE-A-1"))
        self.assertTrue(rp.can_fetch("AtalayaBot", ITEM_HTML_URL))
        fetched = []
        with mock.patch.object(boe, "fetch", side_effect=lambda url, **k: fetched.append(url) or NOTICE):
            boe.parse_notice({**ITEM, "url_html": ITEM_HTML_URL}, dt.date(2026, 11, 16), "UNIVERSIDADES")
        self.assertEqual(fetched, [ITEM_HTML_URL])


class StoreTests(unittest.TestCase):
    def test_latest_run_wins_regardless_of_where_it_ran(self):
        """Regression: a laptop run stored in Madrid time looked 'newer' than a later GitHub run in UTC."""
        import sqlite3, tempfile, os
        from academic_offers import store
        with tempfile.TemporaryDirectory() as d:
            db = store.connect(os.path.join(d, "t.db"))
            a = Offer(source="crg", kind="position", title="Postdoc A", url="u1")
            b = Offer(source="crg", kind="position", title="Postdoc B", url="u2")
            with mock.patch("academic_offers.store.dt") as m:
                m.timezone, m.date = dt.timezone, dt.date
                m.datetime.now.return_value = dt.datetime(2026, 11, 27, 10, 17, tzinfo=dt.timezone.utc)
                store.save(db, {"crg": [a]}, dt.date(2026, 11, 27))
                m.datetime.now.return_value = dt.datetime(2026, 11, 27, 11, 1, tzinfo=dt.timezone.utc)
                store.save(db, {"crg": [a, b]}, dt.date(2026, 11, 27))
            titles = {o["title"] for o in store.current(db, dt.date(2026, 11, 27))}
            db.close()
            self.assertEqual(titles, {"Postdoc A", "Postdoc B"})


class SpainTests(unittest.TestCase):
    def test_easter(self):
        self.assertEqual(easter(2026), dt.date(2026, 4, 5))
        self.assertEqual(easter(2027), dt.date(2027, 3, 28))

    def test_business_days_with_regional_holidays(self):
        # 10 días hábiles from Thu 26 Feb 2026: Andalucía skips its 28 Feb (a Saturday anyway) → 12 Mar
        self.assertEqual(add_days(dt.date(2026, 2, 26), 10, True, "Andalucía"), dt.date(2026, 3, 12))
        # Catalonia: 24 June is a holiday there, not in Madrid
        self.assertEqual(add_days(dt.date(2026, 6, 22), 2, True, "Cataluña"), dt.date(2026, 6, 25))
        self.assertEqual(add_days(dt.date(2026, 6, 22), 2, True, "Madrid"), dt.date(2026, 6, 24))

    def test_natural_days_roll_to_next_working_day(self):
        self.assertEqual(add_days(dt.date(2026, 11, 26), 20, False), dt.date(2026, 12, 16))
        self.assertEqual(add_days(dt.date(2026, 11, 28), 8, False), dt.date(2026, 12, 7))  # 6 Dec is Sunday

    def test_university_lookup(self):
        self.assertEqual(university("de la Universitat Politècnica de València"),
                         ("Universitat Politècnica de València", "Comunitat Valenciana"))


class DateTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(first_date("Fin de la oferta: 03/12/2026 23:59"), "2026-12-03")
        self.assertEqual(first_date("hasta el 3 de diciembre de 2026"), "2026-12-03")
        self.assertEqual(first_date("by December 3 rd , 2026."), "2026-12-03")
        self.assertEqual(first_date("Deadline: 10th September 2026."), "2026-09-10")
        self.assertEqual(date_after("Published 01/11/2026. Deadline for applications : 10/12/2026", "deadline"),
                         "2026-12-10")


class CsicTests(unittest.TestCase):
    def test_window_rule_becomes_deadline(self):
        from academic_offers.sources import csic
        # 10 días hábiles from 22 Oct 2026 in Madrid: 23,26,27,28,29,30 Oct, 2,3,4,5 Nov (1 Nov is a Sunday)
        self.assertEqual(csic._deadline("10 días hábiles a partir del siguiente al 22-10-2026"), "2026-11-05")
        self.assertEqual(csic._deadline("Hasta el 15/12/2026"), "2026-12-15")


class ClassifyTests(unittest.TestCase):
    def check(self, area, field, sub):
        o = classify(Offer(source="t", kind="position", title=f"Plaza – {area}", url="u", area_raw=area))
        self.assertEqual((o.field, o.subfield), (field, sub), area)

    def test_overlapping_keywords(self):
        self.check("Educación Física y Deportiva", "Social Sciences", "Education")
        self.check("Química Física", "Physical Sciences & Engineering", "Chemistry")
        self.check("Física Atómica, Molecular y Nuclear", "Physical Sciences & Engineering", "Physics & Photonics")
        self.check("Fundamentos del Análisis Económico", "Social Sciences", "Economics & Business")
        self.check("Psicología Evolutiva y de la Educación", "Social Sciences", "Psychology")
        self.check("Medicina y Cirugía Animal", "Life & Health Sciences", "Agriculture, Food & Veterinary")
        self.check("Lenguajes y Sistemas Informáticos", "Physical Sciences & Engineering", "Computer Science & AI")

    def test_stage(self):
        o = classify(Offer(source="t", kind="position", title="Postdoctoral researcher in Molecular Biology", url="u"))
        self.assertEqual(o.stage, "Postdoc")


if __name__ == "__main__":
    unittest.main()
