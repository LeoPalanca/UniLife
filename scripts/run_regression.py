"""Run all gravity-model specs and persist results to the SQLite DB.

Cross-section (Spec C-K) + panel (country + city two-stage + OWID + QS multi-year)
+ COVID DiD (LCI wage and LFS employment treatments). Each fit_* function takes
a shared `Recorder` (no global state). Results land in three tables:

  regression_results    : one row per (spec, term) summary
  panel_year_effects    : year-FE points for the year-FE chart
  model_coefficients    : every estimated β from the headline Spec J-main

The runner also prints a small Spec A/B preface (full-FE + sender-FE-only
country-level gravity, kept as transparency baselines for the design step).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.db import get_conn, read_table, write_table
from erasmusgravity.regressions import (
    GAP_COLS,
    Recorder,
    fit_city_panel_two_stage,
    fit_city_spec,
    fit_covid_did,
    fit_covid_did_employment,
    fit_panel_inst_quality,
    fit_panel_owid,
    fit_panel_two_stage,
    quality_of_life,
    show,
)


def main() -> None:
    rec = Recorder()
    flows = read_table("ka1_he_studies_flows_with_indicators")
    qol = quality_of_life()

    # Match Reddit country names to receiving-country names (case-insensitive)
    flows["_key"] = flows["receiving_country"].str.strip().str.lower()
    qol["_key"] = qol["receiving_country"].str.strip().str.lower()
    df = flows.merge(qol.drop(columns="receiving_country"), on="_key", how="left")
    df["y"] = np.log1p(df["flow_count"])

    matched = qol["_key"].isin(flows["_key"]).sum()
    print(f"Reddit countries: {len(qol)} | matched to flows: {matched}")

    base = df.dropna(subset=["y"] + GAP_COLS)
    print(f"\nRows total: {len(df)} | with all gap covariates: {len(base)}")

    print("\n=== Spec A: full FE gravity (bilateral betas; QoL not identifiable) ===")
    a = smf.ols(
        "y ~ earnings_gap + price_level_gap + gdp_gap_usd_wb + C(sending_code) + C(receiving_code)",
        data=base,
    ).fit()
    show(a, GAP_COLS)
    print(f"  N={int(a.nobs)}  R2={a.rsquared:.3f}")

    print("\n=== Spec B: sender FE only, QoL identified ===")
    bdat = base.dropna(subset=["qol"])
    print(f"  rows with QoL too: {len(bdat)}")
    b = smf.ols(
        "y ~ earnings_gap + price_level_gap + gdp_gap_usd_wb + qol + C(sending_code)",
        data=bdat,
    ).fit()
    show(b, [*GAP_COLS, "qol"])
    print(f"  N={int(b.nobs)}  R2={b.rsquared:.3f}")

    print("\n--- City-level QoL (within-country identification) ---")
    fit_city_spec(rec)

    fit_panel_two_stage(rec)
    fit_city_panel_two_stage(rec)
    fit_panel_owid(rec)
    fit_panel_inst_quality(rec)
    fit_covid_did(rec)
    fit_covid_did_employment(rec)

    # Persist so the dashboard can render them.
    conn = get_conn()
    write_table(pd.DataFrame(rec.results), "regression_results", conn)
    write_table(pd.DataFrame(rec.panel_years), "panel_year_effects", conn)
    write_table(pd.DataFrame(rec.model_coeffs), "model_coefficients", conn)
    conn.commit()
    conn.close()
    print(f"\nWrote {len(rec.results)} results + {len(rec.panel_years)} year effects + "
          f"{len(rec.model_coeffs)} coefficients to DB.")


if __name__ == "__main__":
    main()
