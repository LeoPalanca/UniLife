from __future__ import annotations

from pathlib import Path

import country_converter as coco
import pandas as pd


RAW_ANNEX = Path("data/raw/annual-report-2024-statistical-annex.xlsx")
GRANTS_SHEET = "KA1_estimated paxs"


def country_name_to_code(names: pd.Series) -> pd.Series:
    """Convert annex country names to the ISO2-like codes used in the Erasmus flow file."""
    converted = coco.convert(names=names.tolist(), to="ISO2", not_found=None)
    converted = pd.Series(converted, index=names.index, dtype="object")
    return converted.replace({"GB": "UK", "GR": "EL"})


def load_he_grants(path: str | Path = RAW_ANNEX, call_year: int = 2022) -> pd.DataFrame:
    """Load Higher Education KA1 grants by applicant country from the annual annex."""
    raw = pd.read_excel(path, sheet_name=GRANTS_SHEET)
    he = raw.loc[(raw["Field"].eq("Higher Education")) & (raw["Call Year"].eq(call_year))].copy()

    numeric_cols = ["Grants", "Estimated Participants", "Actual Participants", "Projects"]
    for column in numeric_cols:
        he[column] = pd.to_numeric(he[column], errors="coerce").fillna(0)

    he["country_code"] = country_name_to_code(he["Applicant Country"])
    he = he.dropna(subset=["country_code"]).copy()

    grants = (
        he.groupby(["country_code", "Applicant Country"], as_index=False)
        .agg(
            he_grants_eur=("Grants", "sum"),
            he_estimated_participants=("Estimated Participants", "sum"),
            he_actual_participants=("Actual Participants", "sum"),
            he_projects=("Projects", "sum"),
        )
        .rename(columns={"Applicant Country": "grant_country_name"})
    )
    grants["he_grant_per_estimated_participant_eur"] = (
        grants["he_grants_eur"] / grants["he_estimated_participants"].replace(0, pd.NA)
    )
    grants["he_grant_per_actual_participant_eur"] = (
        grants["he_grants_eur"] / grants["he_actual_participants"].replace(0, pd.NA)
    )
    grants["grant_call_year"] = call_year
    return grants.sort_values("country_code").reset_index(drop=True)


def join_sender_grants(flows: pd.DataFrame, grants: pd.DataFrame) -> pd.DataFrame:
    """Join applicant-country HE grant metrics to the sending-country side of flow data."""
    sender_grants = grants.add_prefix("sender_").rename(columns={"sender_country_code": "sending_code"})
    return flows.merge(sender_grants, on="sending_code", how="left")


def grant_coverage(joined: pd.DataFrame) -> pd.DataFrame:
    """Summarize grant missingness after joining grant metrics to flows."""
    checks = [
        ("sender_he_grants_eur", "sender HE grants"),
        ("sender_he_grant_per_estimated_participant_eur", "sender HE grant per estimated participant"),
        ("sender_he_grant_per_actual_participant_eur", "sender HE grant per actual participant"),
    ]
    rows = []
    for column, label in checks:
        missing = joined[column].isna()
        rows.append(
            {
                "indicator": label,
                "missing_rows": int(missing.sum()),
                "missing_flow_count": int(joined.loc[missing, "flow_count"].sum()),
            }
        )
    return pd.DataFrame(rows)
