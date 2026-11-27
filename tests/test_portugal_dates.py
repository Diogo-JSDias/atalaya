"""Regression tests for Portuguese month names in deadline extraction."""
import unittest

from academic_offers.dates import first_date, lisbon_working_day_deadline
import datetime as dt


class PortugueseDateTests(unittest.TestCase):
    def test_portuguese_month(self):
        self.assertEqual(first_date("Candidaturas até 15 de março de 2027"), "2027-03-15")

    def test_portuguese_month_without_de(self):
        self.assertEqual(first_date("Prazo: 2 de outubro 2026"), "2026-10-02")

    def test_lisbon_working_day_deadline_excludes_public_holidays(self):
        self.assertEqual(
            lisbon_working_day_deadline(dt.date(2026, 11, 10), 30),
            dt.date(2026, 12, 23),
        )
        self.assertEqual(
            lisbon_working_day_deadline(dt.date(2026, 10, 16), 10),
            dt.date(2026, 10, 29),
        )

    def test_numeric_portuguese_date(self):
        self.assertEqual(first_date("Termina em 07/11/2026"), "2026-11-07")


if __name__ == "__main__":
    unittest.main()
