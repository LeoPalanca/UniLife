"""Geographic friction and language affinity for the gravity model.

Country centroids (approx. geographic centre, decimal degrees) and dominant
language families are static reference facts, keyed by the EU-style ISO2 codes
used in the Erasmus data (EL = Greece, UK = United Kingdom, XK = Kosovo).

Used to build two gravity terms:
- distance_ij  : great-circle km between origin-country centroid and the
                 destination city (origin is always a country in the flow data).
- same_language: 1 if origin and destination share a language family, else 0.
"""
from __future__ import annotations

import math

# approximate country centroid (lat, lon) for European program/partner countries
COUNTRY_CENTROID: dict[str, tuple[float, float]] = {
    "AT": (47.59, 14.14), "BE": (50.64, 4.67), "BG": (42.77, 25.23),
    "HR": (45.08, 15.48), "CY": (35.13, 33.43), "CZ": (49.80, 15.47),
    "DK": (56.06, 9.50), "EE": (58.67, 25.54), "FI": (64.50, 26.07),
    "FR": (46.56, 2.40), "DE": (51.11, 10.39), "EL": (39.07, 22.96),
    "HU": (47.16, 19.50), "IE": (53.18, -8.14), "IT": (42.50, 12.57),
    "LV": (56.86, 24.92), "LT": (55.34, 23.89), "LU": (49.77, 6.10),
    "MT": (35.92, 14.41), "NL": (52.10, 5.28), "PL": (52.13, 19.39),
    "PT": (39.60, -8.50), "RO": (45.85, 24.97), "SK": (48.71, 19.48),
    "SI": (46.15, 14.99), "ES": (40.24, -3.65), "SE": (62.20, 17.64),
    "UK": (54.12, -2.86), "IS": (64.92, -18.26), "LI": (47.16, 9.55),
    "NO": (64.57, 17.89), "CH": (46.80, 8.23),
    "AL": (41.14, 20.05), "BA": (44.17, 17.77), "ME": (42.79, 19.24),
    "MK": (41.60, 21.70), "RS": (44.22, 20.79), "XK": (42.57, 20.90),
    "TR": (39.06, 35.17), "MD": (47.20, 28.46), "UA": (48.97, 31.16),
    "BY": (53.43, 27.70), "RU": (61.52, 105.32), "AM": (40.29, 44.93),
    "AZ": (40.29, 47.70), "GE": (42.17, 43.51), "AD": (42.55, 1.60),
}

# dominant language family per country (one per country for a same-family dummy)
LANGUAGE_FAMILY: dict[str, str] = {
    # Romance
    "FR": "romance", "IT": "romance", "ES": "romance", "PT": "romance",
    "RO": "romance", "MD": "romance", "AD": "romance",
    # Germanic (incl. English-speaking and German-majority multilingual states)
    "DE": "germanic", "AT": "germanic", "NL": "germanic", "BE": "germanic",
    "LU": "germanic", "CH": "germanic", "LI": "germanic", "DK": "germanic",
    "SE": "germanic", "NO": "germanic", "IS": "germanic", "UK": "germanic",
    "IE": "germanic",
    # Slavic
    "PL": "slavic", "CZ": "slavic", "SK": "slavic", "SI": "slavic",
    "HR": "slavic", "RS": "slavic", "BG": "slavic", "MK": "slavic",
    "BA": "slavic", "ME": "slavic", "UA": "slavic", "BY": "slavic",
    "RU": "slavic",
    # Uralic
    "FI": "uralic", "EE": "uralic", "HU": "uralic",
    # Baltic
    "LT": "baltic", "LV": "baltic",
    # Hellenic
    "EL": "hellenic", "CY": "hellenic",
    # Albanian
    "AL": "albanian", "XK": "albanian",
    # Turkic
    "TR": "turkic", "AZ": "turkic",
    # singletons
    "MT": "semitic", "GE": "kartvelian", "AM": "armenian",
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def country_distance(origin: str, lat: float, lon: float) -> float | None:
    """km from origin-country centroid to a destination point (lat, lon)."""
    c = COUNTRY_CENTROID.get(origin)
    if c is None or lat is None or lon is None:
        return None
    return haversine(c[0], c[1], lat, lon)


def same_language_family(origin: str, dest: str) -> float | None:
    fo, fd = LANGUAGE_FAMILY.get(origin), LANGUAGE_FAMILY.get(dest)
    if fo is None or fd is None:
        return None
    return 1.0 if fo == fd else 0.0
