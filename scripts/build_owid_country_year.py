"""Build a country-year panel of OWID indicators for time-varying gravity terms.

Reddit/Erasmusu QoL and the QS/StudyPortals institution measures are all
time-invariant, so they can only enter the cross-section. Our World in Data
publishes open, country-year series that *do* vary over time, letting us test a
time-varying destination QoL / education-quality term in the panel PPML:

  life_satisfaction : Cantril ladder score (0-10), World Happiness Report (OWID)
  edu_spend_gdp     : total government expenditure on education, % of GDP (OWID)

OWID entities are matched to our EU-style receiving codes by country name
(reusing the flows table, which already encodes EL = Greece, UK = United Kingdom).
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

UA = {"User-Agent": "erasmusgravity-research/1.0 (leo.palanca01@gmail.com)"}
SERIES = {
    "life_satisfaction": ("happiness-cantril-ladder", "cantril_ladder_score"),
    "edu_spend_gdp": ("total-government-expenditure-on-education-gdp", "combined_expenditure_share_gdp"),
}
RAW_DIR = Path("data/raw")
OUT = Path("data/processed/owid_country_year.csv")


def fetch(slug: str) -> pd.DataFrame:
    cache = RAW_DIR / f"owid_{slug}.csv"
    if not cache.exists():
        url = f"https://ourworldindata.org/grapher/{slug}.csv?csvType=full&useColumnShortNames=true"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            cache.write_bytes(r.read())
    return pd.read_csv(cache)


def main() -> None:
    from erasmusgravity.ka1 import country_name_to_code
    code = country_name_to_code(sides=("receiving",), lowercase=True)
    out = None
    for name, (slug, col) in SERIES.items():
        d = fetch(slug)
        d = d.rename(columns={col: name})[["entity", "year", name]]
        d["receiving_code"] = d["entity"].str.lower().str.strip().map(code)
        d = d.dropna(subset=["receiving_code", name])[["receiving_code", "year", name]]
        out = d if out is None else out.merge(d, on=["receiving_code", "year"], how="outer")
        print(f"  {name}: {len(d)} country-years, {d['receiving_code'].nunique()} countries")

    out = out.sort_values(["receiving_code", "year"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"saved {len(out)} rows -> {OUT}")
    print(out[out["year"].between(2014, 2023)].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
