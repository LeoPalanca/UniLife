"""Shared helpers + Recorder used across regression spec modules."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..db import read_table

FLOWS_TABLE = "ka1_he_studies_flows_with_indicators"
ERASMUSU_TABLE = "erasmusu_city_ratings"
REDDIT_TABLE = "reddit_destination_mentions"
COORDS_TABLE = "city_coordinates"

SENTIMENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
GAP_COLS = ["earnings_gap", "price_level_gap", "gdp_gap_usd_wb"]

# Each regression term carries (symbol, label, expected sign) for dashboard rendering.
TERM_META = {
    "rating_10": ("β₂", "Quality of life (Erasmusu rating)", "+"),
    "qol_city": ("β₂", "Quality of life (Reddit sentiment)", "+"),
    "qol_combined": ("β₂", "Quality of life (combined)", "+"),
    "gdp_gap_usd_wb": ("β₁", "GDP-per-capita gap", "+"),
    "earnings_gap": ("control", "Salary gap (per €1K) — robustness", "ambiguous"),
    "price_level_gap": ("control", "Price-level gap (cost of living) — robustness", "−"),
    "log_distance": ("control", "Distance (gravity friction)", "−"),
    "same_language": ("control", "Language affinity (shared family)", "+"),
    "inst_quality": ("β₃", "Institution quality (QS best score)", "+"),
    "user_inst_quality": ("β₃", "Institution quality (StudyPortals student score)", "+"),
    "life_satisfaction": ("β₂", "Quality of life (OWID life satisfaction, time-varying)", "+"),
    "edu_spend_gdp": ("β₃", "Education spending %GDP (OWID, time-varying)", "+"),
}


@dataclass
class Recorder:
    """Collects per-spec rows, year-FE points, and headline coefficient rows."""
    results: list[dict] = field(default_factory=list)
    panel_years: list[dict] = field(default_factory=list)
    model_coeffs: list[dict] = field(default_factory=list)

    def record(self, spec: str, kind: str, term: str, beta: float, p: float, n: int,
               note: str = "") -> None:
        self.results.append({
            "spec": spec, "kind": kind, "term": term,
            "beta": round(float(beta), 5), "p": round(float(p), 4),
            "n": int(n), "note": note,
        })

    def record_year(self, year: int, year_fe: float) -> None:
        self.panel_years.append({"year": int(year), "year_fe": round(float(year_fe), 4)})


def sentiment_series(r: pd.DataFrame) -> pd.Series:
    """Prefer the numeric sentiment_score; fall back to the categorical label."""
    cat = r["sentiment"].map(SENTIMENT_SCORE)
    if "sentiment_score" in r.columns:
        return pd.to_numeric(r["sentiment_score"], errors="coerce").fillna(cat)
    return cat


def norm_city(name) -> str | None:
    """Normalise a city name for matching: lowercase, strip accents, drop 'cedex'."""
    if pd.isna(name):
        return None
    s = str(name).lower().strip().replace("ß", "ss")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\bcedex\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def quality_of_life() -> pd.DataFrame:
    """Country-level Reddit QoL: confidence × log-upvote weighted mean sentiment."""
    r = read_table(REDDIT_TABLE).dropna(subset=["country", "sentiment"]).copy()
    r["s"] = sentiment_series(r)
    r["confidence_weight"] = pd.to_numeric(r["confidence"], errors="coerce").fillna(1.0)
    r["reddit_score"] = pd.to_numeric(r["score"], errors="coerce").fillna(0.0)
    r["score_weight"] = np.log1p(r["reddit_score"].clip(lower=0.0)) + 1.0
    r["w"] = r["confidence_weight"] * r["score_weight"]
    g = r.groupby("country").apply(
        lambda d: pd.Series({
            "qol": np.average(d["s"], weights=d["w"]),
            "qol_unweighted": d["s"].mean(),
            "qol_n": len(d),
        }),
        include_groups=False,
    )
    return g.reset_index().rename(columns={"country": "receiving_country"})


def city_quality_of_life() -> pd.DataFrame:
    """Per-city Reddit QoL, keyed by (lower-stripped country, normalised city)."""
    r = read_table(REDDIT_TABLE).dropna(subset=["country", "city", "sentiment"]).copy()
    r["s"] = sentiment_series(r)
    cw = pd.to_numeric(r["confidence"], errors="coerce").fillna(1.0)
    sw = np.log1p(pd.to_numeric(r["score"], errors="coerce").fillna(0.0).clip(lower=0.0)) + 1.0
    r["w"] = cw * sw
    r["cc"] = r["country"].str.lower().str.strip()
    r["ck"] = r["city"].map(norm_city)
    g = r.groupby(["cc", "ck"]).apply(
        lambda d: pd.Series({"qol_city": np.average(d["s"], weights=d["w"]),
                             "qol_city_n": len(d)}),
        include_groups=False,
    )
    return g.reset_index()


def erasmusu_city_qol() -> pd.DataFrame:
    """Per-city Erasmusu overall rating + opinion count."""
    e = read_table(ERASMUSU_TABLE).dropna(subset=["rating_10", "country_code", "city_norm"])
    return e[["country_code", "city_norm", "rating_10", "n_opinions"]]


def country_qol() -> pd.DataFrame:
    """Country-level Erasmusu + Reddit QoL plus broad destination economics."""
    flows = read_table(FLOWS_TABLE)
    name2code = (
        flows.dropna(subset=["receiving_country", "receiving_code"])
        .assign(_k=lambda d: d["receiving_country"].str.lower().str.strip())
        .drop_duplicates("_k")
        .set_index("_k")["receiving_code"].to_dict()
    )
    e = read_table(ERASMUSU_TABLE).dropna(subset=["rating_10", "country_code"]).copy()
    e["w"] = pd.to_numeric(e["n_opinions"], errors="coerce").fillna(1.0)
    eu = (e.groupby("country_code")
          .apply(lambda d: np.average(d["rating_10"], weights=d["w"]), include_groups=False)
          .rename("qol_erasmusu").reset_index()
          .rename(columns={"country_code": "receiving_code"}))

    rq = quality_of_life()
    rq["receiving_code"] = rq["receiving_country"].str.lower().str.strip().map(name2code)
    rq = (rq.dropna(subset=["receiving_code"])[["receiving_code", "qol"]]
          .rename(columns={"qol": "qol_reddit"}))

    econ = flows.drop_duplicates("receiving_code")[
        ["receiving_code", "receiver_gdp_pc_current_usd_wb",
         "receiver_price_level_aic_eu27_2020_100"]
    ]
    return eu.merge(rq, on="receiving_code", how="outer").merge(econ, on="receiving_code", how="left")


def add_gravity_terms(cf: pd.DataFrame) -> pd.DataFrame:
    """Attach distance (origin centroid -> destination city) and shared-language dummy."""
    from ..geo import COUNTRY_CENTROID, country_distance, same_language_family

    coords = read_table(COORDS_TABLE)[["receiving_code", "receiving_city", "lat", "lon"]].copy()
    coords["ck"] = coords["receiving_city"].map(norm_city)
    coords = coords.dropna(subset=["lat", "lon"]).drop_duplicates(["receiving_code", "ck"])
    cf = cf.merge(coords[["receiving_code", "ck", "lat", "lon"]],
                  on=["receiving_code", "ck"], how="left")

    cen = {k: v for k, v in COUNTRY_CENTROID.items()}
    cf["lat"] = cf["lat"].fillna(cf["receiving_code"].map(lambda c: cen.get(c, (None, None))[0]))
    cf["lon"] = cf["lon"].fillna(cf["receiving_code"].map(lambda c: cen.get(c, (None, None))[1]))

    cf["distance_km"] = [
        country_distance(o, la, lo)
        for o, la, lo in zip(cf["sending_code"], cf["lat"], cf["lon"])
    ]
    cf["log_distance"] = np.log(cf["distance_km"])
    cf["same_language"] = [
        same_language_family(o, d) for o, d in zip(cf["sending_code"], cf["receiving_code"])
    ]
    return cf


def show(res, names) -> None:
    for n in names:
        if n in res.params.index:
            print(f"  {n:18s} beta={res.params[n]:+.4e}  p={res.pvalues[n]:.3f}")
