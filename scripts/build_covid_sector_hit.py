"""Build the 2020 COVID wage hit per (country, NACE sector).

Eurostat Labour Cost Index `lc_lci_r2_a` (D11 wages and salaries, annual % change
vs previous year) gives a comparable annual wage-growth series by NACE sector
and country. The COVID hit is the 2020 deviation from each (country, sector)'s
pre-COVID baseline:

    covid_hit_pp = LCI_growth_{j,s,2020} - mean(LCI_growth_{j,s, 2015..2019})

Negative values = sector wage growth in 2020 fell below its own pre-COVID norm
(harder hit). Output feeds the field-level DiD: every ISCED-F broad field is
mapped to one NACE letter, then `covid_hit_pp` enters the regression as a
destination x sector treatment intensity.
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.indicators import fetch_eurostat

OUT = Path("data/processed/covid_sector_hit.csv")


def main() -> None:
    d = fetch_eurostat("lc_lci_r2_a", lcstruct="D11", unit="PCH_PRE")
    d = d[d["nace_r2"].str.fullmatch(r"[A-Z]")].copy()
    d["year"] = pd.to_numeric(d["time"], errors="coerce")
    d = d.dropna(subset=["value", "year"])
    d = d[~d["geo"].str.startswith(("EU", "EA"))]
    d["receiving_code"] = d["geo"].replace({"GB": "UK", "GR": "EL"})

    pre = (d[d["year"].between(2015, 2019)]
           .groupby(["receiving_code", "nace_r2"])["value"].mean()
           .rename("baseline"))
    y20 = (d[d["year"] == 2020]
           .set_index(["receiving_code", "nace_r2"])["value"]
           .rename("lci_2020"))
    out = pd.concat([y20, pre], axis=1, join="inner").reset_index()
    out["covid_hit_pp"] = out["lci_2020"] - out["baseline"]
    out["nace_label"] = (d.drop_duplicates(["nace_r2"])
                        .set_index("nace_r2")["nace_r2_label"]
                        .reindex(out["nace_r2"]).values)
    out = out[["receiving_code", "nace_r2", "nace_label", "lci_2020", "baseline", "covid_hit_pp"]]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"saved {len(out)} (country, sector) rows -> {OUT}")
    print(f"  countries {out['receiving_code'].nunique()} | sectors {out['nace_r2'].nunique()}")
    print("\nHardest-hit cells (most negative covid_hit_pp):")
    print(out.sort_values("covid_hit_pp").head(8).to_string(index=False))
    print("\nMost-resilient cells:")
    print(out.sort_values("covid_hit_pp", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
