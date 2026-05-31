"""Gravity-model regression specifications.

Each submodule fits a family of specs and appends rows to a `Recorder` (see
`common.Recorder`). The runner script (`scripts/run_regression.py`) wires the
shared context across modules and persists results to the SQLite DB.
"""
from .common import (
    GAP_COLS,
    Recorder,
    SENTIMENT_SCORE,
    TERM_META,
    add_gravity_terms,
    city_quality_of_life,
    country_qol,
    erasmusu_city_qol,
    norm_city,
    quality_of_life,
    sentiment_series,
    show,
)
from .covid import fit_covid_did, fit_covid_did_employment
from .cross_section import fit_city_spec
from .fit import cross_sectional, ppml, print_vif, within_country_cluster
from .panel import (
    fit_city_panel_two_stage,
    fit_panel_inst_quality,
    fit_panel_owid,
    fit_panel_two_stage,
)

__all__ = [
    "GAP_COLS", "Recorder", "SENTIMENT_SCORE", "TERM_META",
    "add_gravity_terms", "city_quality_of_life", "country_qol",
    "erasmusu_city_qol", "norm_city", "quality_of_life", "sentiment_series", "show",
    "fit_covid_did", "fit_covid_did_employment", "fit_city_spec",
    "fit_city_panel_two_stage", "fit_panel_inst_quality", "fit_panel_owid",
    "fit_panel_two_stage", "cross_sectional", "ppml", "print_vif",
    "within_country_cluster",
]
