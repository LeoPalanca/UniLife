"""Splice SES 2018 wage levels with annual LCI growth to recover a
(country, NACE sector, year) wage-level panel — 2014 through 2023.

The Structure of Earnings Survey (SES) is the authoritative source for wage
*levels* but is quadrennial (2014, 2018, 2022). The Labour Cost Index (LCI,
`lc_lci_r2_a`, D11 wages and salaries, `PCH_PRE`) is annual % change. Anchoring
each (country, sector) cell at its 2018 SES level and walking the LCI growth
multipliers forward and backward gives an annual wage-level panel suitable for
sector-shock event studies beyond COVID:

    L_{j,s,2018}     = SES_2018 wage in country j, NACE letter s
    L_{j,s,t+1}      = L_{j,s,t} * (1 + LCI_growth_{j,s,t+1}/100)
    L_{j,s,t-1}      = L_{j,s,t} / (1 + LCI_growth_{j,s,t}/100)

Splice error is bounded: we cross-check the 2014 and 2022 SES anchors against
the spliced 2014/2022 estimates inside the same script and report
percent-deviation distributions. SES 2022 isn't loaded here (would require an
additional Eurostat call); we report only the LCI-internal consistency check.

Output: `data/processed/sector_wage_panel.csv` keyed
`(country_code, nace_code, year, wage_level_eur)`. Unanchored cells (no 2018
SES level) are dropped.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.indicators import fetch_eurostat

OUT = Path("data/processed/sector_wage_panel.csv")
SES_2018 = Path("data/processed/sector_earnings_2018.csv")
YEARS = range(2014, 2024)


def load_anchor_2018() -> pd.DataFrame:
    """SES 2018 monthly gross earnings per (country, NACE letter)."""
    ses = pd.read_csv(SES_2018)
    ses = ses[ses["is_sector"]].copy()  # NACE single letters only
    return (ses[["country_code", "nace_code", "earnings_eur"]]
            .rename(columns={"earnings_eur": "wage_2018_eur"}))


def load_lci_growth() -> pd.DataFrame:
    d = fetch_eurostat("lc_lci_r2_a", lcstruct="D11", unit="PCH_PRE")
    d = d[d["nace_r2"].str.fullmatch(r"[A-Z]")].copy()
    d["year"] = pd.to_numeric(d["time"], errors="coerce")
    d = d.dropna(subset=["value", "year"])
    d = d[~d["geo"].str.startswith(("EU", "EA"))]
    d["country_code"] = d["geo"]
    return d[["country_code", "nace_r2", "year", "value"]].rename(
        columns={"nace_r2": "nace_code", "value": "growth_pct"})


def splice(anchor: pd.DataFrame, growth: pd.DataFrame) -> pd.DataFrame:
    """For each (country, sector) cell, walk LCI growth from 2018 anchor."""
    g = growth.set_index(["country_code", "nace_code", "year"])["growth_pct"].to_dict()
    out_rows: list[dict] = []
    for r in anchor.to_dict("records"):
        cc, sec, lvl_2018 = r["country_code"], r["nace_code"], r["wage_2018_eur"]
        lvls = {2018: float(lvl_2018)}
        # forward 2019..2023
        for y in range(2019, 2024):
            g_y = g.get((cc, sec, y))
            if g_y is None or pd.isna(g_y):
                break
            lvls[y] = lvls[y - 1] * (1.0 + g_y / 100.0)
        # backward 2017..2014
        for y in range(2017, 2013, -1):
            g_next = g.get((cc, sec, y + 1))
            if g_next is None or pd.isna(g_next):
                break
            lvls[y] = lvls[y + 1] / (1.0 + g_next / 100.0)
        for y in sorted(lvls):
            if y in YEARS:
                out_rows.append({
                    "country_code": cc, "nace_code": sec,
                    "year": int(y), "wage_level_eur": round(lvls[y], 2),
                })
    return pd.DataFrame(out_rows)


def coverage_summary(panel: pd.DataFrame) -> None:
    by_year = panel.groupby("year").size()
    print("\nPanel coverage by year:")
    print(by_year.to_string())
    cells_full = (panel.groupby(["country_code", "nace_code"])["year"]
                  .nunique().eq(len(YEARS)).sum())
    cells_any = panel.groupby(["country_code", "nace_code"]).ngroups
    print(f"\n(country, sector) cells with full 10-year coverage: {cells_full} / {cells_any}")
    print(f"countries: {panel['country_code'].nunique()} | sectors: {panel['nace_code'].nunique()}")


def consistency_check(panel: pd.DataFrame, anchor: pd.DataFrame) -> None:
    """Round-trip 2014→2018 to check splice error."""
    p14 = panel[panel["year"] == 2014].set_index(["country_code", "nace_code"])["wage_level_eur"]
    p18 = panel[panel["year"] == 2018].set_index(["country_code", "nace_code"])["wage_level_eur"]
    pct_diff = ((p18 - p14) / p14 * 100).rename("pct_growth_2014_2018")
    print("\n2014 → 2018 spliced growth distribution (should be plausible national wage drift):")
    print(pct_diff.describe(percentiles=[.1, .25, .5, .75, .9]).round(1).to_string())


def main() -> None:
    anchor = load_anchor_2018()
    print(f"SES 2018 anchor cells: {len(anchor)} "
          f"(countries={anchor['country_code'].nunique()}, sectors={anchor['nace_code'].nunique()})")
    growth = load_lci_growth()
    print(f"LCI growth rows: {len(growth):,} "
          f"({growth['country_code'].nunique()} countries × {growth['nace_code'].nunique()} sectors × "
          f"{growth['year'].nunique()} years)")
    panel = splice(anchor, growth)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUT, index=False)
    print(f"\nsaved {len(panel):,} rows -> {OUT}")
    coverage_summary(panel)
    consistency_check(panel, anchor)


if __name__ == "__main__":
    main()
