"""Dashboard payload builders.

All JSON-serializable data the dashboard consumes is built here. The thin
runner at `scripts/build_dashboard.py` calls these functions, assembles the
payload dict, and inlines the JSON into the HTML template.
"""
from __future__ import annotations

import collections
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..db import read_table, table_names

REDDIT_EWMA_HALF_LIFE_DAYS = 365.0
REDDIT_LOOKBACK_YEARS = 15  # cap Reddit history so the text layer matches the Erasmus panel window

# SQLite table names (DB built by scripts/build_db.py)
DATA_PATH = "ka1_he_studies_flows_with_indicators"
ORG_FLOWS_PATH = "erasmus_org_flows_long"
COUNTRY_UNI_FLOWS_PATH = "erasmus_country_uni_flows_long"
UNI_COUNTRY_FLOWS_PATH = "erasmus_uni_country_flows_long"
UNI_UNI_FLOWS_PATH = "erasmus_uni_uni_flows_long"
CITY_COORDS_PATH = "city_coordinates"
SECTOR_EARNINGS_PATH = "sector_earnings_latest"
REDDIT_MENTIONS_PATH = "reddit_destination_mentions"
PANEL_PATH = "erasmus_country_year_panel"
OUTPUT_PATH = Path("dashboard/dist/index.html")


FLOW_COLUMNS = [
    "sending_code",
    "sending_country",
    "receiving_code",
    "receiving_country",
    "flow_count",
    "sender_gdp_pc_current_usd_wb",
    "receiver_gdp_pc_current_usd_wb",
    "gdp_gap_usd_wb",
    "price_level_gap",
    "earnings_gap",
    "sender_he_grants_eur",
    "sender_he_estimated_participants",
    "sender_he_actual_participants",
    "sender_he_grant_per_estimated_participant_eur",
    "sender_he_grant_per_actual_participant_eur",
]


# Implemented model inputs. Expected signs are hypotheses, not estimated findings.
MODEL_VARIABLES = [
    {
        "name": "GDP-per-capita gap",
        "symbol": "β₁",
        "role": "Broad destination-prosperity control",
        "source": "World Bank GDP per capita (gdp_gap_usd_wb)",
        "expected_sign": "+ (richer destinations associated with more flow, broad control)",
        "status": "built",
    },
    {
        "name": "Quality of life",
        "symbol": "β₂",
        "role": "Explanatory – perceived liveability",
        "source": "Erasmusu city ratings (headline regressor); Reddit r/Erasmus via DeepSeek + Pydantic (supporting text evidence)",
        "expected_sign": "+ (better perceived life attracts flows)",
        "status": "built",
    },
    {
        "name": "Institution quality",
        "symbol": "β₃",
        "role": "Explanatory – academic pull",
        "source": "QS World University Rankings 2023, geocoded + snapped to destination city (institution_quality.csv)",
        "expected_sign": "+ (stronger universities attract flows)",
        "status": "built",
    },
    {
        "name": "Language affinity",
        "symbol": "control",
        "role": "Control – origin–destination language affinity (gravity friction)",
        "source": "Shared language-family dummy (geo.py LANGUAGE_FAMILY)",
        "expected_sign": "+ for shared/affine language family",
        "status": "built",
    },
    {
        "name": "Distance",
        "symbol": "control",
        "role": "Control – gravity friction",
        "source": "Origin-country centroid → destination-city great-circle km (geo.py)",
        "expected_sign": "− (farther destinations deter flows)",
        "status": "built",
    },
    {
        "name": "Salary gap",
        "symbol": "robustness",
        "role": "Robustness only – salary heterogeneity (overlaps GDP gap)",
        "source": "Eurostat net earnings (earnings_gap, sector_earnings_2018.csv)",
        "expected_sign": "ambiguous (VIF ~7 with GDP gap; not a headline term)",
        "status": "built",
    },
    {
        "name": "Price-level gap",
        "symbol": "robustness",
        "role": "Robustness only – cost of living (overlaps GDP gap)",
        "source": "Eurostat price levels (price_level_gap)",
        "expected_sign": "ambiguous (VIF ~6.5 with GDP gap; not a headline term)",
        "status": "built",
    },
]


def render_variable_cards(variables: list[dict]) -> str:
    """Render the model variables (the betas) as static descriptive cards."""
    cards = []
    for v in variables:
        cards.append(
            '<div class="card">'
            f'<div class="label">{v["symbol"]} · {v["status"]}</div>'
            f'<div class="value" style="font-size:18px">{v["name"]}</div>'
            f'<p class="note" style="margin:8px 0 0">{v["role"]}<br>'
            f'<strong>Source:</strong> {v["source"]}<br>'
            f'<strong>Expected:</strong> {v["expected_sign"]}</p>'
            "</div>"
        )
    return "\n".join(cards)


def json_safe(value):
    """Recursively convert pandas/numpy missing values to strict JSON-safe nulls."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def clean_records(frame: pd.DataFrame) -> list[dict]:
    """Convert selected dataframe columns to compact JSON-safe records."""
    records = frame[FLOW_COLUMNS].replace({np.nan: None}).to_dict(orient="records")
    for record in records:
        record["flow_count"] = int(record["flow_count"])
    return records


def country_records(flows: pd.DataFrame) -> list[dict]:
    outgoing = (
        flows.groupby(["sending_code", "sending_country"], as_index=False)["flow_count"]
        .sum()
        .rename(columns={"sending_code": "code", "sending_country": "country", "flow_count": "outgoing"})
    )
    incoming = (
        flows.groupby(["receiving_code", "receiving_country"], as_index=False)["flow_count"]
        .sum()
        .rename(columns={"receiving_code": "code", "receiving_country": "country", "flow_count": "incoming"})
    )
    countries = outgoing.merge(incoming, on="code", how="outer", suffixes=("", "_incoming"))
    countries["country"] = countries["country"].fillna(countries["country_incoming"])
    countries["outgoing"] = countries["outgoing"].fillna(0).astype(int)
    countries["incoming"] = countries["incoming"].fillna(0).astype(int)
    countries["total"] = countries["outgoing"] + countries["incoming"]
    countries = countries.sort_values(["outgoing", "total", "code"], ascending=[False, False, True])
    return countries[["code", "country", "outgoing", "incoming", "total"]].to_dict(orient="records")


def weighted_average(group: pd.DataFrame, column: str) -> float | None:
    valid = group.dropna(subset=[column])
    if valid.empty:
        return None
    return float(np.average(valid[column], weights=valid["flow_count"]))


def weighted_records(flows: pd.DataFrame) -> list[dict]:
    rows = []
    for (code, country), group in flows.groupby(["sending_code", "sending_country"]):
        first = group.iloc[0]
        rows.append(
            {
                "sender": f"{code} - {country}",
                "code": code,
                "outgoing": int(group["flow_count"].sum()),
                "weighted_gdp_pc_usd": weighted_average(group, "receiver_gdp_pc_current_usd_wb"),
                "weighted_price_level": weighted_average(group, "receiver_price_level_aic_eu27_2020_100"),
                "weighted_net_earnings_eur": weighted_average(group, "receiver_net_earnings_eur"),
                "grant_per_estimated_participant_eur": first.get("sender_he_grant_per_estimated_participant_eur"),
                "grant_per_actual_participant_eur": first.get("sender_he_grant_per_actual_participant_eur"),
            }
        )
    return pd.DataFrame(rows).replace({np.nan: None}).sort_values("outgoing", ascending=False).to_dict(orient="records")


def _city_coordinates() -> pd.DataFrame:
    return read_table(CITY_COORDS_PATH)[
        ["receiving_code", "receiving_city", "inbound_flow", "lat", "lon", "match_level"]
    ]


def _read_org_flow_levels() -> dict[str, pd.DataFrame]:
    country_uni = COUNTRY_UNI_FLOWS_PATH if COUNTRY_UNI_FLOWS_PATH in table_names() else ORG_FLOWS_PATH
    return {
        "countryUni": read_table(country_uni),
        "uniCountry": read_table(UNI_COUNTRY_FLOWS_PATH),
        "uniUni": read_table(UNI_UNI_FLOWS_PATH),
    }


def _merge_receiving_coords(flows: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    return flows.merge(coords, on=["receiving_code", "receiving_city"], how="left").dropna(subset=["lat", "lon"])


def _merge_sending_coords(flows: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    sending_coords = coords.rename(
        columns={"receiving_code": "sending_code", "receiving_city": "sending_city"}
    )
    return flows.merge(sending_coords, on=["sending_code", "sending_city"], how="left").dropna(subset=["lat", "lon"])


def _country_coordinates(coords: pd.DataFrame) -> pd.DataFrame:
    valid = coords.dropna(subset=["lat", "lon"]).copy()
    rows = []
    for code, group in valid.groupby("receiving_code"):
        weights = group["inbound_flow"].clip(lower=1)
        rows.append(
            {
                "receiving_code": code,
                "lat": float(np.average(group["lat"], weights=weights)),
                "lon": float(np.average(group["lon"], weights=weights)),
                "match_level": "country",
            }
        )
    return pd.DataFrame(rows)


def _merge_country_coords(flows: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    return flows.merge(_country_coordinates(coords), on="receiving_code", how="left").dropna(subset=["lat", "lon"])


def _compact_point(row: pd.Series, org_col: str, city_col: str, country_col: str, with_sender: bool = False) -> dict:
    record = {
        "o": row[org_col],
        "c": row[city_col],
        "n": row[country_col],
        "la": round(float(row["lat"]), 3),
        "lo": round(float(row["lon"]), 3),
        "f": int(row["flow_count"]),
        "m": row["match_level"],
    }
    if with_sender:
        record["s"] = row["sending_code"]
    return record


def org_flow_map_records(top_per_sender: int = 250) -> dict[str, dict[str, list[dict]]]:
    """Compact map records for country->uni, uni->country, and uni->uni views.

    University points are placed at city coordinates (no per-university geocoding
    exists), so clustering groups same-city universities.
    """
    coords = _city_coordinates()
    levels = _read_org_flow_levels()
    payload: dict[str, dict[str, list[dict]]] = {}

    country_uni = _merge_receiving_coords(levels["countryUni"], coords)
    capped = country_uni.sort_values(["sending_code", "flow_count"], ascending=[True, False])
    capped = capped.groupby("sending_code", group_keys=False).head(top_per_sender)
    inbound = (
        country_uni.groupby(
            ["receiving_org", "receiving_city", "receiving_country", "lat", "lon", "match_level"],
            as_index=False,
        )["flow_count"]
        .sum()
        .sort_values("flow_count", ascending=False)
    )
    payload["countryUni"] = {
        "points": [_compact_point(row, "receiving_org", "receiving_city", "receiving_country", True) for _, row in capped.iterrows()],
        "all": [_compact_point(row, "receiving_org", "receiving_city", "receiving_country", False) for _, row in inbound.iterrows()],
    }

    uni_country = _merge_country_coords(levels["uniCountry"], coords)
    per_sender = []
    for _, row in uni_country.iterrows():
        record = {
            "o": row["receiving_country"],
            "c": "Country centroid",
            "n": row["receiving_country"],
            "la": round(float(row["lat"]), 3),
            "lo": round(float(row["lon"]), 3),
            "f": int(row["flow_count"]),
            "m": row["match_level"],
            "s": row["sending_code"],
            "so": row["sending_org"],
            "sc": row["sending_city"],
        }
        record["dc"] = row["receiving_code"]
        per_sender.append(record)
    outbound = (
        uni_country.groupby(
            ["receiving_code", "receiving_country", "lat", "lon", "match_level"],
            as_index=False,
        )["flow_count"]
        .sum()
        .sort_values("flow_count", ascending=False)
    )
    all_countries = []
    for _, row in outbound.iterrows():
        all_countries.append(
            {
                "o": row["receiving_country"],
                "c": "Country centroid",
                "n": row["receiving_country"],
                "la": round(float(row["lat"]), 3),
                "lo": round(float(row["lon"]), 3),
                "f": int(row["flow_count"]),
                "m": row["match_level"],
                "dc": row["receiving_code"],
            }
        )
    payload["uniCountry"] = {
        "points": per_sender,
        "all": all_countries,
        "allSearch": per_sender,
    }

    uni_uni = _merge_receiving_coords(levels["uniUni"], coords)
    capped = uni_uni.sort_values(["sending_code", "flow_count"], ascending=[True, False])
    capped = capped.groupby("sending_code", group_keys=False).head(top_per_sender)
    per_sender = []
    for _, row in capped.iterrows():
        record = _compact_point(row, "receiving_org", "receiving_city", "receiving_country", True)
        record["so"] = row["sending_org"]
        record["sc"] = row["sending_city"]
        per_sender.append(record)
    inbound = (
        uni_uni.groupby(
            ["receiving_org", "receiving_city", "receiving_country", "lat", "lon", "match_level"],
            as_index=False,
        )["flow_count"]
        .sum()
        .sort_values("flow_count", ascending=False)
    )
    payload["uniUni"] = {
        "points": per_sender,
        "all": [_compact_point(row, "receiving_org", "receiving_city", "receiving_country", False) for _, row in inbound.iterrows()],
    }
    return payload


def org_flow_table_records(top_per_sender: int = 300) -> dict[str, list[dict]]:
    """Compact top flow rows for the selected-country university detail table."""
    levels = _read_org_flow_levels()
    records: dict[str, list[dict]] = {}
    for key, frame in levels.items():
        rows = frame.sort_values(["sending_code", "flow_count"], ascending=[True, False])
        rows = rows.groupby("sending_code", group_keys=False).head(top_per_sender)
        rows = rows.replace({np.nan: None})
        if key == "countryUni":
            cols = ["sending_code", "receiving_code", "receiving_country", "receiving_city", "receiving_org", "flow_count"]
        elif key == "uniCountry":
            cols = ["sending_code", "sending_city", "sending_org", "receiving_code", "receiving_country", "flow_count"]
        else:
            cols = [
                "sending_code", "sending_city", "sending_org",
                "receiving_code", "receiving_country", "receiving_city", "receiving_org", "flow_count",
            ]
        records[key] = rows[cols].to_dict(orient="records")
        for record in records[key]:
            record["flow_count"] = int(record["flow_count"])
    return records


def sector_earnings_records() -> list[dict]:
    """Detailed-sector mean monthly earnings per country for the salary explorer."""
    earnings = read_table(SECTOR_EARNINGS_PATH)
    earnings = earnings[earnings["is_sector"] == True]  # noqa: E712 - pandas mask
    earnings = earnings.replace({np.nan: None})
    records = []
    for _, row in earnings.iterrows():
        records.append(
            {
                "code": row["country_code"],
                "country": row["country_name"],
                "nace": row["nace_code"],
                "label": row["nace_label"],
                "year": int(row["year"]),
                "eur": None if row["earnings_eur"] is None else float(row["earnings_eur"]),
                "pps": None if row["earnings_pps"] is None else float(row["earnings_pps"]),
            }
        )
    return records


def _reddit_window_utc() -> tuple[int, int, int]:
    """Anchor EWMA at the moment of build (so the most recent posts carry full weight)
    and look back 15 years. r/Erasmus only goes back to 2011-10-30, so the floor is
    effectively clamped at corpus creation — the lookback never drops real data.

    Returns (end_utc, start_utc, anchor_year).
    """
    end_dt = datetime.now(tz=timezone.utc)
    start_dt = end_dt.replace(year=end_dt.year - REDDIT_LOOKBACK_YEARS)
    return int(end_dt.timestamp()), int(start_dt.timestamp()), end_dt.year


def reddit_meta() -> dict:
    """Coverage stamp for the Reddit data: oldest/newest post + total counts."""
    if REDDIT_MENTIONS_PATH not in table_names():
        return {}
    df = read_table(REDDIT_MENTIONS_PATH)
    created = pd.to_numeric(df.get("created_utc"), errors="coerce").dropna()
    end_utc, start_utc, end_year = _reddit_window_utc()
    if created.empty:
        return {"mentions": int(len(df)), "observationEndYear": end_year}
    in_window = created[(created >= start_utc) & (created <= end_utc)]
    return {
        "mentions": int(len(df)),
        "withDate": int(len(created)),
        "earliestUtc": int(created.min()),
        "latestUtc": int(created.max()),
        "windowStartUtc": start_utc,
        "windowEndUtc": end_utc,
        "observationEndYear": end_year,
        "lookbackYears": REDDIT_LOOKBACK_YEARS,
        "inWindowCount": int(len(in_window)),
        "droppedFuture": int(int((created > end_utc).sum())),
        "droppedOld": int(int((created < start_utc).sum())),
    }


def reddit_records() -> list[dict]:
    """Aggregate r/Erasmus destination mentions to a per-country sentiment summary."""
    if REDDIT_MENTIONS_PATH not in table_names():
        return []
    df = read_table(REDDIT_MENTIONS_PATH).dropna(subset=["country"])
    df["sentiment_score"] = df["sentiment"].map({"positive": 1.0, "neutral": 0.0, "negative": -1.0})
    df["confidence_weight"] = pd.to_numeric(df.get("confidence"), errors="coerce").fillna(1.0)
    df["reddit_score"] = pd.to_numeric(df.get("score"), errors="coerce").fillna(0.0)
    df["score_weight"] = np.log1p(df["reddit_score"].clip(lower=0.0)) + 1.0

    # Align the Reddit text layer with the Erasmus panel window: drop posts after
    # Dec-31 of the last observed Erasmus year (no peeking forward), and posts older
    # than 15 years before that anchor (older opinions are about a different programme).
    # EWMA then decays toward the same observation end, not real-now, so the weights
    # are stable across re-runs.
    end_utc, start_utc, _ = _reddit_window_utc()
    created = pd.to_numeric(df.get("created_utc"), errors="coerce")
    in_window = created.between(start_utc, end_utc) | created.isna()
    df = df.loc[in_window].copy()
    created = created.loc[in_window]

    lam = math.log(2.0) / (REDDIT_EWMA_HALF_LIFE_DAYS * 86400.0)
    age_seconds = (end_utc - created).clip(lower=0.0)
    df["age_weight"] = np.exp(-lam * age_seconds).where(created.notna(), 1.0)

    def top_themes(frame: pd.DataFrame, limit: int = 4) -> str:
        themes: collections.Counter = collections.Counter()
        for value in frame["themes"].dropna():
            for theme in str(value).split(";"):
                theme = theme.strip()
                if theme:
                    themes[theme] += 1
        return ", ".join(theme for theme, _ in themes.most_common(limit))

    rows = []
    for country, group in df.groupby("country"):
        n = len(group)
        pos = int((group["sentiment"] == "positive").sum())
        neu = int((group["sentiment"] == "neutral").sum())
        neg = int((group["sentiment"] == "negative").sum())
        weights = group["confidence_weight"] * group["score_weight"] * group["age_weight"]
        scored = group.dropna(subset=["sentiment_score"])
        scored_weights = weights.loc[scored.index]
        weighted_net = np.average(scored["sentiment_score"], weights=scored_weights) if len(scored) else None
        positive_group = group[group["sentiment"] == "positive"]
        negative_group = group[group["sentiment"] == "negative"]
        effective_n = float(group["age_weight"].sum())
        rows.append(
            {
                "country": country,
                "mentions": n,
                "effectiveMentions": round(effective_n, 1),
                "positive": pos,
                "neutral": neu,
                "negative": neg,
                "net": round((pos - neg) / n, 3) if n else None,
                "weightedNet": round(float(weighted_net), 3) if weighted_net is not None else None,
                "avgScore": round(float(group["reddit_score"].mean()), 1),
                "themes": top_themes(group),
                "positiveThemes": top_themes(positive_group),
                "negativeThemes": top_themes(negative_group),
            }
        )
    rows.sort(key=lambda r: r["mentions"], reverse=True)
    return rows


def time_series_records() -> list[dict]:
    """Compact country x country x year flow rows for the temporal trends section."""
    if PANEL_PATH not in table_names():
        return []
    panel = read_table(PANEL_PATH)
    return [
        {
            "s": row.sending_code,
            "d": row.receiving_code,
            "dn": row.receiving_country,
            "y": int(row.year),
            "f": int(row.flow_count),
        }
        for row in panel.itertuples(index=False)
    ]


def regression_results() -> list[dict]:
    """Persisted regression coefficient rows (written by run_regression.py)."""
    if "regression_results" not in table_names():
        return []
    return read_table("regression_results").to_dict(orient="records")


def panel_year_effects() -> list[dict]:
    """Panel-gravity year fixed effects (the COVID-dip series)."""
    if "panel_year_effects" not in table_names():
        return []
    return read_table("panel_year_effects").to_dict(orient="records")


def covid_event_study() -> list[dict]:
    """Event-study betas: sector COVID-hit interacted with year, 2019 reference."""
    if "covid_event_study" not in table_names():
        return []
    return read_table("covid_event_study").to_dict(orient="records")


def covid_event_study_employment() -> list[dict]:
    """Employment-based event study (covid_emp_hit x year)."""
    if "covid_event_study_employment" not in table_names():
        return []
    return read_table("covid_event_study_employment").to_dict(orient="records")


def model_coefficients() -> list[dict]:
    """Every model beta (estimated + planned) for the per-coefficient table."""
    if "model_coefficients" not in table_names():
        return []
    return read_table("model_coefficients").to_dict(orient="records")

