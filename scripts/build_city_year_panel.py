"""Build an HE-study city-year flow panel from the Vaisanen individual file.

Aggregates Higher-Education *study* mobilities (excludes traineeships) to
(origin country, destination country, destination city, year). City names are
normalised to match the Erasmusu ratings. Output feeds the city-level panel
gravity / two-stage QoL test.
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.erasmusu import norm_city

from erasmusgravity.ka1 import country_name_to_code

RAW = Path("data/raw/Erasmus_2014-2023_individual.parquet")
OUT = Path("data/processed/erasmus_he_city_year_panel.csv")


def main() -> None:
    cols = ["Field", "Activity (mob)", "o_country", "d_country", "Receiving City", "Actual Participants", "year"]
    p = pd.read_parquet(RAW, columns=cols)
    p = p[(p["Field"] == "Higher Education") & p["Activity (mob)"].str.contains("studies", case=False, na=False)]
    p["city_norm"] = p["Receiving City"].map(norm_city)
    p = p.dropna(subset=["o_country", "d_country", "city_norm", "year"])

    panel = (
        p.groupby(["o_country", "d_country", "city_norm", "year"], as_index=False)["Actual Participants"]
        .sum()
        .rename(columns={
            "o_country": "sending_code", "d_country": "receiving_code",
            "Actual Participants": "flow_count",
        })
    )
    panel["flow_count"] = panel["flow_count"].astype(int)
    code = country_name_to_code()
    panel["sending_code"] = panel["sending_code"].map(code)
    panel["receiving_code"] = panel["receiving_code"].map(code)
    panel = panel.dropna(subset=["sending_code", "receiving_code"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUT, index=False)
    print(f"saved {len(panel):,} rows to {OUT}")
    print(f"  years {panel['year'].min()}-{panel['year'].max()} | "
          f"origins {panel['sending_code'].nunique()} | dest countries {panel['receiving_code'].nunique()} | "
          f"dest cities {panel['city_norm'].nunique():,}")


if __name__ == "__main__":
    main()
