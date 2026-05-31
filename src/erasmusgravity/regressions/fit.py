"""Fitting primitives: OLS/WLS with FE clustering, cross-section OLS, and PPML."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from .common import Recorder, TERM_META, show


def within_country_cluster(rec: Recorder, dat: pd.DataFrame, formula: str, term: str,
                           weight_col: str | None = None, spec: str = "") -> None:
    """OLS/WLS with two-way FE; print naive + cluster-by-{city,country} SE for `term`.

    Restricts to receiving codes with ≥2 distinct cities so within-country
    identification is well-defined.
    """
    multi = dat.groupby("receiving_code")["ck"].transform("nunique") >= 2
    dat = dat[multi].reset_index(drop=True)
    if weight_col:
        m = smf.wls(formula, data=dat, weights=dat[weight_col]).fit()
    else:
        m = smf.ols(formula, data=dat).fit()
    print(f"  rows: {len(dat)} | cities: {dat['ck'].nunique()} | "
          f"countries: {dat['receiving_code'].nunique()}")
    show(m, [term])
    print(f"  N={int(m.nobs)}  R2={m.rsquared:.3f}")
    idx = list(m.params.index).index(term)
    p_city = None
    for label, col in (("city", "ck"), ("country", "receiving_code")):
        cl = m.get_robustcov_results(cov_type="cluster",
                                     groups=pd.factorize(dat[col])[0])
        print(f"  cluster-by-{label:7s} ({dat[col].nunique():>3} clusters): "
              f"beta={cl.params[idx]:+.4e}  p={cl.pvalues[idx]:.3f}")
        if label == "city":
            p_city = cl.pvalues[idx]
    if spec:
        rec.record(spec, "within-country (city-clustered)", term,
                   m.params[term], p_city, int(m.nobs),
                   f"{dat['ck'].nunique()} cities / {dat['receiving_code'].nunique()} countries")


def cross_sectional(rec: Recorder, dat: pd.DataFrame, formula: str, term: str,
                    weight_col: str | None = None, spec: str = "") -> None:
    """Cross-sectional OLS/WLS with sending-FE only, cluster by city."""
    dat = dat.reset_index(drop=True)
    if weight_col:
        m = smf.wls(formula, data=dat, weights=dat[weight_col]).fit()
    else:
        m = smf.ols(formula, data=dat).fit()
    print(f"  rows: {len(dat)} | cities: {dat['ck'].nunique()} | "
          f"countries: {dat['receiving_code'].nunique()}")
    show(m, [term])
    print(f"  N={int(m.nobs)}  R2={m.rsquared:.3f}")
    idx = list(m.params.index).index(term)
    cl = m.get_robustcov_results(cov_type="cluster",
                                 groups=pd.factorize(dat["ck"])[0])
    print(f"  cluster-by-city ({dat['ck'].nunique():>3} clusters): "
          f"beta={cl.params[idx]:+.4e}  p={cl.pvalues[idx]:.3f}")
    if spec:
        rec.record(spec, "cross-sectional (city-clustered)", term,
                   m.params[term], cl.pvalues[idx], int(m.nobs),
                   f"{dat['ck'].nunique()} cities")


def ppml(rec: Recorder, dat: pd.DataFrame, formula: str, term: str,
         spec: str = "Spec H: Erasmusu PPML (cross-sectional)",
         record_coeffs: bool = False, print_full: bool = False) -> None:
    """Poisson PML on the flow level, city-clustered SEs (Santos Silva & Tenreyro 2006)."""
    dat = dat.reset_index(drop=True)
    m = smf.glm(formula, data=dat, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(dat["ck"])[0]})
    print(f"  rows: {len(dat)} | cities: {dat['ck'].nunique()} | "
          f"countries: {dat['receiving_code'].nunique()}")
    b, p = m.params[term], m.pvalues[term]
    print(f"  {term:18s} beta={b:+.4e}  p={p:.3f}  "
          f"(exp(beta)-1 = {np.exp(b) - 1:+.1%} per unit)")
    rec.record(spec, "PPML / city-clustered", term, b, p, int(m.nobs),
               f"+{np.exp(b) - 1:.0%} flow per rating point")
    if print_full or record_coeffs:
        print(f"  {'term':22s} {'beta':>14s} {'SE':>11s} {'z':>7s} {'p':>7s} {'%/SD':>9s}")
        for name in m.params.index:
            if name.startswith("C(") or name == "Intercept":
                continue
            coef = float(m.params[name])
            se = float(m.bse[name])
            z = float(m.tvalues[name])
            pv = float(m.pvalues[name])
            sd = float(dat[name].std()) if name in dat.columns else 1.0
            pct = (np.exp(coef * sd) - 1) * 100
            sig = " *" if pv < 0.05 else "  "
            print(f"  {name:22s} {coef:+14.4e} {se:11.3e} {z:+7.2f} {pv:7.3f} {pct:+8.2f}%{sig}")
    if not record_coeffs:
        return
    # Record every estimated beta from this headline model (skip FE dummies + intercept).
    for name in m.params.index:
        if name.startswith("C(") or name == "Intercept":
            continue
        sym, lbl, sign = TERM_META.get(name, ("control", name, ""))
        coef = float(m.params[name])
        sd = float(dat[name].std()) if name in dat.columns else 1.0
        rec.model_coeffs.append({
            "symbol": sym, "variable": lbl, "term": name,
            "beta": round(coef, 6), "p": round(float(m.pvalues[name]), 4),
            "pct_per_sd": round(float(np.exp(coef * sd) - 1), 4),
            "expected_sign": sign,
        })


def print_vif(dat: pd.DataFrame, cols: list[str]) -> None:
    """Variance inflation factors — check whether controls are collinear."""
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    x = dat[cols].dropna().reset_index(drop=True)
    x = sm.add_constant(x)
    print("  VIF (>5 = collinear, >10 = severe):")
    for i, c in enumerate(x.columns):
        if c == "const":
            continue
        print(f"    {c:18s} {variance_inflation_factor(x.values, i):6.2f}")
