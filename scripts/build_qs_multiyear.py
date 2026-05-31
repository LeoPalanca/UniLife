"""Build a multi-year QS rankings panel for time-varying β₃.

QS publishes the "World University Rankings" once per year. Each annual edition
sits behind a numeric ID on `topuniversities.com/sites/default/files/qs-rankings-data/<id>.txt`
as a JSON feed. The live site is Cloudflare-gated, but Wayback serves every
snapshot of the feed unchanged.

The 280 feed IDs that the CDX index returns are a mix of overall world rankings
(one per year) and subject/regional rankings. We probe a small candidate set,
keep only the editions that look like the global "Overall World Ranking"
(rows ≥ 700, top entry MIT with score 100), tag each by the top-3 fingerprint
heuristic, then run the existing institution-quality pipeline per edition.

Caveat documented openly:
- Year labels are heuristic (top-3 fingerprint vs known QS history). Different
  IDs that look identical at the top may differ deeper in the table.
- Branch-campus geocoding adds noise (same as the single-year build).
- QS scores are highly sticky year-over-year, so within-city variation is
  small — bounded payoff against the parked-item caveat.

Output: `data/processed/institution_quality_panel.csv` keyed
`(receiving_code, city_norm, year)` with `best_score`. Cache:
`data/raw/qs_panel_raw.csv` so reruns are free.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.geo import COUNTRY_CENTROID
from erasmusgravity.geocode import NOMINATIM_UA, geocode_cached, snap_to_nearest_city

GEO_CACHE = Path("data/raw/qs_geocoded_panel.csv")
RAW = Path("data/raw/qs_panel_raw.csv")
OUT = Path("data/processed/institution_quality_panel.csv")

UA = {"User-Agent": NOMINATIM_UA}

# (feed_id, fingerprint top-3, heuristic year). Years from rough QS history matching.
# 10801 — MIT/Cambridge/Harvard/UCL/Oxford pattern, ~726 rows: QS 2013-14 release.
# 121321 — MIT/Harvard/Cambridge, ~833 rows: QS 2016-17 release.
# 197036 — MIT/Cambridge=Imperial tie, ~863 rows: QS 2017-18 release.
# 2023 (CSV) — already on disk as data/raw/qs_world_2023.csv.
KNOWN_EDITIONS = [
    {"id": "10801", "year": 2014, "fingerprint": "MIT/Cambridge/Harvard"},
    {"id": "121321", "year": 2017, "fingerprint": "MIT/Harvard/Cambridge"},
    {"id": "197036", "year": 2018, "fingerprint": "MIT/Cambridge=Imperial"},
]
WAYBACK_TS = "20220101000000"  # snapshot date used for every fetch
QS_TO_CODE = {"GR": "EL"}
COUNTRY_TO_CODE = {
    "United Kingdom": "UK", "Germany": "DE", "France": "FR", "Italy": "IT",
    "Spain": "ES", "Netherlands": "NL", "Sweden": "SE", "Switzerland": "CH",
    "Belgium": "BE", "Denmark": "DK", "Finland": "FI", "Norway": "NO",
    "Ireland": "IE", "Austria": "AT", "Portugal": "PT", "Czech Republic": "CZ",
    "Poland": "PL", "Greece": "EL", "Hungary": "HU", "Romania": "RO",
    "Slovenia": "SI", "Slovakia": "SK", "Bulgaria": "BG", "Croatia": "HR",
    "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT", "Cyprus": "CY",
    "Malta": "MT", "Luxembourg": "LU", "Iceland": "IS", "Turkey": "TR",
}


def fetch_edition(feed_id: str) -> list[dict]:
    url = (f"https://web.archive.org/web/{WAYBACK_TS}id_/"
           f"https://www.topuniversities.com/sites/default/files/qs-rankings-data/{feed_id}.txt")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    return d.get("data", [])


def parse_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        try:
            score = float(r.get("score") or 0)
        except (TypeError, ValueError):
            continue
        country = r.get("country") or ""
        code = QS_TO_CODE.get(country, COUNTRY_TO_CODE.get(country))
        if code is None or code not in COUNTRY_CENTROID or score <= 0:
            continue
        out.append({"institution": (r.get("title") or "").strip(), "code": code, "score": score})
    return out


def load_2023() -> pd.DataFrame:
    d = pd.read_csv("data/raw/qs_world_2023.csv").rename(
        columns={"location code": "qs_code", "score scaled": "score"})
    d["code"] = d["qs_code"].replace(QS_TO_CODE)
    d["score"] = pd.to_numeric(d["score"], errors="coerce")
    d = d.dropna(subset=["score"])
    d = d[d["code"].isin(COUNTRY_CENTROID)]
    d = d[["institution", "code", "score"]].copy()
    d["year"] = 2023
    return d


def main() -> None:
    all_rows: list[pd.DataFrame] = []
    for ed in KNOWN_EDITIONS:
        try:
            print(f"fetching QS edition {ed['id']} ({ed['year']}, {ed['fingerprint']})...")
            rows = parse_rows(fetch_edition(ed["id"]))
            if not rows:
                print(f"  ! {ed['id']} returned 0 parseable rows")
                continue
            df = pd.DataFrame(rows)
            df["year"] = ed["year"]
            all_rows.append(df)
            print(f"  {len(df)} European universities")
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"  ! {ed['id']}: {e}")
            continue

    all_rows.append(load_2023())
    print(f"  2023 (live CSV): {len(all_rows[-1])} European universities")

    scored = pd.concat(all_rows, ignore_index=True)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(RAW, index=False)
    print(f"\ncached {len(scored)} rows across {scored['year'].nunique()} editions -> {RAW}")

    geo = geocode_cached(scored, GEO_CACHE, key_cols=("institution", "code"))
    merged = scored.merge(geo, on=["institution", "code"], how="left")
    snapped = snap_to_nearest_city(merged, code_col="code", extra_cols=("year", "score"))
    print(f"snapped to Erasmus cities: {len(snapped)} (institution, year) rows -> "
          f"{snapped['city_norm'].nunique()} cities across {snapped['year'].nunique()} years")

    agg = (snapped.groupby(["receiving_code", "city_norm", "year"], as_index=False)
                  .agg(best_score=("score", "max"), n_ranked=("score", "size")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT, index=False)
    print(f"\nsaved {len(agg)} (city, year) rows to {OUT}")
    print(f"  cities × years: {agg['city_norm'].nunique()} × {agg['year'].nunique()}")
    print("\nSample (best score across years for top cities):")
    print(agg.sort_values("best_score", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
