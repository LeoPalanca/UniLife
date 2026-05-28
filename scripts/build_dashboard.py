from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_PATH = Path("data/processed/ka1_he_studies_flows_with_indicators.csv")
ORG_FLOWS_PATH = Path("data/processed/erasmus_org_flows_long.csv")
CITY_COORDS_PATH = Path("data/processed/city_coordinates.csv")
SECTOR_EARNINGS_PATH = Path("data/processed/sector_earnings_2018.csv")
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


def org_point_records(top_per_sender: int = 250) -> tuple[list[dict], list[dict]]:
    """Compact per-sender university points plus an all-inbound aggregate.

    University points are placed at their receiving-city coordinate (no
    per-university geocoding exists), so clustering groups same-city
    universities. Returns (perSender, allInbound).
    """
    flows = pd.read_csv(ORG_FLOWS_PATH)
    coords = pd.read_csv(CITY_COORDS_PATH)[
        ["receiving_code", "receiving_city", "lat", "lon", "match_level"]
    ]
    merged = flows.merge(coords, on=["receiving_code", "receiving_city"], how="left")
    merged = merged.dropna(subset=["lat", "lon"])

    capped = merged.sort_values(["sending_code", "flow_count"], ascending=[True, False])
    capped = capped.groupby("sending_code", group_keys=False).head(top_per_sender)

    def compact(row: pd.Series, with_sender: bool) -> dict:
        record = {
            "o": row["receiving_org"],
            "c": row["receiving_city"],
            "n": row["receiving_country"],
            "la": round(float(row["lat"]), 3),
            "lo": round(float(row["lon"]), 3),
            "f": int(row["flow_count"]),
            "m": row["match_level"],
        }
        if with_sender:
            record["s"] = row["sending_code"]
        return record

    per_sender = [compact(row, True) for _, row in capped.iterrows()]

    inbound = (
        merged.groupby(
            ["receiving_org", "receiving_city", "receiving_country", "lat", "lon", "match_level"],
            as_index=False,
        )["flow_count"]
        .sum()
        .sort_values("flow_count", ascending=False)
    )
    all_inbound = [compact(row, False) for _, row in inbound.iterrows()]
    return per_sender, all_inbound


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


def build_dashboard() -> str:
    flows = pd.read_csv(DATA_PATH)
    org_points, org_inbound = org_point_records()
    payload = {
        "flows": clean_records(flows),
        "countries": country_records(flows),
        "weighted": weighted_records(flows),
        "orgPoints": org_points,
        "orgInbound": org_inbound,
        "sectorEarnings": sector_earnings_records(),
    }
    data_json = json.dumps(payload, separators=(",", ":"))

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
    select {
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
    .map-controls { margin-bottom: 14px; }
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
      header, main { padding-left: 18px; padding-right: 18px; }
      .grid { grid-template-columns: 1fr; }
      select { min-width: 100%; }
    }
  </style>
</head>
<body>
  <header>
    <h1>unilife.ellep.it</h1>
    <p>Interactive Erasmus+ Higher Education study mobility dashboard. Flows come from the KA1 2022 researcher file and are joined to GDP, price-level, earnings, and Higher Education grant metrics for descriptive analysis.</p>
  </header>
  <main>
    <section>
      <h2>Choose a Sending Country</h2>
      <div class="controls">
        <label>Sending country
          <select id="senderSelect"></select>
        </label>
      </div>
      <div class="cards" id="summaryCards"></div>
      <p class="note">Main flow definition: Higher Education learners, study mobility activity, age 18+, cross-border flows only.</p>
    </section>

    <section>
      <h2>Destination University Map</h2>
      <div class="controls map-controls">
        <label>Map view
          <select id="mapView">
            <option value="sender">Selected country's destinations</option>
            <option value="all">All inbound flows (Europe-wide)</option>
          </select>
        </label>
      </div>
      <div id="map"></div>
      <div class="map-legend">
        <span><span class="legend-dot" style="width:10px;height:10px"></span> smaller flow</span>
        <span><span class="legend-dot" style="width:24px;height:24px"></span> larger flow</span>
        <span>One point per receiving university, sized by incoming students. Zoom out to aggregate nearby universities into clusters; click a cluster to zoom in and pick a university. Universities sit at their city coordinate; cities without a coordinate match fall back to their country centroid.</span>
      </div>
    </section>

    <div class="grid">
      <section>
        <h2>Top Destinations</h2>
        <div class="chart" id="barChart"></div>
      </section>
      <section>
        <h2>GDP Gap and Flow Share</h2>
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

    <section>
      <h2>Flow-Weighted Destination Economics</h2>
      <p class="note">Click column headers to sort. Destination metrics are weighted by each sending country's flow counts.</p>
      <div id="weightedTable"></div>
    </section>

    <section>
      <h2>Expected Earnings by Economic Sector</h2>
      <div class="controls">
        <label>Country
          <select id="earnCountry"></select>
        </label>
        <label>Unit
          <select id="earnUnit">
            <option value="eur">Euro (EUR)</option>
            <option value="pps">Purchasing power standard (PPS)</option>
          </select>
        </label>
      </div>
      <div class="chart" id="earningsChart"></div>
      <p class="note">Mean monthly gross earnings by NACE economic sector, Structure of Earnings Survey 2018. This is a salary-by-sector reference, <strong>not</strong> salary by field of study (Eurostat does not publish earnings by field of study). Coverage is limited to the 17 countries that report this dataset.</p>
    </section>

    <section>
      <h2>Data Sources and Measurement Notes</h2>
      <ul class="source-list">
        <li><strong>Erasmus flows:</strong> <code>Erasmus-KA1-Mobility-Data-2022.xlsx</code>, sheet <code>KA1 mobilities 2022</code>. Filtered to Higher Education study mobility.</li>
        <li><strong>HE grants:</strong> <code>annual-report-2024-statistical-annex.xlsx</code>, sheet <code>KA1_estimated paxs</code>, Call Year 2022, Higher Education rows.</li>
        <li><strong>GDP per capita:</strong> World Bank current US$ is used for the dashboard GDP-gap plot because it covers more Erasmus partner countries; Eurostat GDP remains in the processed dataset.</li>
        <li><strong>Price levels and net earnings:</strong> Eurostat API. Missing values are shown as <code>n/a</code>.</li>
        <li><strong>Scholarship proxy:</strong> grant per participant is applicant-country-level, not the exact grant received by individual students or country pairs. Treat the social-elevator angle as descriptive, not causal.</li>
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
    const orgPoints = payload.orgPoints;
    const orgInbound = payload.orgInbound;
    const sectorEarnings = payload.sectorEarnings;
    const senderSelect = document.getElementById('senderSelect');
    const mapViewSelect = document.getElementById('mapView');
    const earnCountrySelect = document.getElementById('earnCountry');
    const earnUnitSelect = document.getElementById('earnUnit');
    const tooltip = document.getElementById('tooltip');
    let weightedSort = { key: 'outgoing', dir: -1 };
    let destinationSort = { key: 'flow_count', dir: -1 };

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

    function populateSelect() {
      senderSelect.innerHTML = countries
        .filter(country => country.outgoing > 0)
        .map(country => `<option value="${country.code}">${escapeHtml(country.code + ' - ' + country.country)}</option>`)
        .join('');
      senderSelect.value = countries.find(country => country.code === 'IT') ? 'IT' : senderSelect.options[0].value;
      senderSelect.addEventListener('change', updateCountry);
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
      });
    }

    let map = null;
    let clusterLayer = null;

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
      const points = view === 'all'
        ? orgInbound
        : orgPoints.filter(point => point.s === senderSelect.value);
      if (!points.length) return;
      const maxFlow = Math.max(...points.map(point => point.f), 1);
      const markers = [];
      const bounds = [];
      points.forEach(point => {
        const radius = 4 + 16 * Math.sqrt(point.f / maxFlow);
        const fallback = point.m !== 'city';
        const color = fallback ? '#b44e5a' : '#2f6f73';
        const marker = L.circleMarker([point.la, point.lo], {
          radius, color, weight: 1, fillColor: color, fillOpacity: 0.55, flow: point.f
        });
        const where = fallback ? ' (city without coordinate match: country-level estimate)' : '';
        marker.bindPopup(`<strong>${escapeHtml(point.o)}</strong><br>${escapeHtml(point.c)}, ${escapeHtml(point.n)}${where}<br>${fmtInt(point.f)} incoming students`);
        marker.bindTooltip(`${escapeHtml(point.o)}: ${fmtInt(point.f)}`);
        markers.push(marker);
        bounds.push([point.la, point.lo]);
      });
      clusterLayer.addLayers(markers);
      if (bounds.length) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 7 });
      }
    }

    function updateCountry() {
      const rows = senderRows(senderSelect.value);
      renderSummary(rows);
      renderBar(rows);
      renderScatter(rows);
      renderDestinationTable(rows);
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
    if (typeof L !== 'undefined') {
      initMap();
      mapViewSelect.addEventListener('change', renderMap);
      renderMap();
    }
  </script>
</body>
</html>
"""
    return html.replace("__DATA__", data_json)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_dashboard(), encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
