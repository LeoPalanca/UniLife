"""Build a city-level institution-quality score (gravity term beta3).

QS World University Rankings give university name + country + an overall score,
but no city. To attach quality to Erasmus destination *cities* without fuzzy-
matching messy institution names, each ranked university is geocoded (Nominatim,
filtered to its country) and snapped to the nearest Erasmus receiving city
(data/processed/city_coordinates.csv). Per (receiving_code, city_norm) we keep:

  n_ranked    : how many ranked universities sit in/near the city
  best_score  : QS overall score of the city's strongest university (primary)
  sum_score   : summed QS score (size + quality of the city's academic cluster)

Geocoding is cached to data/raw/qs_geocoded.csv so reruns are free and the
network step is resumable. Branch-campus geocodes add some noise (documented).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.geo import COUNTRY_CENTROID
from erasmusgravity.geocode import geocode_cached, snap_to_nearest_city

QS = Path("data/raw/qs_world_2023.csv")
GEO_CACHE = Path("data/raw/qs_geocoded.csv")
OUT = Path("data/processed/institution_quality.csv")

# QS publishes Greece as "GR"; Erasmus data uses "EL".
QS_TO_CODE = {"GR": "EL"}


def load_qs() -> pd.DataFrame:
    d = pd.read_csv(QS).rename(columns={"location code": "qs_code", "score scaled": "score"})
    d["code"] = d["qs_code"].replace(QS_TO_CODE)
    d["score"] = pd.to_numeric(d["score"], errors="coerce")
    d = d.dropna(subset=["score"])
    d = d[d["code"].isin(COUNTRY_CENTROID)]
    return d[["institution", "code", "score"]].reset_index(drop=True)


def main() -> None:
    qs = load_qs()
    print(f"QS European universities: {len(qs)} in {qs['code'].nunique()} countries")
    geo = geocode_cached(qs, GEO_CACHE, key_cols=("institution", "code"))
    scored = geo.merge(qs[["institution", "code", "score"]],
                       on=["institution", "code"], how="left")
    snapped = snap_to_nearest_city(scored, code_col="code", extra_cols=("score",))
    print(f"snapped to Erasmus cities: {len(snapped)} universities "
          f"-> {snapped['city_norm'].nunique()} cities")

    agg = snapped.groupby(["receiving_code", "city_norm"], as_index=False).agg(
        n_ranked=("score", "size"), best_score=("score", "max"), sum_score=("score", "sum"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT, index=False)
    print(f"saved {len(agg)} city rows to {OUT}")
    print(agg.sort_values("best_score", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
