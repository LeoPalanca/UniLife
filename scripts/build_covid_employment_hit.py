"""Build the 2020 COVID employment hit per (country, NACE sector).

Wage-based hits (`build_covid_sector_hit.py`) are contaminated by 2020 wage-subsidy
schemes (NL NOW, German Kurzarbeit, etc.) — so the LCI series proxies lockdown
intensity, not the sector-damage channel we want. Employment-based hits use
Eurostat `lfsa_egan22d` (annual employment levels by NACE), which is not subject
to the same subsidy distortion: a furloughed worker remains employed in the LFS.

    emp_growth_{j,s,t} = (E_{j,s,t} - E_{j,s,t-1}) / E_{j,s,t-1}
    covid_emp_hit_pp = emp_growth_{j,s,2020} - mean(emp_growth_{j,s, 2015..2019})

Negative values = sector employment in 2020 fell below its own pre-COVID norm
(harder hit). This feeds an alternative DiD specification alongside the original
LCI-based one — the cleaner replication the methodology notes called for.
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.indicators import fetch_eurostat

OUT = Path("data/processed/covid_employment_hit.csv")


def main() -> None:
    d = fetch_eurostat(
        "lfsa_egan2",
        unit="THS_PER",
        sex="T",
        age="Y15-64",
    )
    d = d[d["nace_r2"].str.fullmatch(r"[A-Z]")].copy()
    d["year"] = pd.to_numeric(d["time"], errors="coerce")
    d = d.dropna(subset=["value", "year"])
    d = d[~d["geo"].str.startswith(("EU", "EA"))]
    d["receiving_code"] = d["geo"].replace({"GB": "UK", "GR": "EL"})

    # annual employment growth per (country, sector)
    d = d.sort_values(["receiving_code", "nace_r2", "year"])
    d["emp_growth"] = (
        d.groupby(["receiving_code", "nace_r2"])["value"].pct_change()
    )

    pre = (d[d["year"].between(2015, 2019)]
           .groupby(["receiving_code", "nace_r2"])["emp_growth"].mean()
           .rename("baseline"))
    y20 = (d[d["year"] == 2020]
           .set_index(["receiving_code", "nace_r2"])["emp_growth"]
           .rename("emp_2020_growth"))
    out = pd.concat([y20, pre], axis=1, join="inner").reset_index()
    out = out.dropna(subset=["emp_2020_growth", "baseline"])
    out["covid_emp_hit_pp"] = out["emp_2020_growth"] - out["baseline"]
    out["nace_label"] = (d.drop_duplicates(["nace_r2"])
                        .set_index("nace_r2")["nace_r2_label"]
                        .reindex(out["nace_r2"]).values)
    out = out[["receiving_code", "nace_r2", "nace_label",
               "emp_2020_growth", "baseline", "covid_emp_hit_pp"]]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"saved {len(out)} (country, sector) rows -> {OUT}")
    print(f"  countries {out['receiving_code'].nunique()} | sectors {out['nace_r2'].nunique()}")
    print("\nHardest-hit cells (most negative covid_emp_hit_pp):")
    print(out.sort_values("covid_emp_hit_pp").head(8).to_string(index=False))
    print("\nMost-resilient cells:")
    print(out.sort_values("covid_emp_hit_pp", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
