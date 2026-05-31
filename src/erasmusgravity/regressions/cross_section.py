"""Cross-sectional specs (Spec C-K) on the city-pair flow panel."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..db import read_table, table_names
from .common import (
    GAP_COLS,
    Recorder,
    add_gravity_terms,
    city_quality_of_life,
    erasmusu_city_qol,
    norm_city,
    quality_of_life,
)
from .fit import cross_sectional, ppml, print_vif, within_country_cluster

CITY_FLOWS = "erasmus_city_flows_long"
FLOWS = "ka1_he_studies_flows_with_indicators"
INSTQ = "institution_quality"
USERINSTQ = "user_institution_quality"


def _zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def fit_city_spec(rec: Recorder) -> None:
    """Run Specs C through K on the city-pair flow table."""
    gaps = read_table(FLOWS)[
        ["sending_code", "receiving_code", "earnings_gap", "price_level_gap", "gdp_gap_usd_wb"]
    ].drop_duplicates(["sending_code", "receiving_code"])

    cf = read_table(CITY_FLOWS).merge(gaps, on=["sending_code", "receiving_code"], how="left")
    # Rescale earnings_gap to €1,000 units so PPML β is publication-readable.
    cf["earnings_gap"] = cf["earnings_gap"] / 1000.0
    cf["cc"] = cf["receiving_country"].str.lower().str.strip()
    cf["ck"] = cf["receiving_city"].map(norm_city)
    cf = cf.merge(city_quality_of_life(), on=["cc", "ck"], how="left")
    cf = cf.merge(
        erasmusu_city_qol(),
        left_on=["receiving_code", "ck"],
        right_on=["country_code", "city_norm"], how="left",
    )
    cf = cf.merge(
        quality_of_life()[["receiving_country", "qol"]].rename(columns={"qol": "qol_country"}),
        on="receiving_country", how="left",
    )
    cf = add_gravity_terms(cf)

    if INSTQ in table_names():
        iq = read_table(INSTQ).rename(columns={"city_norm": "ck", "best_score": "inst_quality"})
        cf = cf.merge(iq[["receiving_code", "ck", "inst_quality"]],
                      on=["receiving_code", "ck"], how="left")
        cf["inst_quality"] = cf["inst_quality"].fillna(0.0)
    if USERINSTQ in table_names():
        uq = read_table(USERINSTQ).rename(
            columns={"city_norm": "ck", "best_user_score": "user_inst_quality"})
        cf = cf.merge(uq[["receiving_code", "ck", "user_inst_quality"]],
                      on=["receiving_code", "ck"], how="left")
        cf["user_inst_quality"] = cf["user_inst_quality"].fillna(0.0)
    cf["y"] = np.log1p(cf["flow_count"])

    print("\n=== Spec C: Reddit city sentiment, receiving-COUNTRY FE ===")
    rc = cf.dropna(subset=["y", "qol_city", "sending_code", "receiving_code"]).copy()
    within_country_cluster(rec, rc,
        "y ~ qol_city + C(sending_code) + C(receiving_code)", "qol_city",
        spec="Spec C: Reddit city sentiment (within-country)")

    print("\n=== Spec D: Erasmusu rating (n_opinions>=5), opinion-weighted, receiving-COUNTRY FE ===")
    ed = cf.dropna(subset=["y", "rating_10", "sending_code", "receiving_code"]).copy()
    ed = ed[ed["n_opinions"] >= 5]
    within_country_cluster(rec, ed,
        "y ~ rating_10 + C(sending_code) + C(receiving_code)", "rating_10",
        weight_col="n_opinions", spec="Spec D: Erasmusu rating (within-country)")

    # Correlation between the two QoL measures on the overlap (city level)
    city = cf.dropna(subset=["qol_city", "rating_10"]).drop_duplicates(["receiving_code", "ck"])
    if len(city) > 2:
        r = city["qol_city"].corr(city["rating_10"])
        print(f"\n  Reddit vs Erasmusu overlap: {len(city)} cities | corr = {r:.3f}")

    print("\n=== Spec E: combined QoL (z Erasmusu -> z Reddit-city -> z Reddit-country), COUNTRY FE ===")
    ctab = cf.drop_duplicates(["receiving_code", "ck"]).copy()
    z_eu = _zscore(ctab["rating_10"])
    z_rc = _zscore(ctab["qol_city"])
    z_co = _zscore(ctab["qol_country"])
    ctab["qol_combined"] = z_eu.where(z_eu.notna(), z_rc.where(z_rc.notna(), z_co))
    cf = cf.merge(ctab[["receiving_code", "ck", "qol_combined"]],
                  on=["receiving_code", "ck"], how="left")
    cm = cf.dropna(subset=["y", "qol_combined", "sending_code", "receiving_code"]).copy()
    within_country_cluster(rec, cm,
        "y ~ qol_combined + C(sending_code) + C(receiving_code)", "qol_combined",
        spec="Spec E: combined QoL (within-country)")

    gapvars = "earnings_gap + price_level_gap + gdp_gap_usd_wb"
    print("\n=== Spec F: Erasmusu rating, CROSS-SECTIONAL (no receiver FE, gap controls) ===")
    fd = cf.dropna(subset=["y", "rating_10", *GAP_COLS, "sending_code"]).copy()
    fd = fd[fd["n_opinions"] >= 5]
    cross_sectional(rec, fd, f"y ~ rating_10 + {gapvars} + C(sending_code)", "rating_10",
                    weight_col="n_opinions",
                    spec="Spec F: Erasmusu rating (cross-sectional)")

    print("\n=== Spec G: combined QoL, CROSS-SECTIONAL (no receiver FE, gap controls) ===")
    gd = cf.dropna(subset=["y", "qol_combined", *GAP_COLS, "sending_code"]).copy()
    cross_sectional(rec, gd, f"y ~ qol_combined + {gapvars} + C(sending_code)", "qol_combined",
                    spec="Spec G: combined QoL (cross-sectional)")

    print("\n=== Spec H: Erasmusu rating, PPML (Poisson on flow level, the proper gravity estimator) ===")
    hd = cf.dropna(subset=["flow_count", "rating_10", *GAP_COLS, "sending_code"]).copy()
    hd = hd[hd["n_opinions"] >= 5]
    ppml(rec, hd, f"flow_count ~ rating_10 + {gapvars} + C(sending_code)", "rating_10")

    print("\n=== Spec I: headline PPML + distance + language affinity (full gravity terms) ===")
    full = ("flow_count ~ rating_10 + " + gapvars +
            " + log_distance + same_language + C(sending_code)")
    hi = cf.dropna(subset=["flow_count", "rating_10", *GAP_COLS,
                           "log_distance", "same_language", "sending_code"]).copy()
    hi = hi[hi["n_opinions"] >= 5]
    ppml(rec, hi, full, "rating_10",
         spec="Spec I: full-gravity PPML (distance + language)")

    if "inst_quality" in cf.columns:
        # HEADLINE spec: gdp_gap_usd_wb is the broad prosperity control (per
        # reports/gravity_model.md §3). earnings_gap and price_level_gap are demoted to
        # Spec J-robust (collinear with each other and with gdp_gap; VIF ~5-7).
        print("\n=== Spec J-main: headline gravity (gdp_gap_usd_wb only; drops salary/price-level) ===")
        main_formula = ("flow_count ~ rating_10 + gdp_gap_usd_wb + log_distance + same_language"
                        " + inst_quality + C(sending_code)")
        hjm = cf.dropna(subset=["flow_count", "rating_10", "gdp_gap_usd_wb", "log_distance",
                                "same_language", "inst_quality", "sending_code"]).copy()
        hjm = hjm[hjm["n_opinions"] >= 5]
        ppml(rec, hjm, main_formula, "rating_10",
             spec="Spec J-main: headline gravity (gdp_gap only, no salary/price)",
             record_coeffs=True, print_full=True)
        print_vif(hjm, ["rating_10", "gdp_gap_usd_wb", "log_distance",
                        "same_language", "inst_quality"])

        print("\n=== Spec J-robust: full economic controls (exploratory, multicollinear) ===")
        fullj = full + " + inst_quality"
        hj = cf.dropna(subset=["flow_count", "rating_10", *GAP_COLS, "log_distance",
                               "same_language", "inst_quality", "sending_code"]).copy()
        hj = hj[hj["n_opinions"] >= 5]
        ppml(rec, hj, fullj, "rating_10",
             spec="Spec J-robust: full controls (+ gdp_gap + price_level_gap, exploratory)",
             print_full=True)
        print_vif(hj, ["rating_10", *GAP_COLS, "log_distance",
                       "same_language", "inst_quality"])
    else:
        print_vif(hi, ["rating_10", *GAP_COLS, "log_distance", "same_language"])

    if "user_inst_quality" in cf.columns and "inst_quality" in cf.columns:
        # Cross-check: QS (expert/metric) vs StudyPortals (student/user) institution quality
        both = cf.drop_duplicates(["receiving_code", "ck"])
        both = both[(both["inst_quality"] > 0) & (both["user_inst_quality"] > 0)]
        if len(both) > 2:
            r = both["inst_quality"].corr(both["user_inst_quality"])
            print(f"\n  QS vs StudyPortals institution quality: {len(both)} cities | corr = {r:.3f}")

        print("\n=== Spec K: complete gravity, beta3 = StudyPortals student rating (user-based cross-check) ===")
        fullk = full + " + user_inst_quality"
        hk = cf.dropna(subset=["flow_count", "rating_10", *GAP_COLS, "log_distance",
                               "same_language", "user_inst_quality", "sending_code"]).copy()
        hk = hk[hk["n_opinions"] >= 5]
        ppml(rec, hk, fullk, "user_inst_quality",
             spec="Spec K: beta3 = StudyPortals student rating (cross-check)")
