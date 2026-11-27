"""Spain-specific helpers: university → region, business-day deadlines, Spanish number words."""
from __future__ import annotations

import datetime as dt
import re

# Keyword found in the institution name → (short name, Comunidad autónoma)
UNIVERSITIES = [
    ("Almería", "Universidad de Almería", "Andalucía"),
    ("Cádiz", "Universidad de Cádiz", "Andalucía"),
    ("Córdoba", "Universidad de Córdoba", "Andalucía"),
    ("Granada", "Universidad de Granada", "Andalucía"),
    ("Huelva", "Universidad de Huelva", "Andalucía"),
    ("Jaén", "Universidad de Jaén", "Andalucía"),
    ("Málaga", "Universidad de Málaga", "Andalucía"),
    ("Pablo de Olavide", "Universidad Pablo de Olavide", "Andalucía"),
    ("Sevilla", "Universidad de Sevilla", "Andalucía"),
    ("Internacional de Andalucía", "UNIA", "Andalucía"),
    ("Zaragoza", "Universidad de Zaragoza", "Aragón"),
    ("Oviedo", "Universidad de Oviedo", "Asturias"),
    ("Illes Balears", "Universitat de les Illes Balears", "Illes Balears"),
    ("Islas Baleares", "Universitat de les Illes Balears", "Illes Balears"),
    ("La Laguna", "Universidad de La Laguna", "Canarias"),
    ("Las Palmas", "Universidad de Las Palmas de Gran Canaria", "Canarias"),
    ("Cantabria", "Universidad de Cantabria", "Cantabria"),
    ("Castilla-La Mancha", "Universidad de Castilla-La Mancha", "Castilla-La Mancha"),
    ("Burgos", "Universidad de Burgos", "Castilla y León"),
    ("León", "Universidad de León", "Castilla y León"),
    ("Salamanca", "Universidad de Salamanca", "Castilla y León"),
    ("Valladolid", "Universidad de Valladolid", "Castilla y León"),
    ("Autònoma de Barcelona", "Universitat Autònoma de Barcelona", "Cataluña"),
    ("Autónoma de Barcelona", "Universitat Autònoma de Barcelona", "Cataluña"),
    ("Politècnica de Catalunya", "Universitat Politècnica de Catalunya", "Cataluña"),
    ("Politécnica de Cataluña", "Universitat Politècnica de Catalunya", "Cataluña"),
    ("Pompeu Fabra", "Universitat Pompeu Fabra", "Cataluña"),
    ("Girona", "Universitat de Girona", "Cataluña"),
    ("Lleida", "Universitat de Lleida", "Cataluña"),
    ("Rovira i Virgili", "Universitat Rovira i Virgili", "Cataluña"),
    ("Universitat de Barcelona", "Universitat de Barcelona", "Cataluña"),
    ("Universidad de Barcelona", "Universitat de Barcelona", "Cataluña"),
    ("Alicante", "Universidad de Alicante", "Comunitat Valenciana"),
    ("Jaume I", "Universitat Jaume I", "Comunitat Valenciana"),
    ("Miguel Hernández", "Universidad Miguel Hernández", "Comunitat Valenciana"),
    ("Politècnica de València", "Universitat Politècnica de València", "Comunitat Valenciana"),
    ("Politécnica de Valencia", "Universitat Politècnica de València", "Comunitat Valenciana"),
    ("Universitat de València", "Universitat de València", "Comunitat Valenciana"),
    ("Extremadura", "Universidad de Extremadura", "Extremadura"),
    ("A Coruña", "Universidade da Coruña", "Galicia"),
    ("Santiago de Compostela", "Universidade de Santiago de Compostela", "Galicia"),
    ("Vigo", "Universidade de Vigo", "Galicia"),
    ("La Rioja", "Universidad de La Rioja", "La Rioja"),
    ("Alcalá", "Universidad de Alcalá", "Madrid"),
    ("Autónoma de Madrid", "Universidad Autónoma de Madrid", "Madrid"),
    ("Carlos III", "Universidad Carlos III de Madrid", "Madrid"),
    ("Complutense", "Universidad Complutense de Madrid", "Madrid"),
    ("Politécnica de Madrid", "Universidad Politécnica de Madrid", "Madrid"),
    ("Rey Juan Carlos", "Universidad Rey Juan Carlos", "Madrid"),
    ("Educación a Distancia", "UNED", "Madrid"),
    ("Menéndez Pelayo", "UIMP", "Madrid"),
    ("Murcia", "Universidad de Murcia", "Región de Murcia"),
    ("Politécnica de Cartagena", "Universidad Politécnica de Cartagena", "Región de Murcia"),
    ("Pública de Navarra", "Universidad Pública de Navarra", "Navarra"),
    ("País Vasco", "Universidad del País Vasco/EHU", "País Vasco"),
]


def university(text: str) -> tuple[str, str]:
    for key, name, region in UNIVERSITIES:
        if key in text:
            return name, region
    m = re.search(r"(Universi(?:dad|tat|dade)[^,.]*)", text)
    return (m.group(1).strip() if m else ""), ""


NUMBER_WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciséis": 16, "veinte": 20, "veinticinco": 25,
    "treinta": 30, "cuarenta": 40, "cuarenta y cinco": 45,
}


def to_int(word: str) -> int | None:
    word = word.strip().lower()
    if word.isdigit():
        return int(word)
    return NUMBER_WORDS.get(word)


# Holidays for deadline maths. National fixed dates + Easter, plus each region's usual holidays.
# Regions move some holidays between years and local holidays are ignored, so computed deadlines
# remain flagged as estimates on the site.
_NATIONAL = {(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)}
_REGIONAL = {
    "Andalucía": {(2, 28)}, "Aragón": {(4, 23)}, "Asturias": {(9, 8)}, "Illes Balears": {(3, 1)},
    "Canarias": {(5, 30)}, "Cantabria": {(7, 28)}, "Castilla-La Mancha": {(5, 31)},
    "Castilla y León": {(4, 23)}, "Cataluña": {(6, 24), (9, 11), (12, 26)},
    "Comunitat Valenciana": {(3, 19), (6, 24), (10, 9)}, "Extremadura": {(9, 8)},
    "Galicia": {(5, 17), (7, 25)}, "La Rioja": {(6, 9)}, "Madrid": {(5, 2)},
    "Región de Murcia": {(6, 9)}, "Navarra": {(12, 3)}, "País Vasco": {(7, 25)},
}
_NO_HOLY_THURSDAY = {"Cataluña", "Comunitat Valenciana"}
_EASTER_MONDAY = {"Cataluña", "Comunitat Valenciana", "País Vasco", "Navarra", "Illes Balears", "La Rioja"}


def easter(year: int) -> dt.date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(year, month, day)


def is_holiday(d: dt.date, region: str = "") -> bool:
    if (d.month, d.day) in _NATIONAL or (d.month, d.day) in _REGIONAL.get(region, set()):
        return True
    e = easter(d.year)
    if d == e - dt.timedelta(days=2):  # Good Friday, national
        return True
    if d == e - dt.timedelta(days=3) and region not in _NO_HOLY_THURSDAY:
        return True
    return d == e + dt.timedelta(days=1) and region in _EASTER_MONDAY


def _working(d: dt.date, region: str = "") -> bool:
    return d.weekday() < 5 and not is_holiday(d, region)


def add_days(start: dt.date, n: int, business: bool, region: str = "") -> dt.date:
    """Deadline counted from the day after `start` (Ley 39/2015, art. 30)."""
    d = start
    if business:
        counted = 0
        while counted < n:
            d += dt.timedelta(days=1)
            if _working(d, region):
                counted += 1
    else:
        d = start + dt.timedelta(days=n)
        while not _working(d, region):  # a deadline ending on a non-working day moves to the next one
            d += dt.timedelta(days=1)
    return d
