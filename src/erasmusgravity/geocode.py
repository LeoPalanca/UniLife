from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

import pandas as pd

from .cities import normalize_city_key

# Erasmus/EU country codes that differ from the ISO-3166 alpha-2 codes geonames uses.
CODE_REMAP = {"UK": "GB", "EL": "GR"}
# Erasmus code -> Nominatim countrycode (lowercase ISO-3166-1 alpha-2).
CODE_TO_CC = {"UK": "gb", "EL": "gr"}
# Default User-Agent for Nominatim — service requires identification.
NOMINATIM_UA = "erasmusgravity-research/1.0 (leo.palanca01@gmail.com)"
DEFAULT_SNAP_KM = 35.0

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


def geocode_nominatim(name: str, cc: str, timeout: int = 30,
                      user_agent: str = NOMINATIM_UA) -> tuple[float, float] | None:
    """Single Nominatim search restricted to one country code (lowercase ISO2).

    Returns `(lat, lon)` or `None` if the query yields no result or the network
    call fails. Callers must respect the 1 req/sec usage policy themselves.
    """
    q = urllib.parse.urlencode({"q": name, "format": "json", "limit": 1, "countrycodes": cc})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{q}",
        headers={"User-Agent": user_agent},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:  # noqa: BLE001 - network best-effort, callers cache + resume
        print(f"    ! {name}: {e}")
        return None
    if not d:
        return None
    return float(d[0]["lat"]), float(d[0]["lon"])


def geocode_cached(rows: pd.DataFrame, cache_path: str | Path,
                   key_cols: tuple[str, str] = ("institution", "code"),
                   pause: float = 1.1,
                   checkpoint_every: int = 25) -> pd.DataFrame:
    """Resumable geocoding loop. `rows` carries the key_cols (typically
    institution + Erasmus country code). Writes incremental progress to
    `cache_path` so reruns skip completed entries. Erasmus codes are mapped to
    Nominatim countrycodes via `CODE_TO_CC` (UK→gb, EL→gr) with lowercase
    fallback.
    """
    cache_path = Path(cache_path)
    name_col, code_col = key_cols
    columns = [name_col, code_col, "lat", "lon"]
    cache = (pd.read_csv(cache_path) if cache_path.exists()
             else pd.DataFrame(columns=columns))
    done = set(zip(cache[name_col], cache[code_col]))
    out = cache.to_dict("records")
    todo = [r for r in rows[list(key_cols)].drop_duplicates().to_dict("records")
            if (r[name_col], r[code_col]) not in done]
    print(f"geocoding {len(todo)} new entries ({len(done)} cached)")
    for i, r in enumerate(todo, 1):
        cc = CODE_TO_CC.get(r[code_col], str(r[code_col]).lower())
        ll = geocode_nominatim(r[name_col], cc)
        out.append({name_col: r[name_col], code_col: r[code_col],
                    "lat": ll[0] if ll else None, "lon": ll[1] if ll else None})
        if i % checkpoint_every == 0:
            print(f"  {i}/{len(todo)}")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(out).to_csv(cache_path, index=False)
        time.sleep(pause)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(out)
    df.to_csv(cache_path, index=False)
    return df


def snap_to_nearest_city(scored: pd.DataFrame,
                         coords_path: str | Path = "data/processed/city_coordinates.csv",
                         max_km: float = DEFAULT_SNAP_KM,
                         code_col: str = "code",
                         extra_cols: Iterable[str] = ()) -> pd.DataFrame:
    """Snap each geocoded entry to its nearest Erasmus receiving city within `max_km`.

    `scored` must carry `lat`, `lon`, `code` (Erasmus country code), and any
    columns named in `extra_cols` (e.g. `score`, `year`). Returns one row per
    successful snap with `receiving_code`, `city_norm`, plus the `extra_cols`.
    Drops entries with missing coordinates or no candidate within `max_km`.
    """
    from .erasmusu import norm_city
    from .geo import haversine

    coords = pd.read_csv(coords_path).dropna(subset=["lat", "lon"])
    coords["city_norm"] = coords["receiving_city"].map(norm_city)
    by_code = {c: g for c, g in coords.groupby("receiving_code")}

    out: list[dict] = []
    for r in scored.dropna(subset=["lat", "lon"]).to_dict("records"):
        cand = by_code.get(r[code_col])
        if cand is None:
            continue
        dist = cand.apply(lambda c: haversine(r["lat"], r["lon"], c["lat"], c["lon"]), axis=1)
        j = dist.idxmin()
        if dist[j] > max_km:
            continue
        row = {"receiving_code": r[code_col], "city_norm": cand.loc[j, "city_norm"]}
        for col in extra_cols:
            row[col] = r.get(col)
        out.append(row)
    return pd.DataFrame(out)
