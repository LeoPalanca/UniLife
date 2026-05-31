"""Temporal Erasmus+ panel built from the Väisänen et al. (2025) geolocated dataset.

The source parquet covers 2014-2023 with pre-computed LAU (city) and NUTS3 (region)
codes. We filter to Higher Education study mobilities (the same scope as the
single-year KA1 pipeline) and aggregate to bilateral panels for gravity modelling.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_PANEL = Path("data/raw/Erasmus_2014-2023_individual.parquet")

_LOAD_COLUMNS = [
    "Activity (mob)",
    "Field",
    "Participant Age",
    "Sending Country",
    "Receiving Country",
    "o_country",
    "d_country",
    "orig_LAU",
    "dest_LAU",
    "orig_NUTS",
    "dest_NUTS",
    "year",
    "Actual Participants",
]


def _country_code(value: object) -> str | None:
    """Extract the 2-letter code from a "XX - Name" country string."""
    if not isinstance(value, str) or len(value) < 2:
        return None
    code = value[:2].upper()
    return code if code.isalpha() else None


def load_panel_individual(path: Path = RAW_PANEL) -> pd.DataFrame:
    """Load and filter the individual-level panel to cross-border HE study mobility.

    Filters mirror the single-year KA1 pipeline: Higher Education field, study
    activity (not traineeships), plausible adult age, and distinct origin/destination
    countries. ``weight`` carries the number of identical participants per row.
    """
    df = pd.read_parquet(path, columns=_LOAD_COLUMNS)

    df = df[df["Field"] == "Higher Education"]
    df = df[df["Activity (mob)"].str.contains("studies", case=False, na=False)]
    df = df[df["Participant Age"].between(18, 100)]

    df = df.assign(
        sending_code=df["Sending Country"].map(_country_code),
        receiving_code=df["Receiving Country"].map(_country_code),
        weight=df["Actual Participants"].fillna(1).astype(int),
    )
    df = df.dropna(subset=["sending_code", "receiving_code"])
    df = df[df["sending_code"] != df["receiving_code"]]
    return df


def aggregate_country_year(df: pd.DataFrame) -> pd.DataFrame:
    """Bilateral country x country x year flow panel."""
    grouped = (
        df.groupby(
            ["sending_code", "o_country", "receiving_code", "d_country", "year"],
            dropna=False,
        )["weight"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "o_country": "sending_country",
                "d_country": "receiving_country",
                "weight": "flow_count",
            }
        )
    )
    return grouped.sort_values(["year", "flow_count"], ascending=[True, False])


def aggregate_geo_year(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Bilateral flow panel at a geocoded level ("LAU" city or "NUTS" region)."""
    orig, dest = f"orig_{level}", f"dest_{level}"
    sub = df.dropna(subset=[orig, dest])
    grouped = (
        sub.groupby([orig, dest, "year"])["weight"].sum().reset_index()
        .rename(columns={orig: "origin", dest: "destination", "weight": "flow_count"})
    )
    return grouped.sort_values(["year", "flow_count"], ascending=[True, False])


def build_panels(path: Path = RAW_PANEL) -> dict[str, pd.DataFrame]:
    df = load_panel_individual(path)
    return {
        "country_year": aggregate_country_year(df),
        "lau_year": aggregate_geo_year(df, "LAU"),
        "nuts_year": aggregate_geo_year(df, "NUTS"),
    }
