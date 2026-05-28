from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .cities import normalize_city_key

# Erasmus/EU country codes that differ from the ISO-3166 alpha-2 codes geonames uses.
CODE_REMAP = {"UK": "GB", "EL": "GR"}

_CEDEX = re.compile(r"\bcedex\b.*", re.IGNORECASE)
_BRACKET = re.compile(r"[\[\(].*?[\]\)]")
_SPLIT = re.compile(r"[/,;_]| - ")
_DIGITS = re.compile(r"\b\d+\b")


def clean_city_for_lookup(value: object) -> str | None:
    """Strip postal/arrondissement noise before gazetteer lookup."""
    text = _CEDEX.sub("", str(value))
    text = _BRACKET.sub("", text)
    text = _SPLIT.split(text)[0]
    text = _DIGITS.sub("", text)
    return normalize_city_key(text)


def _gc_cities() -> dict:
    import geonamescache

    return geonamescache.GeonamesCache().get_cities()


def build_gazetteer() -> dict[tuple[str, str], tuple[float, float]]:
    """Map (country_code, normalized_name) -> (lat, lon) using the most populous match."""
    lut: dict[tuple[str, str], tuple[float, float, int]] = {}
    for city in _gc_cities().values():
        cc = city["countrycode"]
        pop = city.get("population", 0) or 0
        coord = (city["latitude"], city["longitude"], pop)
        names = [city["name"], *city.get("alternatenames", [])]
        for name in names:
            key = normalize_city_key(name)
            if not key:
                continue
            slot = (cc, key)
            if slot not in lut or pop > lut[slot][2]:
                lut[slot] = coord
    return {slot: (lat, lon) for slot, (lat, lon, _) in lut.items()}


def country_centroids() -> dict[str, tuple[float, float]]:
    """Population-weighted country centroid from the gazetteer, for fallback points."""
    agg: dict[str, list[float]] = {}
    for city in _gc_cities().values():
        cc = city["countrycode"]
        pop = city.get("population", 0) or 0
        if pop <= 0:
            continue
        lat_sum, lon_sum, w = agg.get(cc, [0.0, 0.0, 0.0])
        agg[cc] = [lat_sum + city["latitude"] * pop, lon_sum + city["longitude"] * pop, w + pop]
    return {cc: (lat / w, lon / w) for cc, (lat, lon, w) in agg.items() if w > 0}


def geocode_receiving_cities(flows: pd.DataFrame) -> pd.DataFrame:
    """Build a coordinate table for distinct receiving cities with a city/country match level."""
    gazetteer = build_gazetteer()
    centroids = country_centroids()

    cities = (
        flows.groupby(["receiving_code", "receiving_country", "receiving_city"], as_index=False)["flow_count"]
        .sum()
        .rename(columns={"flow_count": "inbound_flow"})
    )

    lats, lons, levels = [], [], []
    for code, name in zip(cities["receiving_code"], cities["receiving_city"]):
        gc_code = CODE_REMAP.get(code, code)
        key = clean_city_for_lookup(name)
        hit = gazetteer.get((gc_code, key)) if key else None
        if hit is not None:
            lats.append(hit[0])
            lons.append(hit[1])
            levels.append("city")
        else:
            centroid = centroids.get(gc_code)
            lats.append(centroid[0] if centroid else None)
            lons.append(centroid[1] if centroid else None)
            levels.append("country" if centroid else "missing")

    cities["lat"] = lats
    cities["lon"] = lons
    cities["match_level"] = levels
    return cities.sort_values("inbound_flow", ascending=False).reset_index(drop=True)


def build_city_coordinates(flows_path: str | Path = "data/processed/erasmus_city_flows_long.csv") -> pd.DataFrame:
    flows = pd.read_csv(flows_path)
    return geocode_receiving_cities(flows)
