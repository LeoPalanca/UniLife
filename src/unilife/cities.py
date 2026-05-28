from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from .ka1 import PARTICIPANTS_COL, RAW_KA1, canonical_country_names, filter_he_studies, load_ka1_raw

_WS = re.compile(r"\s+")


def normalize_city_key(value: object) -> str | None:
    """Build an accent- and case-insensitive matching key for a city name."""
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _WS.sub(" ", text).strip().upper()
    return text or None


_PLACEHOLDER_ORGS = {"NAN", "NONE", "NA", "N/A", "UNKNOWN", "UNDEFINED", "TBD"}
ORG_NOT_SPECIFIED = "__NOT_SPECIFIED__"
UNIVERSITY_CROSSWALK = Path("data/crosswalks/university_names.csv")


def load_university_crosswalk(path: str | Path = UNIVERSITY_CROSSWALK) -> dict[tuple[str, str], str]:
    """Map (country_code, normalized org key) -> curated canonical university name.

    Lets several raw strings (acronym and full-name variants) for the same
    university collapse to one labeled point. Curated, top-flow coverage only.
    """
    path = Path(path)
    if not path.exists():
        return {}
    table = pd.read_csv(path)
    crosswalk: dict[tuple[str, str], str] = {}
    for row in table.itertuples():
        key = normalize_org_key(str(row.variant_key))
        if key is None:
            continue
        crosswalk[(str(row.country_code), key)] = str(row.canonical_name)
    return crosswalk


def normalize_org_key(value: object) -> str | None:
    """Accent/case/whitespace-insensitive key for an organization name.

    Returns None for blank or placeholder names so they can be dropped.
    """
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _WS.sub(" ", text).strip().upper().strip(" .,-/_")
    if not text or text in _PLACEHOLDER_ORGS:
        return None
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def canonical_org_names(filtered: pd.DataFrame) -> dict[tuple[str, str], str]:
    """Pick one display name per (country_code, org_key) by participant-weighted frequency."""
    part = filtered[["receiving_code", "Receiving Organization", PARTICIPANTS_COL]].rename(
        columns={"receiving_code": "code", "Receiving Organization": "org"}
    )
    part = part.dropna(subset=["code", "org"])
    part["org_key"] = part["org"].map(normalize_org_key)
    part = part.dropna(subset=["org_key"])
    part["display"] = part["org"].astype(str).str.strip()
    grouped = part.groupby(["code", "org_key", "display"], as_index=False)[PARTICIPANTS_COL].sum()
    grouped = grouped.sort_values([PARTICIPANTS_COL, "display"], ascending=[False, True])
    grouped = grouped.drop_duplicates(["code", "org_key"])
    return {(row.code, row.org_key): row.display for row in grouped.itertuples()}


def canonical_city_names(filtered: pd.DataFrame) -> dict[tuple[str, str], str]:
    """Pick one display name per (country_code, city_key) by participant-weighted frequency."""
    frames = []
    for code_col, city_col in (("sending_code", "Sending City"), ("receiving_code", "Receiving City")):
        part = filtered[[code_col, city_col, PARTICIPANTS_COL]].rename(
            columns={code_col: "code", city_col: "city"}
        )
        frames.append(part)
    names = pd.concat(frames, ignore_index=True).dropna(subset=["code", "city"])
    names["city_key"] = names["city"].map(normalize_city_key)
    names = names.dropna(subset=["city_key"])
    names["display"] = names["city"].astype(str).str.strip().str.title()
    grouped = names.groupby(["code", "city_key", "display"], as_index=False)[PARTICIPANTS_COL].sum()
    grouped = grouped.sort_values([PARTICIPANTS_COL, "display"], ascending=[False, True])
    grouped = grouped.drop_duplicates(["code", "city_key"])
    return {(row.code, row.city_key): row.display for row in grouped.itertuples()}


def aggregate_city_flows(filtered: pd.DataFrame, include_domestic: bool = False) -> pd.DataFrame:
    """Aggregate filtered KA1 records to sending-city -> receiving-city flows."""
    country_names = canonical_country_names(filtered)
    city_names = canonical_city_names(filtered)

    df = filtered.copy()
    df["sending_city_key"] = df["Sending City"].map(normalize_city_key)
    df["receiving_city_key"] = df["Receiving City"].map(normalize_city_key)
    df = df.dropna(subset=["sending_city_key", "receiving_city_key"]).copy()

    df["sending_country"] = df["sending_code"].map(country_names).fillna(df["sending_country"])
    df["receiving_country"] = df["receiving_code"].map(country_names).fillna(df["receiving_country"])

    keys = ["sending_code", "sending_country", "sending_city_key", "receiving_code", "receiving_country", "receiving_city_key"]
    flows = (
        df.groupby(keys, as_index=False)[PARTICIPANTS_COL]
        .sum()
        .rename(columns={PARTICIPANTS_COL: "flow_count"})
    )

    flows["sending_city"] = [city_names.get((c, k), k.title()) for c, k in zip(flows["sending_code"], flows["sending_city_key"])]
    flows["receiving_city"] = [city_names.get((c, k), k.title()) for c, k in zip(flows["receiving_code"], flows["receiving_city_key"])]

    if not include_domestic:
        flows = flows.loc[flows["sending_code"] != flows["receiving_code"]]

    cols = [
        "sending_code", "sending_country", "sending_city",
        "receiving_code", "receiving_country", "receiving_city",
        "flow_count",
    ]
    flows = flows[cols].sort_values(["sending_code", "flow_count"], ascending=[True, False])
    return flows.reset_index(drop=True)


def build_ka1_he_studies_city_flows(path: str | Path = RAW_KA1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the HE studies-only sending-city -> receiving-city flow dataset."""
    raw = load_ka1_raw(path)
    filtered, diagnostics = filter_he_studies(raw)
    flows = aggregate_city_flows(filtered, include_domestic=False)
    return flows, diagnostics


def aggregate_org_flows(filtered: pd.DataFrame, include_domestic: bool = False) -> pd.DataFrame:
    """Aggregate filtered KA1 records to receiving-university flows within cities."""
    country_names = canonical_country_names(filtered)
    city_names = canonical_city_names(filtered)
    org_names = canonical_org_names(filtered)
    crosswalk = load_university_crosswalk()

    df = filtered.copy()
    df["sending_city_key"] = df["Sending City"].map(normalize_city_key)
    df["receiving_city_key"] = df["Receiving City"].map(normalize_city_key)
    df["receiving_org_key"] = df["Receiving Organization"].map(normalize_org_key)
    df = df.dropna(subset=["receiving_city_key"]).copy()
    df["receiving_org_key"] = df["receiving_org_key"].fillna(ORG_NOT_SPECIFIED)

    df["sending_country"] = df["sending_code"].map(country_names).fillna(df["sending_country"])
    df["receiving_country"] = df["receiving_code"].map(country_names).fillna(df["receiving_country"])

    def org_display(code: str, key: str) -> str:
        if key == ORG_NOT_SPECIFIED:
            return "(University not specified)"
        return crosswalk.get((code, key)) or org_names.get((code, key), key.title())

    df["receiving_org"] = [
        org_display(c, k) for c, k in zip(df["receiving_code"], df["receiving_org_key"])
    ]
    df["receiving_city"] = [
        city_names.get((c, k), k.title()) for c, k in zip(df["receiving_code"], df["receiving_city_key"])
    ]

    keys = [
        "sending_code", "sending_country",
        "receiving_code", "receiving_country", "receiving_city", "receiving_org",
    ]
    flows = (
        df.groupby(keys, as_index=False)[PARTICIPANTS_COL]
        .sum()
        .rename(columns={PARTICIPANTS_COL: "flow_count"})
    )

    if not include_domestic:
        flows = flows.loc[flows["sending_code"] != flows["receiving_code"]]

    cols = [
        "sending_code", "sending_country",
        "receiving_code", "receiving_country", "receiving_city", "receiving_org",
        "flow_count",
    ]
    flows = flows[cols].sort_values(["receiving_code", "flow_count"], ascending=[True, False])
    return flows.reset_index(drop=True)


def build_ka1_he_studies_org_flows(path: str | Path = RAW_KA1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the HE studies-only receiving-university flow dataset."""
    raw = load_ka1_raw(path)
    filtered, diagnostics = filter_he_studies(raw)
    flows = aggregate_org_flows(filtered, include_domestic=False)
    return flows, diagnostics
