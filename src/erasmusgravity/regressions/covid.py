"""COVID-2020 sector-DiD specs on the (origin, destination, field, year) flow panel.

`fit_covid_did()` uses LCI wage-growth as the treatment intensity; the sign came
out counterintuitive because the LCI is contaminated by wage-subsidy schemes.
`fit_covid_did_employment()` swaps the treatment to LFS employment deviation,
which is not subsidy-contaminated — used as the clean replication.

Both persist their event-study trajectories to `covid_event_study` and
`covid_event_study_employment` for dashboard rendering.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from ..db import get_conn, read_table, table_names, write_table
from .common import Recorder

FIELD_PANEL = "erasmus_field_flow_panel"
COVID_HIT = "covid_sector_hit"
COVID_EMP_HIT = "covid_employment_hit"


def _build_did_panel(treatment_col: str, treatment_table: str) -> pd.DataFrame | None:
    """Merge field panel + sector-hit treatment; drop hyperinflation regimes."""
    from ..fields import ISCED_TO_NACE

    if FIELD_PANEL not in table_names() or treatment_table not in table_names():
        return None
    panel = read_table(FIELD_PANEL).copy()
    hit = read_table(treatment_table)[["receiving_code", "nace_r2", treatment_col]]

    panel["isced_broad"] = panel["isced_broad"].astype(str).str.zfill(2)
    panel["nace_r2"] = panel["isced_broad"].map(ISCED_TO_NACE)
    d = panel.dropna(subset=["nace_r2"]).merge(hit, on=["receiving_code", "nace_r2"], how="left")
    d = d[d["receiving_code"] != "TR"]  # hyperinflation distortion
    d = d.dropna(subset=[treatment_col])
    d["post"] = (d["year"] >= 2021).astype(int)
    d["jf"] = d["receiving_code"] + ":" + d["isced_broad"]
    return d


def _did_event_study(d: pd.DataFrame, treatment_col: str, event_col_prefix: str,
                     out_table: str) -> None:
    """Year-by-year event-study, persisted to `out_table`."""
    e = d[d["year"].between(2015, 2023)].copy()
    e["year"] = e["year"].astype(int)
    yr_terms: list[str] = []
    for yr in sorted(e["year"].unique()):
        if yr == 2019:
            continue
        col = f"{event_col_prefix}{yr}"
        e[col] = e[treatment_col] * (e["year"] == yr).astype(int)
        yr_terms.append(col)
    formula = "flow_count ~ " + " + ".join(yr_terms) + " + C(jf) + C(sending_code) + C(year)"
    es = smf.glm(formula, data=e, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(e["jf"])[0]})

    print(f"  year | β({treatment_col} x year) | p (cell-clustered)")
    rows: list[dict] = []
    for t in yr_terms:
        yr = int(t.replace(event_col_prefix, ""))
        rows.append({"year": yr, "beta": float(es.params[t]), "p": float(es.pvalues[t])})
    for r in sorted(rows, key=lambda x: x["year"]):
        sym = "*" if r["p"] < 0.05 else " "
        print(f"  {r['year']}   {r['beta']:+.4e}   p={r['p']:.3f}  {sym}")

    if rows:
        conn = get_conn()
        write_table(pd.DataFrame(rows), out_table, conn)
        conn.commit(); conn.close()


def fit_covid_did(rec: Recorder) -> None:
    """LCI wage-growth treatment (the contaminated channel)."""
    d = _build_did_panel("covid_hit_pp", COVID_HIT)
    if d is None:
        return
    d["covid_post"] = d["covid_hit_pp"] * d["post"]

    print("\n--- COVID-2020 sector-DiD on field-level flows ---")
    print(f"  rows: {len(d):,} | (dest, field) cells: {d['jf'].nunique()} | "
          f"origins: {d['sending_code'].nunique()} | years: {d['year'].min()}-{d['year'].max()}")

    print("\n=== COVID DiD: PPML, dest x field FE + sending FE + year FE ===")
    m = smf.glm("flow_count ~ covid_post + C(jf) + C(sending_code) + C(year)",
                data=d, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["jf"])[0]})
    b, p = m.params["covid_post"], m.pvalues["covid_post"]
    sd = float(d["covid_post"].std())
    print(f"  covid_hit x Post:  beta={b:+.4e}  p={p:.3f}  per-SD={np.exp(b*sd)-1:+.1%}  N={int(m.nobs)}")
    rec.record("COVID DiD: sector hit x post-2020",
               "PPML, destXfield + sending + year FE (cell-clustered)",
               "covid_post", b, p, int(m.nobs),
               f"{d['jf'].nunique()} cells, per-SD {np.exp(b*sd)-1:+.0%}")

    print("\n=== COVID event-study: covid_hit x year (2019 = baseline) ===")
    _did_event_study(d, "covid_hit_pp", "hit_y", "covid_event_study")


def fit_covid_did_employment(rec: Recorder) -> None:
    """Employment-based replication (the clean channel, subsidy-free)."""
    d = _build_did_panel("covid_emp_hit_pp", COVID_EMP_HIT)
    if d is None:
        return
    d["covid_emp_post"] = d["covid_emp_hit_pp"] * d["post"]

    print("\n--- COVID-2020 sector-DiD on field-level flows (employment-based) ---")
    print(f"  rows: {len(d):,} | (dest, field) cells: {d['jf'].nunique()} | "
          f"origins: {d['sending_code'].nunique()} | years: {d['year'].min()}-{d['year'].max()}")

    print("\n=== COVID DiD (employment): PPML, dest x field FE + sending FE + year FE ===")
    m = smf.glm("flow_count ~ covid_emp_post + C(jf) + C(sending_code) + C(year)",
                data=d, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["jf"])[0]})
    b, p = m.params["covid_emp_post"], m.pvalues["covid_emp_post"]
    sd = float(d["covid_emp_post"].std())
    print(f"  covid_emp_hit x Post:  beta={b:+.4e}  p={p:.3f}  per-SD={np.exp(b*sd)-1:+.1%}  N={int(m.nobs)}")
    rec.record("COVID DiD (employment): sector hit x post-2020",
               "PPML, destXfield + sending + year FE (cell-clustered)",
               "covid_emp_post", b, p, int(m.nobs),
               f"{d['jf'].nunique()} cells, per-SD {np.exp(b*sd)-1:+.0%}")

    print("\n=== COVID event-study (employment): covid_emp_hit x year (2019 = baseline) ===")
    _did_event_study(d, "covid_emp_hit_pp", "emp_hit_y", "covid_event_study_employment")
