"""Build a (sending, receiving, ISCED broad field, year) HE-study flow panel.

Aggregates the Vaisanen individual file to the granularity needed for the
field-level gravity / COVID-DiD analysis: each row is one origin x destination
x ISCED-F broad field x year cell, with summed Actual Participants. Records
with no mappable broad field (generic programmes, unknown) are dropped, as are
non-cross-border pairs and rows missing key keys.
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.fields import to_broad_code

from erasmusgravity.ka1 import country_name_to_code

RAW = Path("data/raw/Erasmus_2014-2023_individual.parquet")
OUT = Path("data/processed/erasmus_field_flow_panel.csv")


def main() -> None:
    cols = ["Field", "Activity (mob)", "Field of Education", "o_country", "d_country",
            "Actual Participants", "year"]
    p = pd.read_parquet(RAW, columns=cols)
    p = p[(p["Field"] == "Higher Education")
          & p["Activity (mob)"].str.contains("studies", case=False, na=False)]
    p["isced_broad"] = p["Field of Education"].map(to_broad_code)
    p = p.dropna(subset=["isced_broad", "o_country", "d_country", "year"])

    code = country_name_to_code()
    p["sending_code"] = p["o_country"].map(code)
    p["receiving_code"] = p["d_country"].map(code)
    p = p.dropna(subset=["sending_code", "receiving_code"])
    p = p[p["sending_code"] != p["receiving_code"]]  # cross-border only

    panel = (p.groupby(["sending_code", "receiving_code", "isced_broad", "year"], as_index=False)
             ["Actual Participants"].sum()
             .rename(columns={"Actual Participants": "flow_count"}))
    panel["flow_count"] = panel["flow_count"].astype(int)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUT, index=False)
    print(f"saved {len(panel):,} rows -> {OUT}")
    print(f"  origins {panel['sending_code'].nunique()} | dests {panel['receiving_code'].nunique()}"
          f" | fields {panel['isced_broad'].nunique()} | years {panel['year'].min()}-{panel['year'].max()}")
    print("\nfield share of flows:")
    print(panel.groupby("isced_broad")["flow_count"].sum().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
