from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_KA1 = Path("data/raw/Erasmus-KA1-Mobility-Data-2022.xlsx")
KA1_SHEET = "KA1 mobilities 2022"
PARTICIPANTS_COL = "Actual Participants (Contracted Projects)"


KA1_COLUMNS = [
    "Academic Year",
    "Mobility Start Month",
    "Mobility Duration",
    "Activity (mob)",
    "Field",
    "Participant Profile",
    "Participant Age",
    "Sending Country",
    "Sending City",
    "Sending Organization",
    "Receiving Country",
    "Receiving City",
    "Receiving Organization",
    PARTICIPANTS_COL,
]


def split_country(value: object) -> tuple[str | None, str | None]:
    """Split Erasmus country values formatted like 'IT - Italy'."""
    if not isinstance(value, str) or " - " not in value:
        return None, None
    code, country = value.split(" - ", 1)
    return code.strip(), country.strip()


def load_ka1_raw(path: str | Path = RAW_KA1) -> pd.DataFrame:
    """Load the KA1 2022 mobility file with the columns used by this project."""
    return pd.read_excel(path, sheet_name=KA1_SHEET, usecols=KA1_COLUMNS)


def filter_he_studies(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filter KA1 data to higher-education learner study mobilities."""
    diagnostics: list[dict[str, int | str]] = []

    def record(step: str, frame: pd.DataFrame) -> None:
        diagnostics.append({"step": step, "rows": len(frame), "participants": int(frame[PARTICIPANTS_COL].sum())})

    df = raw.copy()
    df[PARTICIPANTS_COL] = pd.to_numeric(df[PARTICIPANTS_COL], errors="coerce").fillna(0).astype(int)
    df["participant_age"] = pd.to_numeric(df["Participant Age"], errors="coerce")
    df["mobility_duration"] = pd.to_numeric(df["Mobility Duration"], errors="coerce")
    record("raw", df)

    df = df.loc[df["Field"].eq("Higher Education")].copy()
    record("higher_education", df)

    profile = df["Participant Profile"].astype(str).str.lower()
    df = df.loc[profile.eq("learner") | profile.eq("learners")].copy()
    record("learners_only", df)

    activity = df["Activity (mob)"].astype(str)
    studies = activity.str.startswith("HE-SMS", na=False) | activity.str.contains(
        "Student mobility for studies", case=False, na=False
    )
    df = df.loc[studies].copy()
    record("studies_only", df)

    df = df.loc[df["participant_age"].ge(18)].copy()
    record("age_18_plus", df)

    sending = df["Sending Country"].apply(split_country).apply(pd.Series)
    sending.columns = ["sending_code", "sending_country"]
    receiving = df["Receiving Country"].apply(split_country).apply(pd.Series)
    receiving.columns = ["receiving_code", "receiving_country"]
    df = pd.concat([df, sending, receiving], axis=1)

    df = df.dropna(subset=["sending_code", "receiving_code"]).copy()
    record("valid_country_codes", df)

    diagnostics_df = pd.DataFrame(diagnostics)
    return df.reset_index(drop=True), diagnostics_df


def aggregate_country_flows(filtered: pd.DataFrame, include_domestic: bool = False) -> pd.DataFrame:
    """Aggregate filtered KA1 records to sending-receiving country flows."""
    flow_cols = ["sending_code", "sending_country", "receiving_code", "receiving_country"]
    flows = (
        filtered.groupby(flow_cols, as_index=False)[PARTICIPANTS_COL]
        .sum()
        .rename(columns={PARTICIPANTS_COL: "flow_count"})
        .sort_values(["sending_code", "flow_count"], ascending=[True, False])
        .reset_index(drop=True)
    )

    if not include_domestic:
        flows = flows.loc[flows["sending_code"] != flows["receiving_code"]].reset_index(drop=True)

    return flows


def build_ka1_he_studies_flows(path: str | Path = RAW_KA1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the project's main HE studies-only country-pair flow dataset."""
    raw = load_ka1_raw(path)
    filtered, diagnostics = filter_he_studies(raw)
    flows = aggregate_country_flows(filtered, include_domestic=False)
    return flows, diagnostics
