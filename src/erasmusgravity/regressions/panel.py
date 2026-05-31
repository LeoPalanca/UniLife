"""Panel-gravity specs: country two-stage, city two-stage, OWID time-varying, QS multi-year."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from ..db import read_table, table_names
from .common import Recorder, TERM_META, country_qol

COUNTRY_PANEL = "erasmus_country_year_panel"
CITY_PANEL = "erasmus_he_city_year_panel"
ERASMUSU = "erasmusu_city_ratings"
OWID = "owid_country_year"


def fit_panel_two_stage(rec: Recorder) -> None:
    """Stage 1: panel PPML -> destination attractiveness FEs. Stage 2: QoL explains them."""
    panel = read_table(COUNTRY_PANEL)
    print(f"\n--- Panel gravity (country x country x year, {panel['year'].min()}-{panel['year'].max()}) ---")
    print(f"  rows: {len(panel):,} | pairs: {panel.groupby(['sending_code','receiving_code']).ngroups:,}")

    print("\n=== Stage 1: PPML, origin + destination + year FE -> destination attractiveness ===")
    m = smf.glm("flow_count ~ C(sending_code) + C(receiving_code) + C(year)",
                data=panel, family=sm.families.Poisson()).fit()
    yr = {i.split("[T.")[1].rstrip("]"): v for i, v in m.params.items()
          if i.startswith("C(year)[T.")}
    print("  year FE (vs base):", {k: round(v, 2) for k, v in sorted(yr.items())})
    base_year = int(panel["year"].min())
    rec.record_year(base_year, 0.0)
    for k, v in sorted(yr.items()):
        rec.record_year(int(k), float(v))
    fe = {i.split("[T.")[1].rstrip("]"): v for i, v in m.params.items()
          if i.startswith("C(receiving_code)[T.")}
    dest = pd.DataFrame({"receiving_code": list(fe), "dest_fe": list(fe.values())})
    print(f"  extracted {len(dest)} destination attractiveness FEs")

    print("\n=== Stage 2: destination FE ~ QoL (+ destination economics), cross-section ===")
    d = dest.merge(country_qol(), on="receiving_code", how="left")
    for qcol, label in (("qol_erasmusu", "Erasmusu rating"), ("qol_reddit", "Reddit sentiment")):
        sub = d.dropna(subset=["dest_fe", qcol])
        if len(sub) < 5:
            continue
        s2 = smf.ols(
            f"dest_fe ~ {qcol} + receiver_gdp_pc_current_usd_wb + receiver_price_level_aic_eu27_2020_100",
            data=sub).fit()
        b, p = s2.params.get(qcol), s2.pvalues.get(qcol)
        print(f"  {label:16s}: N={int(s2.nobs):>3}  beta={b:+.4e}  p={p:.3f}  R2={s2.rsquared:.2f}")
        rec.record(f"Two-stage COUNTRY: {label}", "panel dest-FE ~ QoL", qcol,
                   b, p, int(s2.nobs), "country-level (underpowered)")


def fit_city_panel_two_stage(rec: Recorder) -> None:
    """City-level two-stage: panel PPML -> city destination FEs, then QoL explains them."""
    panel = read_table(CITY_PANEL)
    eu = read_table(ERASMUSU).dropna(subset=["rating_10", "country_code", "city_norm"]).copy()
    eu["dest_id"] = eu["country_code"] + ":" + eu["city_norm"]
    panel["dest_id"] = panel["receiving_code"] + ":" + panel["city_norm"]
    pm = panel[panel["dest_id"].isin(set(eu["dest_id"]))].copy()
    print("\n--- City-level panel two-stage (HE study, 2014-2023) ---")
    print(f"  panel rows (Erasmusu-matched dests): {len(pm):,} | dest cities: {pm['dest_id'].nunique()}")

    print("\n=== Stage 1: PPML, origin + city-destination + year FE -> city attractiveness ===")
    m = smf.glm("flow_count ~ C(sending_code) + C(dest_id) + C(year)",
                data=pm, family=sm.families.Poisson()).fit()
    fe = {i.split("[T.")[1].rstrip("]"): v for i, v in m.params.items()
          if i.startswith("C(dest_id)[T.")}
    dest = pd.DataFrame({"dest_id": list(fe), "city_fe": list(fe.values())})
    print(f"  extracted {len(dest)} city attractiveness FEs")

    print("\n=== Stage 2: city FE ~ Erasmusu rating (opinion-weighted), country-clustered ===")
    d = dest.merge(eu[["dest_id", "country_code", "rating_10", "n_opinions"]],
                   on="dest_id", how="left").dropna()
    s2 = smf.wls("city_fe ~ rating_10", data=d, weights=d["n_opinions"]).fit()
    b, p = s2.params["rating_10"], s2.pvalues["rating_10"]
    cl = s2.get_robustcov_results(cov_type="cluster",
                                  groups=pd.factorize(d["country_code"])[0])
    ci = list(s2.params.index).index("rating_10")
    print(f"  N={int(s2.nobs)} cities | {d['country_code'].nunique()} countries")
    print(f"  rating_10 beta={b:+.4e}  naive p={p:.3f}  R2={s2.rsquared:.2f}")
    print(f"  cluster-by-country p={cl.pvalues[ci]:.3f}")
    rec.record("Two-stage CITY: Erasmusu rating",
               "panel city-FE ~ QoL (country-clustered)", "rating_10",
               b, cl.pvalues[ci], int(s2.nobs),
               f"{d['country_code'].nunique()} countries — HEADLINE")


def fit_panel_owid(rec: Recorder) -> None:
    """Time-varying panel test using OWID country-year terms (Cantril, education spend)."""
    if OWID not in table_names():
        return
    panel = read_table(COUNTRY_PANEL)
    owid = read_table(OWID)
    pm = panel.merge(owid, on=["receiving_code", "year"], how="left")
    print("\n--- Time-varying panel (OWID country-year terms, 2014-2023) ---")

    for term in ["life_satisfaction", "edu_spend_gdp"]:
        d = pm.dropna(subset=["flow_count", term]).copy()
        if d[term].nunique() < 5:
            continue
        sym, lbl, _ = TERM_META.get(term, ("", term, ""))
        m = smf.glm(f"flow_count ~ {term} + C(sending_code) + C(receiving_code) + C(year)",
                    data=d, family=sm.families.Poisson()).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(d["receiving_code"])[0]})
        b, p = m.params[term], m.pvalues[term]
        sd = float(d[term].std())
        print(f"  {sym} {term:18s} beta={b:+.4e}  p={p:.3f}  "
              f"per-SD={np.exp(b * sd) - 1:+.1%}  (N={int(m.nobs)}, dest-clustered)")
        rec.record(f"Panel time-varying: {lbl}",
                   "panel PPML, origin+dest+year FE (dest-clustered)",
                   term, b, p, int(m.nobs),
                   f"{d['receiving_code'].nunique()} destinations, per-SD {np.exp(b*sd)-1:+.0%}")


def fit_panel_inst_quality(rec: Recorder) -> None:
    """Time-varying β₃ on the city-year panel (QS multi-edition splice)."""
    if "institution_quality_panel" not in table_names() or CITY_PANEL not in table_names():
        return
    panel = read_table(CITY_PANEL)
    iq = read_table("institution_quality_panel")[
        ["receiving_code", "city_norm", "year", "best_score"]]
    pm = panel.merge(iq, on=["receiving_code", "city_norm", "year"], how="left")
    d = pm.dropna(subset=["flow_count", "best_score"]).copy()
    if d["best_score"].nunique() < 5:
        return
    print("\n--- Time-varying β₃ panel (institution_quality_panel) ---")
    d["dest_city"] = d["receiving_code"] + ":" + d["city_norm"]
    m = smf.glm("flow_count ~ best_score + C(sending_code) + C(dest_city) + C(year)",
                data=d, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["dest_city"])[0]})
    b, p = m.params["best_score"], m.pvalues["best_score"]
    sd = float(d["best_score"].std())
    print(f"  β₃ best_score (panel) beta={b:+.4e}  p={p:.3f}  "
          f"per-SD={np.exp(b * sd) - 1:+.1%}  (N={int(m.nobs)}, city-clustered)")
    rec.record("Panel time-varying: Institution quality (QS multi-year)",
               "panel PPML, origin + dest-city + year FE (city-clustered)",
               "best_score", b, p, int(m.nobs),
               f"{d['dest_city'].nunique()} cities × {d['year'].nunique()} years, "
               f"per-SD {np.exp(b*sd)-1:+.0%}")
