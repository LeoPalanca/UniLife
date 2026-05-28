from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


DATA_PATH = Path("data/processed/ka1_he_studies_flows_with_indicators.csv")
ORG_FLOWS_PATH = Path("data/processed/erasmus_org_flows_long.csv")
COUNTRY_UNI_FLOWS_PATH = Path("data/processed/erasmus_country_uni_flows_long.csv")
UNI_COUNTRY_FLOWS_PATH = Path("data/processed/erasmus_uni_country_flows_long.csv")
UNI_UNI_FLOWS_PATH = Path("data/processed/erasmus_uni_uni_flows_long.csv")
CITY_COORDS_PATH = Path("data/processed/city_coordinates.csv")
SECTOR_EARNINGS_PATH = Path("data/processed/sector_earnings_2018.csv")
REDDIT_MENTIONS_PATH = Path("data/processed/reddit_destination_mentions.csv")
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


# Step-3 design of the gravity model (see report). Each variable is a term in the
# regression below; "built" means the data is already in the processed pipeline,
# "planned" means it is part of the described-but-not-estimated design.
MODEL_VARIABLES = [
    {
        "name": "Salary gap",
        "symbol": "β₁",
        "role": "Explanatory – labour-market pull",
        "source": "Eurostat net earnings (earnings_gap, sector_earnings_2018.csv)",
        "expected_sign": "+ (higher destination pay attracts flows)",
        "status": "built",
    },
    {
        "name": "Quality of life",
        "symbol": "β₂",
        "role": "Explanatory – perceived liveability",
        "source": "Reddit r/Erasmus, sentiment + themes via Gemini/Pydantic (text layer)",
        "expected_sign": "+ (better perceived life attracts flows)",
        "status": "built",
    },
    {
        "name": "Institution quality",
        "symbol": "β₃",
        "role": "Explanatory – academic pull",
        "source": "University ranking score (destination)",
        "expected_sign": "+ (stronger universities attract flows)",
        "status": "planned",
    },
    {
        "name": "Language affinity",
        "symbol": "control",
        "role": "Control – origin–destination language affinity (gravity friction)",
        "source": "Mediterranean / Anglo-Saxon / Germanic country groupings",
        "expected_sign": "+ for shared/affine language family",
        "status": "planned",
    },
    {
        "name": "GDP gap",
        "symbol": "control",
        "role": "Control – income difference",
        "source": "World Bank GDP per capita (gdp_gap_usd_wb)",
        "expected_sign": "ambiguous",
        "status": "built",
    },
    {
        "name": "Price-level gap",
        "symbol": "control",
        "role": "Control – cost of living",
        "source": "Eurostat price levels (price_level_gap)",
        "expected_sign": "− (costlier destinations deter flows)",
        "status": "built",
    },
    {
        "name": "Distance",
        "symbol": "control",
        "role": "Control – gravity friction",
        "source": "Origin–destination distance (km)",
        "expected_sign": "− (farther destinations deter flows)",
        "status": "planned",
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
    return pd.read_csv(CITY_COORDS_PATH)[
        ["receiving_code", "receiving_city", "inbound_flow", "lat", "lon", "match_level"]
    ]


def _read_org_flow_levels() -> dict[str, pd.DataFrame]:
    country_uni_path = COUNTRY_UNI_FLOWS_PATH if COUNTRY_UNI_FLOWS_PATH.exists() else ORG_FLOWS_PATH
    return {
        "countryUni": pd.read_csv(country_uni_path),
        "uniCountry": pd.read_csv(UNI_COUNTRY_FLOWS_PATH),
        "uniUni": pd.read_csv(UNI_UNI_FLOWS_PATH),
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
    earnings = pd.read_csv(SECTOR_EARNINGS_PATH)
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
                "eur": None if row["earnings_eur"] is None else int(row["earnings_eur"]),
                "pps": None if row["earnings_pps"] is None else int(row["earnings_pps"]),
            }
        )
    return records


def reddit_records() -> list[dict]:
    """Aggregate r/Erasmus destination mentions to a per-country sentiment summary."""
    if not REDDIT_MENTIONS_PATH.exists():
        return []
    df = pd.read_csv(REDDIT_MENTIONS_PATH).dropna(subset=["country"])
    df["sentiment_score"] = df["sentiment"].map({"positive": 1.0, "neutral": 0.0, "negative": -1.0})
    df["confidence_weight"] = pd.to_numeric(df.get("confidence"), errors="coerce").fillna(1.0)
    df["reddit_score"] = pd.to_numeric(df.get("score"), errors="coerce").fillna(0.0)
    df["score_weight"] = np.log1p(df["reddit_score"].clip(lower=0.0)) + 1.0

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
        weights = group["confidence_weight"] * group["score_weight"]
        scored = group.dropna(subset=["sentiment_score"])
        scored_weights = weights.loc[scored.index]
        weighted_net = np.average(scored["sentiment_score"], weights=scored_weights) if len(scored) else None
        positive_group = group[group["sentiment"] == "positive"]
        negative_group = group[group["sentiment"] == "negative"]
        rows.append(
            {
                "country": country,
                "mentions": n,
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


def build_dashboard() -> str:
    flows = pd.read_csv(DATA_PATH)
    org_flow_levels = org_flow_map_records()
    payload = {
        "flows": clean_records(flows),
        "countries": country_records(flows),
        "weighted": weighted_records(flows),
        "orgFlowLevels": org_flow_levels,
        "orgFlowTables": org_flow_table_records(),
        "sectorEarnings": sector_earnings_records(),
        "redditByCountry": reddit_records(),
    }
    data_json = json.dumps(json_safe(payload), separators=(",", ":"), allow_nan=False)

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>unilife.ellep.it</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" crossorigin="">
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" crossorigin="">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js" crossorigin=""></script>
  <style>
    :root {
      color-scheme: light;
      --ink: #1f2933;
      --muted: #5f6b76;
      --line: #d8dee4;
      --paper: #f7f7f4;
      --panel: #ffffff;
      --accent: #2f6f73;
      --accent-2: #b44e5a;
      --soft: #eef3f1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--paper);
      color: var(--ink);
    }
    header {
      padding: 30px 42px 22px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }
    h2 { margin: 0 0 16px; font-size: 20px; letter-spacing: 0; }
    h3 { margin: 0 0 10px; font-size: 16px; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.5; max-width: 960px; }
    main {
      padding: 28px 42px 48px;
      display: grid;
      gap: 24px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      overflow-x: auto;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
      gap: 24px;
    }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: end;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }
    select, input {
      min-width: 280px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      background: #fff;
      color: var(--ink);
      font-size: 15px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .card {
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .card .label { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
    .card .value { font-size: 22px; font-weight: 700; }
    .chart svg {
      width: 100%;
      height: auto;
      display: block;
      overflow: visible;
    }
    .axis, .gridline { stroke: #b9c1c8; stroke-width: 1; }
    .axis-text { fill: var(--muted); font-size: 11px; }
    .bar { fill: var(--accent); }
    .bar-alt { fill: var(--accent-2); }
    .point { fill: #5d6f9f; fill-opacity: .68; stroke: #fff; stroke-width: .8; }
    .zero-line { stroke: #333; stroke-width: 1.2; }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      min-width: 820px;
    }
    .data-table th, .data-table td {
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: right;
      white-space: nowrap;
    }
    .data-table th:first-child, .data-table td:first-child,
    .data-table th:nth-child(2), .data-table td:nth-child(2) {
      text-align: left;
    }
    .data-table th.sortable {
      cursor: pointer;
      user-select: none;
      color: var(--accent);
    }
    .note, .source-list {
      font-size: 13px;
      color: var(--muted);
    }
    .source-list li { margin-bottom: 6px; }
    .heatmap-wrap { overflow: auto; }
    #map {
      height: 540px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }
    .map-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-top: 12px;
      font-size: 12px;
      color: var(--muted);
      align-items: center;
    }
    .legend-dot {
      display: inline-block;
      border-radius: 50%;
      background: rgba(47, 111, 115, .55);
      border: 1px solid var(--accent);
      vertical-align: middle;
      margin-right: 6px;
    }
    .leaflet-popup-content { font-size: 13px; }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 10px 42px 12px;
      display: grid;
      gap: 10px;
      box-shadow: 0 1px 6px rgba(0, 0, 0, .06);
    }
    .topbar-row {
      display: flex;
      align-items: end;
      gap: 12px;
      flex-wrap: wrap;
    }
    .toolbar-main { display: grid; grid-template-columns: auto minmax(260px, 1.3fr) minmax(190px, .8fr) minmax(260px, 1.1fr) auto; align-items: end; }
    .toolbar-secondary { align-items: center; gap: 14px; }
    .topbar .brand { align-self: center; font-weight: 800; font-size: 22px; color: var(--ink); white-space: nowrap; padding-right: 12px; }
    .topbar label { gap: 5px; font-size: 12px; min-width: 0; }
    .topbar label.search-wide { min-width: 240px; }
    .topbar label.compact { min-width: 150px; max-width: 230px; }
    .topbar select, .topbar input { min-width: 0; width: 100%; padding: 7px 9px; font-size: 14px; }
    .topbar .topstat { font-size: 13px; color: var(--muted); white-space: nowrap; }
    .topbar .topstat strong { color: var(--ink); font-size: 15px; }
    .topbar nav { margin-left: auto; display: flex; gap: 14px; flex-wrap: wrap; }
    .topbar nav a { color: var(--accent); text-decoration: none; font-size: 13px; font-weight: 600; }
    .topbar nav a:hover { text-decoration: underline; }
    .topbar button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--soft);
      color: var(--ink);
      font-weight: 600;
      padding: 8px 11px;
      cursor: pointer;
    }
    .topbar button:hover { border-color: var(--accent); color: var(--accent); }
    .scope-pill {
      border: 1px solid #c9d7d5;
      border-radius: 999px;
      background: var(--soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      padding: 6px 10px;
      white-space: nowrap;
    }
    #senderSelect { display: none; }
    section[id] { scroll-margin-top: 150px; }
    .tooltip {
      position: fixed;
      pointer-events: none;
      background: rgba(31, 41, 51, .94);
      color: #fff;
      padding: 7px 9px;
      border-radius: 6px;
      font-size: 12px;
      max-width: 260px;
      z-index: 5;
      display: none;
    }
    @media (max-width: 700px) {
      header, main, .topbar { padding-left: 18px; padding-right: 18px; }
      .grid { grid-template-columns: 1fr; }
      select, input { min-width: 100%; }
      .toolbar-main { grid-template-columns: 1fr; }
      .topbar .brand { padding-right: 0; }
      .topbar nav { margin-left: 0; }
    }
  </style>
</head>
<body>
  <header>
    <h1>unilife.ellep.it</h1>
    <p><strong>Research question:</strong> what explains the size of Erasmus+ Higher Education flows from one country to another? We frame destination choice as a gravity-style model where flows respond to the salary gap, perceived quality of life, institution quality, and language affinity between origin and destination.</p>
  </header>
  <div class="topbar">
    <div class="topbar-row toolbar-main">
      <span class="brand">UniLife</span>
      <label class="search-wide">Sending country
        <input id="countrySearch" list="countryOptions" autocomplete="off" placeholder="Search country or code">
        <datalist id="countryOptions"></datalist>
      </label>
      <label>Flow level
        <select id="orgLevel">
          <option value="countryUni">Country &rarr; university</option>
          <option value="uniCountry">University &rarr; country</option>
          <option value="uniUni">University &rarr; university</option>
        </select>
      </label>
      <label class="search-wide">University / place
        <input id="orgSearch" list="orgOptions" autocomplete="off" placeholder="Search university, city, country">
        <datalist id="orgOptions"></datalist>
      </label>
      <button id="clearOrgSearch" type="button">Clear</button>
      <select id="senderSelect" aria-hidden="true" tabindex="-1"></select>
    </div>
    <div class="topbar-row toolbar-secondary">
      <span class="scope-pill">KA1 study mobility · cross-border country pairs</span>
      <label class="compact">Map view
        <select id="mapView">
          <option value="sender">Selected sending country</option>
          <option value="all">All countries aggregate</option>
        </select>
      </label>
      <label class="compact">Salary country
        <select id="earnCountry"></select>
      </label>
      <label class="compact">Salary unit
        <select id="earnUnit">
          <option value="eur">Euro (EUR)</option>
          <option value="pps">Purchasing power standard (PPS)</option>
        </select>
      </label>
      <span class="topstat" id="topStat"></span>
      <nav>
        <a href="#sec-map">Map</a>
        <a href="#sec-university-flows">Universities</a>
        <a href="#sec-economics">Economics</a>
        <a href="#sec-salary">Salary</a>
        <a href="#sec-reddit">Reddit</a>
      </nav>
    </div>
  </div>
  <main>
    <section>
      <h2>The Model</h2>
      <p>We model each origin&ndash;destination flow as a gravity-style regression. This is the project's <strong>step-3 design</strong>: the specification below describes how the collected text and spatial data would be used to answer the research question. It is documented, not estimated.</p>
      <p class="note" style="font-size:15px"><code>log(1 + flow<sub>ij</sub>) = &beta;&#8321;&middot;salary_gap<sub>ij</sub> + &beta;&#8322;&middot;quality_of_life<sub>j</sub> + &beta;&#8323;&middot;institution_quality<sub>j</sub> + controls(gdp_gap, price_level_gap, distance, language_affinity) + origin FE + destination FE + &epsilon;<sub>ij</sub></code></p>
      <p class="note">Language affinity is a gravity control (a bilateral friction that directly shapes flows), not an instrument. Origin and destination fixed effects absorb broad country-level differences. The estimate is descriptive, not causal.</p>
    </section>

    <section>
      <h2>Explanatory Variables (the &beta;s)</h2>
      <p class="note">Each term in the model and its data source. <strong>built</strong> = data already in the processed pipeline; <strong>planned</strong> = part of the described design (text layer / rankings / language groupings).</p>
      <div class="cards">
__VARIABLE_CARDS__
      </div>
    </section>

    <section id="sec-overview">
      <h2>Selected Country Overview</h2>
      <div class="cards" id="summaryCards"></div>
      <p class="note">Use the sending-country selector in the top bar. Main flow definition: Higher Education learners, study mobility activity, age 18+, cross-border flows only.</p>
    </section>

    <section id="sec-map">
      <h2>University Flow Map</h2>
      <div id="map"></div>
      <div class="map-legend">
        <span><span class="legend-dot" style="width:10px;height:10px"></span> smaller flow</span>
        <span><span class="legend-dot" style="width:24px;height:24px"></span> larger flow</span>
        <span id="mapNote">One point per university endpoint, sized by students. Zoom out to aggregate nearby universities into clusters; click a cluster to zoom in and pick a university. Universities sit at their city coordinate; cities without a coordinate match fall back to their country centroid.</span>
      </div>
    </section>

    <section id="sec-university-flows">
      <h2>University-Level Flow Detail</h2>
      <p class="note" id="orgFlowNote"></p>
      <div id="orgFlowTable"></div>
    </section>

    <div class="grid">
      <section>
        <h2>Top Destinations</h2>
        <div class="chart" id="barChart"></div>
      </section>
      <section>
        <h2>GDP Gap and Flow Share &mdash; control</h2>
        <div class="chart" id="scatterChart"></div>
        <p class="note"><strong>GDP gap</strong> = receiving-country GDP per capita minus sending-country GDP per capita. <strong>Flow share</strong> = flow to that destination divided by all outgoing flows from the selected sending country.</p>
      </section>
    </div>

    <section>
      <h2>Selected Country Destination Table</h2>
      <div id="destinationTable"></div>
    </section>

    <section>
      <h2>Flow Heatmap</h2>
      <p class="note">Rows and columns use the same country order: countries are sorted by total Erasmus flow volume among the displayed top countries.</p>
      <div class="heatmap-wrap chart" id="heatmap"></div>
    </section>

    <section id="sec-economics">
      <h2>Flow-Weighted Destination Economics</h2>
      <p class="note">Click column headers to sort. Destination metrics are weighted by each sending country's flow counts.</p>
      <div id="weightedTable"></div>
    </section>

    <section id="sec-salary">
      <h2>Expected Earnings by Economic Sector &mdash; evidence for &beta;&#8321; (salary gap)</h2>
      <div class="chart" id="earningsChart"></div>
      <p class="note">Mean monthly gross earnings by NACE economic sector, Structure of Earnings Survey 2018. This is a salary-by-sector reference, <strong>not</strong> salary by field of study (Eurostat does not publish earnings by field of study). Coverage is limited to the 17 countries that report this dataset.</p>
    </section>

    <section id="sec-reddit">
      <h2>Perceived Quality of Life &mdash; evidence for &beta;&#8322; (Reddit r/Erasmus)</h2>
      <p class="note">Destination mentions extracted from r/Erasmus posts and comments with Gemini + Pydantic (city/country, sentiment, themes). <strong>Net sentiment</strong> = (positive &minus; negative) / mentions. <strong>Score-weighted net</strong> also weights by extraction confidence and log Reddit score. Per-country counts are small, so read this as a qualitative perception signal, not a precise measure. Click headers to sort.</p>
      <div id="redditTable"></div>
    </section>

    <section>
      <h2>Data Sources and Measurement Notes</h2>
      <ul class="source-list">
        <li><strong>Erasmus flows:</strong> <code>Erasmus-KA1-Mobility-Data-2022.xlsx</code>, sheet <code>KA1 mobilities 2022</code>. Filtered to Higher Education study mobility.</li>
        <li><strong>Flow scope:</strong> Erasmus mobility is modeled as cross-border origin&ndash;destination movement. Same-country rows in the KA1 file are extremely rare and treated as coding artifacts, not as a domestic Erasmus layer.</li>
        <li><strong>HE grants:</strong> <code>annual-report-2024-statistical-annex.xlsx</code>, sheet <code>KA1_estimated paxs</code>, Call Year 2022, Higher Education rows.</li>
        <li><strong>GDP per capita:</strong> World Bank current US$ is used for the dashboard GDP-gap plot because it covers more Erasmus partner countries; Eurostat GDP remains in the processed dataset.</li>
        <li><strong>Price levels and net earnings:</strong> Eurostat API. Missing values are shown as <code>n/a</code>.</li>
        <li><strong>Scholarship proxy:</strong> grant per participant is applicant-country-level, not the exact grant received by individual students or country pairs. Treat the social-elevator angle as descriptive, not causal.</li>
        <li><strong>Quality of life (built):</strong> Reddit <code>r/Erasmus</code> posts and comments, with destination, sentiment, and themes extracted via Gemini + Pydantic. Aggregated to per-country net sentiment. Feeds &beta;&#8322;. Per-country counts are small; treat as a qualitative perception layer.</li>
        <li><strong>Institution quality (planned):</strong> destination university ranking score. Feeds &beta;&#8323;.</li>
        <li><strong>Language affinity (planned):</strong> Mediterranean / Anglo-Saxon / Germanic country groupings used as an origin&ndash;destination affinity <strong>control</strong> (gravity friction), not an instrument.</li>
      </ul>
    </section>
  </main>
  <div class="tooltip" id="tooltip"></div>
  <script id="dashboard-data" type="application/json">__DATA__</script>
  <script>
    const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
    const flows = payload.flows;
    const countries = payload.countries;
    const weightedRows = payload.weighted;
    const orgFlowLevels = payload.orgFlowLevels;
    const orgFlowTables = payload.orgFlowTables;
    const sectorEarnings = payload.sectorEarnings;
    const redditByCountry = payload.redditByCountry || [];
    const senderSelect = document.getElementById('senderSelect');
    const countrySearch = document.getElementById('countrySearch');
    const countryOptions = document.getElementById('countryOptions');
    const orgLevelSelect = document.getElementById('orgLevel');
    const mapViewSelect = document.getElementById('mapView');
    const orgSearch = document.getElementById('orgSearch');
    const orgOptions = document.getElementById('orgOptions');
    const clearOrgSearch = document.getElementById('clearOrgSearch');
    const earnCountrySelect = document.getElementById('earnCountry');
    const earnUnitSelect = document.getElementById('earnUnit');
    const tooltip = document.getElementById('tooltip');
    let weightedSort = { key: 'outgoing', dir: -1 };
    let destinationSort = { key: 'flow_count', dir: -1 };
    let redditSort = { key: 'mentions', dir: -1 };

    const fmtInt = value => value == null ? 'n/a' : Math.round(value).toLocaleString('en-US');
    const fmtMoney = value => value == null ? 'n/a' : Math.round(value).toLocaleString('en-US');
    const fmtOne = value => value == null ? 'n/a' : Number(value).toLocaleString('en-US', { maximumFractionDigits: 1 });
    const fmtPct = value => value == null ? 'n/a' : (value * 100).toLocaleString('en-US', { maximumFractionDigits: 1 }) + '%';

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    }

    function showTip(event, html) {
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
      tooltip.style.left = Math.min(event.clientX + 12, window.innerWidth - 280) + 'px';
      tooltip.style.top = (event.clientY + 12) + 'px';
    }
    function hideTip() { tooltip.style.display = 'none'; }

    function extent(values) {
      const clean = values.filter(value => value != null && Number.isFinite(value));
      if (!clean.length) return [0, 1];
      let min = Math.min(...clean);
      let max = Math.max(...clean);
      if (min === max) { min -= 1; max += 1; }
      return [min, max];
    }

    function scale(value, domainMin, domainMax, rangeMin, rangeMax) {
      return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
    }

    function senderRows(code) {
      const rows = flows.filter(row => row.sending_code === code);
      const total = rows.reduce((sum, row) => sum + row.flow_count, 0);
      return rows.map(row => ({ ...row, flow_share: total ? row.flow_count / total : 0 }));
    }

    const norm = value => String(value ?? '').trim().toLowerCase();
    const countryLabel = country => `${country.code} - ${country.country}`;

    function populateSelect() {
      const activeCountries = countries.filter(country => country.outgoing > 0);
      senderSelect.innerHTML = activeCountries
        .map(country => `<option value="${country.code}">${escapeHtml(countryLabel(country))}</option>`)
        .join('');
      countryOptions.innerHTML = activeCountries
        .map(country => `<option value="${escapeHtml(countryLabel(country))}"></option>`)
        .join('');
      senderSelect.value = countries.find(country => country.code === 'IT') ? 'IT' : senderSelect.options[0].value;
      syncCountrySearch();
      senderSelect.addEventListener('change', updateCountry);
      countrySearch.addEventListener('change', selectCountryFromSearch);
      countrySearch.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
          event.preventDefault();
          selectCountryFromSearch();
        }
      });
      countrySearch.addEventListener('input', () => {
        const exact = findCountryMatch(countrySearch.value, true);
        if (exact && exact.code !== senderSelect.value) setCountry(exact.code);
      });
    }

    function findCountryMatch(value, exactOnly = false) {
      const query = norm(value);
      if (!query) return null;
      const activeCountries = countries.filter(country => country.outgoing > 0);
      const exact = activeCountries.find(country =>
        norm(country.code) === query ||
        norm(country.country) === query ||
        norm(countryLabel(country)) === query
      );
      if (exact || exactOnly) return exact || null;
      return activeCountries.find(country =>
        norm(country.code).startsWith(query) ||
        norm(country.country).includes(query) ||
        norm(countryLabel(country)).includes(query)
      ) || null;
    }

    function setCountry(code) {
      senderSelect.value = code;
      syncCountrySearch();
      updateCountry();
    }

    function syncCountrySearch() {
      const selected = countries.find(country => country.code === senderSelect.value);
      countrySearch.value = selected ? countryLabel(selected) : senderSelect.value;
    }

    function selectCountryFromSearch() {
      const match = findCountryMatch(countrySearch.value, false);
      if (match) {
        setCountry(match.code);
      } else {
        syncCountrySearch();
      }
    }

    function renderSummary(rows) {
      const first = rows[0] || {};
      const total = rows.reduce((sum, row) => sum + row.flow_count, 0);
      const richerShare = rows.filter(row => row.gdp_gap_usd_wb > 0).reduce((sum, row) => sum + row.flow_count, 0) / total;
      const destinations = new Set(rows.map(row => row.receiving_code)).size;
      const grantPerEstimated = first.sender_he_grant_per_estimated_participant_eur;
      const grants = first.sender_he_grants_eur;
      document.getElementById('summaryCards').innerHTML = [
        ['Outgoing students', fmtInt(total)],
        ['Destinations', fmtInt(destinations)],
        ['Share to richer GDP pc countries', fmtPct(richerShare)],
        ['HE grants, EUR', fmtMoney(grants)],
        ['Grant per estimated participant', fmtMoney(grantPerEstimated)]
      ].map(([label, value]) => `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
    }

    function renderBar(rows) {
      const data = [...rows].sort((a, b) => b.flow_count - a.flow_count).slice(0, 12).reverse();
      const width = 760;
      const rowH = 28;
      const left = 130;
      const right = 70;
      const height = 44 + data.length * rowH;
      const max = Math.max(...data.map(row => row.flow_count), 1);
      const bars = data.map((row, i) => {
        const y = 24 + i * rowH;
        const w = scale(row.flow_count, 0, max, 0, width - left - right);
        const label = `${row.receiving_code} - ${row.receiving_country}`;
        const tip = `${escapeHtml(label)}<br>${fmtInt(row.flow_count)} students<br>${fmtPct(row.flow_share)} of outgoing flow`;
        return `<g data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()">
          <text x="${left - 8}" y="${y + 16}" text-anchor="end" class="axis-text">${escapeHtml(row.receiving_code)}</text>
          <rect class="bar" x="${left}" y="${y}" width="${w}" height="18" rx="3"></rect>
          <text x="${left + w + 6}" y="${y + 14}" class="axis-text">${fmtInt(row.flow_count)}</text>
        </g>`;
      }).join('');
      document.getElementById('barChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${bars}</svg>`;
    }

    function renderScatter(rows) {
      const data = rows.filter(row => row.gdp_gap_usd_wb != null);
      const width = 760, height = 430, left = 72, right = 28, top = 24, bottom = 54;
      const [rawXMin, rawXMax] = extent(data.map(row => row.gdp_gap_usd_wb));
      const xMin = Math.min(rawXMin, 0), xMax = Math.max(rawXMax, 0);
      const [yMin, yMax] = [0, Math.max(...data.map(row => row.flow_share), 0.01)];
      const zeroX = scale(0, xMin, xMax, left, width - right);
      const circles = data.map(row => {
        const x = scale(row.gdp_gap_usd_wb, xMin, xMax, left, width - right);
        const y = scale(row.flow_share, yMin, yMax, height - bottom, top);
        const r = Math.max(4, Math.min(18, Math.sqrt(row.flow_count) / 3.2));
        const label = `${row.sending_code} to ${row.receiving_code}`;
        const tip = `${escapeHtml(label)}<br>${fmtInt(row.flow_count)} students<br>Flow share: ${fmtPct(row.flow_share)}<br>GDP gap: ${fmtMoney(row.gdp_gap_usd_wb)} US$`;
        return `<circle class="point" cx="${x}" cy="${y}" r="${r}" data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()"></circle>`;
      }).join('');
      document.getElementById('scatterChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">
        <line class="axis" x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}"></line>
        <line class="axis" x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}"></line>
        <line class="zero-line" x1="${zeroX}" y1="${top}" x2="${zeroX}" y2="${height - bottom}"></line>
        ${circles}
        <text class="axis-text" x="${left}" y="${height - 16}">poorer destination</text>
        <text class="axis-text" x="${width - right}" y="${height - 16}" text-anchor="end">richer destination</text>
        <text class="axis-text" x="${width / 2}" y="${height - 16}" text-anchor="middle">GDP pc gap</text>
        <text class="axis-text" x="12" y="${top}" transform="rotate(-90 12 ${top})">flow share</text>
      </svg>`;
    }

    function sortableHeader(label, key, tableName) {
      return `<th class="sortable" data-table="${tableName}" data-key="${key}">${label}</th>`;
    }

    function sortRows(rows, sort) {
      return [...rows].sort((a, b) => {
        const av = a[sort.key], bv = b[sort.key];
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        if (typeof av === 'string') return av.localeCompare(bv) * sort.dir;
        return (av - bv) * sort.dir;
      });
    }

    function renderDestinationTable(rows) {
      const sorted = sortRows(rows, destinationSort);
      const body = sorted.map(row => `<tr>
        <td>${escapeHtml(row.receiving_code)}</td>
        <td>${escapeHtml(row.receiving_country)}</td>
        <td>${fmtInt(row.flow_count)}</td>
        <td>${fmtPct(row.flow_share)}</td>
        <td>${fmtMoney(row.receiver_gdp_pc_current_usd_wb)}</td>
        <td>${fmtMoney(row.gdp_gap_usd_wb)}</td>
        <td>${fmtOne(row.price_level_gap)}</td>
        <td>${fmtMoney(row.earnings_gap)}</td>
      </tr>`).join('');
      document.getElementById('destinationTable').innerHTML = `<table class="data-table">
        <thead><tr>
          ${sortableHeader('Code', 'receiving_code', 'destination')}
          ${sortableHeader('Destination', 'receiving_country', 'destination')}
          ${sortableHeader('Students', 'flow_count', 'destination')}
          ${sortableHeader('Flow share', 'flow_share', 'destination')}
          ${sortableHeader('Receiver GDP pc US$', 'receiver_gdp_pc_current_usd_wb', 'destination')}
          ${sortableHeader('GDP gap US$', 'gdp_gap_usd_wb', 'destination')}
          ${sortableHeader('Price gap', 'price_level_gap', 'destination')}
          ${sortableHeader('Earnings gap EUR', 'earnings_gap', 'destination')}
        </tr></thead><tbody>${body}</tbody></table>`;
    }

    function renderWeightedTable() {
      const rows = sortRows(weightedRows, weightedSort);
      const body = rows.map(row => `<tr>
        <td>${escapeHtml(row.code)}</td>
        <td>${escapeHtml(row.sender.replace(row.code + ' - ', ''))}</td>
        <td>${fmtInt(row.outgoing)}</td>
        <td>${fmtMoney(row.weighted_gdp_pc_usd)}</td>
        <td>${fmtOne(row.weighted_price_level)}</td>
        <td>${fmtMoney(row.weighted_net_earnings_eur)}</td>
        <td>${fmtMoney(row.grant_per_estimated_participant_eur)}</td>
        <td>${fmtMoney(row.grant_per_actual_participant_eur)}</td>
      </tr>`).join('');
      document.getElementById('weightedTable').innerHTML = `<table class="data-table">
        <thead><tr>
          ${sortableHeader('Code', 'code', 'weighted')}
          ${sortableHeader('Sender', 'sender', 'weighted')}
          ${sortableHeader('Outgoing students', 'outgoing', 'weighted')}
          ${sortableHeader('Weighted destination GDP pc US$', 'weighted_gdp_pc_usd', 'weighted')}
          ${sortableHeader('Weighted destination price level', 'weighted_price_level', 'weighted')}
          ${sortableHeader('Weighted destination earnings EUR', 'weighted_net_earnings_eur', 'weighted')}
          ${sortableHeader('Grant per estimated participant EUR', 'grant_per_estimated_participant_eur', 'weighted')}
          ${sortableHeader('Grant per actual participant EUR', 'grant_per_actual_participant_eur', 'weighted')}
        </tr></thead><tbody>${body}</tbody></table>`;
    }

    function renderHeatmap() {
      const order = countries.filter(country => country.total > 0).slice(0, 30);
      const codes = order.map(country => country.code);
      const byPair = new Map(flows.map(row => [`${row.sending_code}|${row.receiving_code}`, row]));
      const max = Math.max(...flows.filter(row => codes.includes(row.sending_code) && codes.includes(row.receiving_code)).map(row => row.flow_count), 1);
      const cell = 18, left = 92, top = 78, width = left + codes.length * cell + 18, height = top + codes.length * cell + 24;
      const labelsX = codes.map((code, i) => `<text class="axis-text" x="${left + i * cell + 12}" y="${top - 8}" transform="rotate(-60 ${left + i * cell + 12} ${top - 8})">${code}</text>`).join('');
      const labelsY = codes.map((code, i) => `<text class="axis-text" x="${left - 8}" y="${top + i * cell + 13}" text-anchor="end">${code}</text>`).join('');
      const cells = codes.flatMap((sender, yIdx) => codes.map((receiver, xIdx) => {
        const row = byPair.get(`${sender}|${receiver}`);
        const value = row ? row.flow_count : 0;
        const intensity = value ? Math.max(0.12, Math.log1p(value) / Math.log1p(max)) : 0;
        const color = value ? `rgba(47, 111, 115, ${intensity})` : '#f3f5f5';
        const text = row ? `${sender} to ${receiver}<br>${fmtInt(value)} students` : `${sender} to ${receiver}<br>0 students`;
        return `<rect x="${left + xIdx * cell}" y="${top + yIdx * cell}" width="${cell - 1}" height="${cell - 1}" fill="${color}" data-tip="${text}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()"></rect>`;
      })).join('');
      document.getElementById('heatmap').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${labelsX}${labelsY}${cells}</svg>`;
    }

    function wireSorting() {
      document.body.addEventListener('click', event => {
        const th = event.target.closest('th.sortable');
        if (!th) return;
        const table = th.dataset.table;
        const key = th.dataset.key;
        if (table === 'destination') {
          destinationSort = { key, dir: destinationSort.key === key ? -destinationSort.dir : -1 };
          updateCountry();
        }
        if (table === 'weighted') {
          weightedSort = { key, dir: weightedSort.key === key ? -weightedSort.dir : -1 };
          renderWeightedTable();
        }
        if (table === 'reddit') {
          redditSort = { key, dir: redditSort.key === key ? -redditSort.dir : -1 };
          renderRedditTable();
        }
      });
    }

    function netBadge(value) {
      if (value == null) return 'n/a';
      const sign = value > 0 ? '+' : '';
      const color = value > 0.05 ? 'var(--accent)' : value < -0.05 ? 'var(--accent-2)' : 'var(--muted)';
      return `<strong style="color:${color}">${sign}${value.toFixed(2)}</strong>`;
    }

    function renderRedditTable() {
      if (!redditByCountry.length) {
        document.getElementById('redditTable').innerHTML = '<p class="note">No extracted mentions found. Run scripts/extract_reddit.py first.</p>';
        return;
      }
      const rows = sortRows(redditByCountry, redditSort);
      const body = rows.map(row => `<tr>
        <td>${escapeHtml(row.country)}</td>
        <td>${fmtInt(row.mentions)}</td>
        <td>${fmtInt(row.positive)}</td>
        <td>${fmtInt(row.neutral)}</td>
        <td>${fmtInt(row.negative)}</td>
        <td>${netBadge(row.net)}</td>
        <td>${netBadge(row.weightedNet)}</td>
        <td>${row.avgScore == null ? '' : row.avgScore.toFixed(1)}</td>
        <td style="text-align:left;white-space:normal">${escapeHtml(row.positiveThemes || '')}</td>
        <td style="text-align:left;white-space:normal">${escapeHtml(row.negativeThemes || '')}</td>
      </tr>`).join('');
      document.getElementById('redditTable').innerHTML = `<table class="data-table">
        <thead><tr>
          ${sortableHeader('Destination country', 'country', 'reddit')}
          ${sortableHeader('Mentions', 'mentions', 'reddit')}
          ${sortableHeader('Positive', 'positive', 'reddit')}
          ${sortableHeader('Neutral', 'neutral', 'reddit')}
          ${sortableHeader('Negative', 'negative', 'reddit')}
          ${sortableHeader('Net sentiment', 'net', 'reddit')}
          ${sortableHeader('Score-weighted net', 'weightedNet', 'reddit')}
          ${sortableHeader('Avg. score', 'avgScore', 'reddit')}
          <th style="text-align:left">Positive themes</th>
          <th style="text-align:left">Negative themes</th>
        </tr></thead><tbody>${body}</tbody></table>`;
    }

    let map = null;
    let clusterLayer = null;
    const orgLevelLabels = {
      countryUni: 'country → university',
      uniCountry: 'university → country',
      uniUni: 'university → university'
    };
    const mapNotes = {
      countryUni: 'Country → university: points are receiving universities, sized by students arriving from the selected sending country or from all countries.',
      uniCountry: 'University → country: points are destination countries. Search a sending university to see its arrival countries.',
      uniUni: 'University → university: points are receiving universities, with popups showing the sending university for selected-country rows.'
    };

    function orgQuery() {
      return norm(orgSearch.value);
    }

    function recordMatchesSearch(record, query) {
      if (!query) return true;
      return Object.values(record).some(value => norm(value).includes(query));
    }

    function currentOrgRows() {
      const level = orgLevelSelect.value;
      return (orgFlowTables[level] || [])
        .filter(row => row.sending_code === senderSelect.value)
        .filter(row => recordMatchesSearch(row, orgQuery()))
        .sort((a, b) => b.flow_count - a.flow_count);
    }

    function populateOrgOptions() {
      const level = orgLevelSelect.value;
      const rows = (orgFlowTables[level] || [])
        .filter(row => mapViewSelect.value === 'all' || row.sending_code === senderSelect.value);
      const values = new Set();
      rows.forEach(row => {
        [
          row.sending_org, row.receiving_org,
          row.sending_city, row.receiving_city,
          row.receiving_country,
        ].forEach(value => {
          if (value && String(value).trim()) values.add(String(value).trim());
        });
      });
      orgOptions.innerHTML = [...values]
        .sort((a, b) => a.localeCompare(b))
        .slice(0, 1200)
        .map(value => `<option value="${escapeHtml(value)}"></option>`)
        .join('');
    }

    function clusterFlow(cluster) {
      return cluster.getAllChildMarkers().reduce((sum, marker) => sum + (marker.options.flow || 0), 0);
    }

    function initMap() {
      map = L.map('map', { scrollWheelZoom: false }).setView([50, 12], 4);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 14,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      clusterLayer = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 48,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: cluster => {
          const total = clusterFlow(cluster);
          const size = total >= 5000 ? 52 : total >= 1000 ? 44 : total >= 200 ? 36 : 28;
          return L.divIcon({
            html: `<div style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:50%;background:rgba(47,111,115,.78);color:#fff;font-size:12px;font-weight:700;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">${fmtInt(total)}</div>`,
            className: 'flow-cluster',
            iconSize: [size, size]
          });
        }
      }).addTo(map);
    }

    function renderMap() {
      if (!map) return;
      clusterLayer.clearLayers();
      const view = mapViewSelect.value;
      const level = orgLevelSelect.value;
      const levelRecords = orgFlowLevels[level] || { points: [], all: [] };
      const query = orgQuery();
      const points = view === 'all'
        ? (query && levelRecords.allSearch ? levelRecords.allSearch : levelRecords.all)
        : levelRecords.points.filter(point => point.s === senderSelect.value);
      const filteredPoints = points.filter(point => recordMatchesSearch(point, query));
      document.getElementById('mapNote').textContent = mapNotes[level];
      if (!filteredPoints.length) return;
      const maxFlow = Math.max(...filteredPoints.map(point => point.f), 1);
      const markers = [];
      const bounds = [];
      filteredPoints.forEach(point => {
        const radius = 4 + 16 * Math.sqrt(point.f / maxFlow);
        const fallback = point.m !== 'city';
        const color = fallback ? '#b44e5a' : '#2f6f73';
        const marker = L.circleMarker([point.la, point.lo], {
          radius, color, weight: 1, fillColor: color, fillOpacity: 0.55, flow: point.f
        });
        const where = fallback ? ' (city without coordinate match: country-level estimate)' : '';
        marker.bindPopup(mapPopup(point, level, where));
        marker.bindTooltip(`${escapeHtml(point.o)}: ${fmtInt(point.f)}`);
        markers.push(marker);
        bounds.push([point.la, point.lo]);
      });
      clusterLayer.addLayers(markers);
      if (bounds.length) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 7 });
      }
    }

    function mapPopup(point, level, where) {
      if (level === 'uniCountry') {
        const origin = point.so ? `<strong>${escapeHtml(point.so)}</strong><br>${escapeHtml(point.sc)} &rarr; ` : '';
        return `${origin}<strong>${escapeHtml(point.dc)} - ${escapeHtml(point.o)}</strong><br>${escapeHtml(point.c)}${where}<br>${fmtInt(point.f)} students`;
      }
      if (level === 'uniUni' && point.so) {
        return `<strong>${escapeHtml(point.so)}</strong><br>${escapeHtml(point.sc)} &rarr; <strong>${escapeHtml(point.o)}</strong><br>${escapeHtml(point.c)}, ${escapeHtml(point.n)}${where}<br>${fmtInt(point.f)} students`;
      }
      return `<strong>${escapeHtml(point.o)}</strong><br>${escapeHtml(point.c)}, ${escapeHtml(point.n)}${where}<br>${fmtInt(point.f)} students`;
    }

    function renderOrgFlowTable() {
      const level = orgLevelSelect.value;
      const rows = currentOrgRows();
      const query = orgQuery();
      const filteredText = query ? ` matching "${orgSearch.value}"` : '';
      const note = `Showing ${rows.length} ${orgLevelLabels[level]} rows${filteredText} for the selected sending country. Organization names come from the Erasmus KA1 file and are normalized only lightly.`;
      document.getElementById('orgFlowNote').textContent = note;
      if (!rows.length) {
        document.getElementById('orgFlowTable').innerHTML = '<p class="note">No university-level rows for this selected country.</p>';
        return;
      }
      let header = '';
      let body = '';
      if (level === 'countryUni') {
        header = '<th>Destination country</th><th>Receiving city</th><th>Receiving university</th><th>Students</th>';
        body = rows.map(row => `<tr>
          <td>${escapeHtml(row.receiving_code)} - ${escapeHtml(row.receiving_country)}</td>
          <td>${escapeHtml(row.receiving_city)}</td>
          <td style="text-align:left;white-space:normal">${escapeHtml(row.receiving_org)}</td>
          <td>${fmtInt(row.flow_count)}</td>
        </tr>`).join('');
      } else if (level === 'uniCountry') {
        header = '<th>Sending city</th><th>Sending university</th><th>Destination country</th><th>Students</th>';
        body = rows.map(row => `<tr>
          <td>${escapeHtml(row.sending_city)}</td>
          <td style="text-align:left;white-space:normal">${escapeHtml(row.sending_org)}</td>
          <td>${escapeHtml(row.receiving_code)} - ${escapeHtml(row.receiving_country)}</td>
          <td>${fmtInt(row.flow_count)}</td>
        </tr>`).join('');
      } else {
        header = '<th>Sending city</th><th>Sending university</th><th>Receiving country</th><th>Receiving city</th><th>Receiving university</th><th>Students</th>';
        body = rows.map(row => `<tr>
          <td>${escapeHtml(row.sending_city)}</td>
          <td style="text-align:left;white-space:normal">${escapeHtml(row.sending_org)}</td>
          <td>${escapeHtml(row.receiving_code)} - ${escapeHtml(row.receiving_country)}</td>
          <td>${escapeHtml(row.receiving_city)}</td>
          <td style="text-align:left;white-space:normal">${escapeHtml(row.receiving_org)}</td>
          <td>${fmtInt(row.flow_count)}</td>
        </tr>`).join('');
      }
      document.getElementById('orgFlowTable').innerHTML = `<table class="data-table">
        <thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
    }

    function updateCountry() {
      const rows = senderRows(senderSelect.value);
      const total = rows.reduce((sum, row) => sum + row.flow_count, 0);
      const selected = countries.find(country => country.code === senderSelect.value);
      document.getElementById('topStat').innerHTML = selected
        ? `${escapeHtml(selected.country)}: <strong>${fmtInt(total)}</strong> outgoing students`
        : '';
      renderSummary(rows);
      renderBar(rows);
      renderScatter(rows);
      renderDestinationTable(rows);
      populateOrgOptions();
      renderOrgFlowTable();
      if (mapViewSelect.value === 'sender') renderMap();
    }

    function populateEarnCountries() {
      const seen = new Map();
      sectorEarnings.forEach(row => { if (!seen.has(row.code)) seen.set(row.code, row.country); });
      const options = [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]));
      earnCountrySelect.innerHTML = options
        .map(([code, country]) => `<option value="${code}">${escapeHtml(country)}</option>`)
        .join('');
      earnCountrySelect.value = seen.has('ES') ? 'ES' : options[0][0];
    }

    function renderEarnings() {
      const code = earnCountrySelect.value;
      const unit = earnUnitSelect.value;
      const data = sectorEarnings
        .filter(row => row.code === code && row[unit] != null)
        .sort((a, b) => b[unit] - a[unit]);
      if (!data.length) {
        document.getElementById('earningsChart').innerHTML = '<p class="note">No data for this country.</p>';
        return;
      }
      const reversed = [...data].reverse();
      const width = 760, rowH = 26, left = 240, right = 80;
      const height = 30 + reversed.length * rowH;
      const max = Math.max(...reversed.map(row => row[unit]), 1);
      const unitLabel = unit === 'eur' ? 'EUR' : 'PPS';
      const bars = reversed.map((row, i) => {
        const y = 16 + i * rowH;
        const w = scale(row[unit], 0, max, 0, width - left - right);
        const tip = `${escapeHtml(row.label)}<br>${fmtMoney(row[unit])} ${unitLabel}/month`;
        return `<g data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()">
          <text x="${left - 8}" y="${y + 14}" text-anchor="end" class="axis-text">${escapeHtml(row.label.length > 38 ? row.label.slice(0, 37) + '…' : row.label)}</text>
          <rect class="bar" x="${left}" y="${y}" width="${w}" height="17" rx="3"></rect>
          <text x="${left + w + 6}" y="${y + 13}" class="axis-text">${fmtMoney(row[unit])}</text>
        </g>`;
      }).join('');
      document.getElementById('earningsChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${bars}</svg>`;
    }

    populateSelect();
    wireSorting();
    updateCountry();
    renderHeatmap();
    renderWeightedTable();
    populateEarnCountries();
    renderEarnings();
    earnCountrySelect.addEventListener('change', renderEarnings);
    earnUnitSelect.addEventListener('change', renderEarnings);
    renderRedditTable();
    orgLevelSelect.addEventListener('change', () => {
      populateOrgOptions();
      renderOrgFlowTable();
      renderMap();
    });
    mapViewSelect.addEventListener('change', () => {
      populateOrgOptions();
      renderMap();
    });
    orgSearch.addEventListener('input', () => {
      renderOrgFlowTable();
      renderMap();
    });
    clearOrgSearch.addEventListener('click', () => {
      orgSearch.value = '';
      renderOrgFlowTable();
      renderMap();
    });
    populateOrgOptions();
    if (typeof L !== 'undefined') {
      initMap();
      renderMap();
    }
  </script>
</body>
</html>
"""
    html = html.replace("__VARIABLE_CARDS__", render_variable_cards(MODEL_VARIABLES))
    return html.replace("__DATA__", data_json)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_dashboard(), encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
