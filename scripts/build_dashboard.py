"""Assemble the self-contained dashboard HTML.

Payload builders live in `erasmusgravity.dashboard.payload`. This script
imports them, packs the JSON payload, and inlines it into the HTML/CSS/JS
template defined in `build_dashboard()` below.

Output: `dashboard/dist/index.html` (one self-contained file).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.db import read_table
from erasmusgravity.dashboard import (
    DATA_PATH,
    FLOW_COLUMNS,
    MODEL_VARIABLES,
    OUTPUT_PATH,
    clean_records,
    country_records,
    covid_event_study,
    covid_event_study_employment,
    json_safe,
    model_coefficients,
    org_flow_map_records,
    org_flow_table_records,
    panel_year_effects,
    reddit_meta,
    reddit_records,
    regression_results,
    render_variable_cards,
    sector_earnings_records,
    time_series_records,
    weighted_records,
)


def build_dashboard() -> str:
    flows = read_table(DATA_PATH)
    org_flow_levels = org_flow_map_records()
    payload = {
        "flows": clean_records(flows),
        "countries": country_records(flows),
        "weighted": weighted_records(flows),
        "orgFlowLevels": org_flow_levels,
        "orgFlowTables": org_flow_table_records(),
        "sectorEarnings": sector_earnings_records(),
        "redditByCountry": reddit_records(),
        "redditMeta": reddit_meta(),
        "timeSeries": time_series_records(),
        "regressionResults": regression_results(),
        "panelYears": panel_year_effects(),
        "covidEventStudy": covid_event_study(),
        "covidEventStudyEmployment": covid_event_study_employment(),
        "modelCoefficients": model_coefficients(),
    }
    return render_dashboard(payload)


def render_dashboard(payload: dict) -> str:
    """Render existing analytical outputs without re-estimating or collecting data."""
    data_json = json.dumps(json_safe(payload), separators=(",", ":"), allow_nan=False)

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ErasmusGravity · Erasmus mobility research</title>
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
    .heatmap-wrap { overflow: auto; padding: 0; }
    .heatmap-wrap svg { display: block; margin: 0; }
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
    .trend-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
    }
    .trend-legend span { display: inline-flex; align-items: center; }
    .legend-swatch {
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 2px;
      margin-right: 6px;
    }
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
    /* ErasmusGravity design-system layer, adapted from dashboard/mockup.html. */
    :root {
      --ink-strong: #11181f;
      --faint: #8a949d;
      --line-soft: #e7ebef;
      --soft-2: #f3f5f5;
      --accent-deep: #234f52;
      --accent-bright: #37868b;
      --accent-2-deep: #8f3b46;
      --positive: #2f6f73;
      --negative: #b44e5a;
      --neutral: #5f6b76;
      --c3: #c98a2b;
      --c4: #4a6fa5;
      --c5: #6b8f3a;
      --c6: #8a5a9e;
      --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Palladio, Georgia, "Times New Roman", serif;
      --mono: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, "Liberation Mono", monospace;
      --radius: 8px;
      --shadow: 0 1px 2px rgba(17,24,31,.04), 0 8px 24px -16px rgba(17,24,31,.28);
    }
    html { scroll-behavior: smooth; }
    body {
      font-family: var(--sans);
      font-size: 15px;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      font-variant-numeric: tabular-nums;
    }
    h1, h2, h3, h4, p { margin: 0; }
    code { font-family: var(--mono); }
    .pagehead {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 64px 42px 48px;
      position: relative;
      overflow: hidden;
    }
    .hero-inner {
      max-width: 1320px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 32px;
      align-items: center;
    }
    .kicker {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .16em;
      text-transform: uppercase;
      color: var(--accent);
      display: inline-flex;
      align-items: center;
      gap: 9px;
      margin-bottom: 18px;
    }
    .kicker .dot { width: 18px; height: 18px; }
    .pagehead h1 {
      font-size: clamp(34px, 4.6vw, 58px);
      font-weight: 800;
      letter-spacing: -.03em;
      line-height: 1.0;
      color: var(--ink-strong);
      max-width: 15ch;
      margin: 0;
    }
    .pagehead h1 .pull {
      color: var(--accent);
      font-style: italic;
      font-family: var(--serif);
      font-weight: 700;
    }
    .pagehead .rq {
      max-width: 62ch;
      margin-top: 22px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.55;
    }
    .pagehead .rq b { color: var(--ink); font-weight: 700; }
    .hero-orbits { justify-self: end; max-width: 100%; opacity: .85; pointer-events: none; }
    .meta-strip {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      margin-top: 28px;
      padding-top: 22px;
      border-top: 1px solid var(--line);
    }
    .readout { font-size: 13px; color: var(--muted); }
    .readout b { color: var(--ink); font-weight: 700; }
    .topbar {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 1100;
      padding: 0;
      display: block;
      gap: 0;
      box-shadow: none;
      transition: box-shadow .2s ease;
    }
    .leaflet-pane, .leaflet-top, .leaflet-bottom { z-index: 400; }
    .leaflet-control { z-index: 500; }
    .nav-toggle {
      display: none;
      align-items: center;
      gap: 6px;
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 11px;
      cursor: pointer;
      margin-left: auto;
    }
    .nav-toggle svg { display: block; }
    .nav-toggle:hover { border-color: var(--accent); }
    .topbar.stuck { box-shadow: 0 10px 28px -18px rgba(17,24,31,.45); }
    .tb-row1 {
      padding: 12px 42px;
      display: flex;
      align-items: center;
      gap: 24px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 21px;
      letter-spacing: -.01em;
      white-space: nowrap;
    }
    .brand .e { font-weight: 500; color: var(--ink); }
    .brand .g { font-weight: 800; color: var(--accent); }
    .nav { display: flex; gap: 2px; flex-wrap: wrap; margin-right: auto; }
    .nav a {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--muted);
      text-decoration: none;
      padding: 5px 10px;
      border-radius: 999px;
    }
    .nav a:hover, .nav a.active { color: var(--accent); background: var(--soft); text-decoration: none; }
    .modeswitch {
      display: inline-flex;
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px;
    }
    .modeswitch button {
      font: inherit;
      font-size: 12.5px;
      font-weight: 700;
      border: none;
      background: none;
      color: var(--muted);
      padding: 6px 14px;
      border-radius: 999px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .modeswitch button.active {
      background: #fff;
      color: var(--accent);
      box-shadow: 0 1px 3px rgba(17,24,31,.12);
    }
    .tb-row2 { padding: 0 42px 18px; }
    .ctrl-surface {
      margin-top: 4px;
      border: 1px solid var(--line);
      border-radius: 13px;
      background: var(--paper);
      box-shadow: inset 0 1px 0 #fff, 0 1px 2px rgba(17,24,31,.03);
      overflow: hidden;
    }
    .cs-head {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 11px 18px;
      border-bottom: 1px solid var(--line-soft);
    }
    .cs-head .t {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: var(--accent);
    }
    .cs-head .reset {
      margin-left: auto;
      font: inherit;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--muted);
      background: none;
      border: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 9px;
      border-radius: 7px;
    }
    .cs-head .reset:hover { color: var(--accent); background: rgba(47,111,115,.08); }
    .cs-grid { display: grid; grid-template-columns: 1.7fr 1.2fr; }
    .ctrl-group {
      margin: 0;
      border: 0;
      border-right: 1px solid var(--line-soft);
      padding: 16px 20px 18px;
      min-width: 0;
    }
    .ctrl-group:last-child { border-right: none; }
    .cg-legend {
      display: flex;
      align-items: center;
      gap: 7px;
      font-family: var(--serif);
      font-style: italic;
      font-size: 15px;
      font-weight: 700;
      color: var(--ink-strong);
      margin-bottom: 13px;
    }
    .cg-legend .gl { width: 18px; height: 18px; flex: none; }
    .cg-fields { display: grid; gap: 13px; }
    .cg-fields.two { grid-template-columns: 1fr 1fr; }
    label.field, .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }
    .field > span:first-child {
      font-size: 11.5px;
      font-weight: 700;
      letter-spacing: .03em;
      color: var(--muted);
    }
    .field input, .field select {
      font: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      width: 100%;
      min-width: 0;
      transition: border-color .15s ease, box-shadow .15s ease;
    }
    .field input::placeholder { color: var(--faint); }
    .field input:focus, .field select:focus {
      outline: none;
      border-color: var(--accent-bright);
      box-shadow: 0 0 0 3px rgba(47,111,115,.14);
    }
    .field .ip { position: relative; display: block; }
    .field .ip .ic {
      position: absolute;
      left: 11px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--faint);
      pointer-events: none;
    }
    .field .ip input { padding-left: 33px; }
    .field .ip:focus-within .ic { color: var(--accent); }
    .selwrap { position: relative; }
    .selwrap select {
      appearance: none;
      -webkit-appearance: none;
      padding-right: 32px;
      cursor: pointer;
    }
    .selwrap::after {
      content: "";
      position: absolute;
      right: 13px;
      top: 50%;
      width: 8px;
      height: 8px;
      border-right: 1.6px solid var(--muted);
      border-bottom: 1.6px solid var(--muted);
      transform: translateY(-65%) rotate(45deg);
      pointer-events: none;
    }
    .field .hint {
      font-size: 11px;
      color: var(--faint);
      line-height: 1.4;
      margin-top: -1px;
    }
    body.mode-free .explore-only { display: none; }
    .filter-redesign { display: flex; flex-direction: column; gap: 16px; }
    .filter-primary {
      display: grid; grid-template-columns: minmax(0,220px) 1fr; gap: 14px 18px;
      align-items: start;
      padding: 14px 16px; border-radius: 12px;
      background: var(--paper);
      border: 1.5px solid rgba(47,111,115,0.28);
    }
    .filter-primary .fp-label { display: flex; flex-direction: column; gap: 3px; }
    .filter-primary .fp-title {
      font-weight: 700; font-size: 16px; color: var(--ink);
      display: flex; align-items: center; gap: 8px;
    }
    .filter-primary .fp-emoji { font-size: 20px; line-height: 1; }
    .filter-primary .fp-hint { font-size: 12px; color: var(--muted); }
    .filter-primary .fp-controls {
      display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center;
    }
    .pill-toggle {
      border: 1.5px solid var(--line); background: #fff; color: var(--ink);
      padding: 8px 14px; border-radius: 999px; font-size: 13px; font-weight: 600;
      cursor: pointer; transition: all .15s ease; white-space: nowrap;
    }
    .coverage-badge {
      display: inline-block; margin: 0 6px 6px 0; padding: 2px 8px;
      background: rgba(47,111,115,0.08); border: 1px solid rgba(47,111,115,0.2);
      border-radius: 4px; font-size: 12px; font-weight: 600; color: var(--accent, #2f6f73);
      white-space: nowrap;
    }
    .coverage-badge:empty { display: none; }
    .pill-toggle:hover { border-color: var(--accent, #2f6f73); }
    .pill-toggle.on {
      background: var(--accent, #2f6f73); color: #fff; border-color: var(--accent, #2f6f73);
    }
    .seg-btn {
      border: 1.5px solid var(--line); background: #fff; color: var(--ink);
      padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; transition: all .15s ease;
    }
    .seg-btn:hover { border-color: var(--accent); }
    .seg-btn.on { background: var(--accent); color: #fff; border-color: var(--accent); }
    .dest-filter-input {
      flex: 1; min-width: 180px; max-width: 320px;
      padding: 8px 12px; border-radius: 8px;
      border: 1.5px solid var(--line); font-size: 13px;
      background: #fff; color: var(--ink);
    }
    .dest-filter-input:focus { outline: none; border-color: var(--accent); }
    .filter-optional { padding: 4px 4px 0; }
    .filter-optional .fo-head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; flex-wrap: wrap; }
    .filter-optional .fo-title { font-weight: 600; color: var(--ink); font-size: 14px; display: flex; align-items: center; gap: 8px; }
    .filter-optional .fo-head .reset { margin-left: auto; }
    .filter-optional .fo-explain { font-size: 12px; color: var(--muted); margin: 0 0 12px; line-height: 1.5; }
    .filter-optional .fo-explain b { color: var(--ink); }
    .filter-optional .fo-grid {
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px;
    }
    .filter-optional .field span:first-child { display: flex; align-items: center; gap: 6px; }
    @media (max-width: 720px) {
      .filter-primary { grid-template-columns: 1fr; gap: 10px; }
      .filter-primary .fp-controls { grid-template-columns: 1fr; }
      .pill-toggle { width: 100%; }
      .filter-optional .fo-grid { grid-template-columns: 1fr; }
    }
    main {
      padding: 36px 42px 56px;
      display: flex;
      flex-direction: column;
      gap: 30px;
      max-width: 1320px;
      margin: 0 auto;
    }
    main > section[id] { scroll-margin-top: 90px; }
    main > section, .grid > section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 30px 30px 32px;
      box-shadow: var(--shadow);
      overflow-x: auto;
    }
    main > section.intro { border-left: 3px solid var(--accent); }
    main > section > h2, .grid > section > h2, .duo > section > h2 {
      font-size: 27px;
      font-weight: 800;
      letter-spacing: -.02em;
      color: var(--ink-strong);
      line-height: 1.12;
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }
    .h2-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      line-height: 1.1;
    }
    .sec-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .sec-head > h2 { margin-bottom: 0; }
    .sec-ctrl {
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 230px;
    }
    .sec-ctrl > span {
      font-size: 11.5px;
      font-weight: 700;
      letter-spacing: .03em;
      color: var(--muted);
    }
    .filter-chip {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      font-weight: 700;
      color: var(--accent-deep);
      background: rgba(47, 111, 115, .09);
      border: 1px solid #c9d7d5;
      border-radius: 999px;
      padding: 4px 11px 4px 9px;
      line-height: 1;
      white-space: nowrap;
    }
    .filter-chip .fdot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent-2);
      flex: none;
    }
    .filter-chip .lab {
      color: var(--muted);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .11em;
      font-size: 9.5px;
    }
    .filter-chip .fc-country { letter-spacing: -.01em; }
    .duo {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 30px;
      align-items: start;
    }
    .duo > section { margin: 0; }
    .act {
      margin: 22px 4px 0;
      padding-bottom: 14px;
      border-bottom: 2px solid var(--ink-strong);
      display: flex;
      align-items: flex-end;
      gap: 18px;
    }
    .act:first-of-type { margin-top: 6px; }
    .act .gd-glyph { flex: none; margin-bottom: 2px; }
    .act .gd-main { flex: 1; }
    .act .gd-role {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .16em;
      text-transform: uppercase;
      color: var(--accent);
    }
    .act h3 {
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -.02em;
      color: var(--ink-strong);
      margin-top: 6px;
      line-height: 1.1;
    }
    .act .gd-sym {
      font-family: var(--serif);
      font-style: italic;
      font-size: 30px;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: -2px;
      white-space: nowrap;
    }
    .act .gd-sym sub { font-size: 18px; }
    .act.ctrl { border-bottom-color: #c9d7d5; }
    .act.ctrl .gd-role { color: var(--muted); }
    .act.ctrl .gd-sym {
      font-family: var(--mono);
      font-style: normal;
      font-size: 15px;
      font-weight: 700;
      color: var(--muted);
    }
    .sec-kicker.dep {
      background: var(--ink-strong);
      color: var(--paper);
    }
    .sec-kicker .lab {
      font-family: var(--sans);
      font-style: normal;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .1em;
      text-transform: uppercase;
      opacity: .82;
    }
    .collapsible {
      padding: 0;
      overflow: hidden;
    }
    .collapsible details { padding: 0; }
    .collapsible summary {
      list-style: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 24px 30px;
      border-radius: 14px;
    }
    .collapsible summary::-webkit-details-marker { display: none; }
    .collapsible summary h2 {
      font-size: 27px;
      font-weight: 800;
      letter-spacing: -.02em;
      color: var(--ink-strong);
      line-height: 1.12;
      margin: 0;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    .collapsible summary h2 .sec-kicker { align-self: flex-start; }
    .collapse-toggle {
      flex: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid #c9d7d5;
      border-radius: 999px;
      background: var(--soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      padding: 6px 12px;
      white-space: nowrap;
    }
    .collapse-toggle::before { content: "Show"; }
    .collapse-toggle::after {
      content: "";
      width: 7px;
      height: 7px;
      border-right: 1.6px solid currentColor;
      border-bottom: 1.6px solid currentColor;
      transform: translateY(-2px) rotate(45deg);
    }
    .collapsible details[open] .collapse-toggle::before { content: "Hide"; }
    .collapsible details[open] .collapse-toggle::after { transform: translateY(2px) rotate(225deg); }
    .collapse-body {
      padding: 0 30px 32px;
      border-top: 1px solid var(--line-soft);
    }
    #sec-flow-filters .collapse-body { border-top: none; padding-top: 4px; }
    #sec-flow-filters > details > summary { padding-bottom: 12px; }
    .collapse-body > .note:first-child { margin-top: 18px; }
    .grid, .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 24px; }
    .cards, .card-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .card {
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 16px 18px;
    }
    .card .label { font-size: 13px; font-weight: 600; color: var(--muted); line-height: 1.3; }
    .card .value {
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -.02em;
      margin-top: 8px;
      color: var(--ink-strong);
    }
    .summary-stack { display: flex; flex-direction: column; gap: 24px; margin-top: 22px; }
    .summary-group {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 18px 20px 22px;
      border: 1px solid var(--line-soft);
      border-left: 3px solid var(--accent);
      border-radius: var(--radius);
      background: var(--paper);
      min-width: 0;
    }
    .summary-group .grp-head {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .summary-group .grp-head .kicker-num {
      font-family: var(--mono);
      font-size: 10.5px;
      letter-spacing: .04em;
      color: var(--paper);
      background: var(--accent);
      border-radius: 5px;
      padding: 3px 7px;
      font-weight: 700;
    }
    .summary-group .grp-head .grp-emoji { font-size: 17px; line-height: 1; }
    .summary-group .grp-head .grp-name {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .16em;
      text-transform: uppercase;
      color: var(--accent);
    }
    .summary-group .grp-head .grp-hint {
      font-family: var(--serif);
      font-style: italic;
      color: var(--muted);
      font-weight: 500;
      font-size: 14px;
      letter-spacing: 0;
      text-transform: none;
      flex-basis: 100%;
      line-height: 1.4;
      margin-top: -2px;
    }
    .summary-group .grp-foot {
      font-size: 11.5px;
      color: var(--faint);
      font-style: italic;
      line-height: 1.4;
      margin-top: 4px;
    }
    .summary-group .cards {
      margin-top: 0;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
    }
    .summary-group .cards .card {
      display: flex;
      flex-direction: column;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: 0 1px 2px rgba(17,24,31,.03);
      transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease;
      padding: 16px 18px 18px;
      cursor: pointer;
      min-width: 0;
      overflow: hidden;
    }
    .summary-group .cards .card:hover {
      box-shadow: 0 6px 18px -10px rgba(17,24,31,.28);
      transform: translateY(-1px);
    }
    .summary-group .cards .card.open { border-color: var(--accent); box-shadow: 0 6px 18px -10px rgba(17,24,31,.28); }
    .summary-group .cards .card .card-sub { margin-top: auto; padding-top: 12px; }
    .summary-group .cards .card .value {
      font-size: clamp(22px, 4.6vw, 30px);
      word-break: break-word;
    }
    .card-chart {
      flex-basis: 100%;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed var(--line-soft);
      display: none;
    }
    .card.open .card-chart { display: block; }
    .card-chart svg { width: 100%; height: 44px; display: block; }
    .card-chart-axis {
      display: flex;
      justify-content: space-between;
      font-family: var(--mono);
      font-size: 10.5px;
      color: var(--faint);
      margin-top: 4px;
      letter-spacing: .02em;
    }
    .card-chart-axis .mean-tick { color: var(--muted); font-weight: 600; }
    .card-chart-hint { font-size: 11px; color: var(--faint); margin-top: 4px; font-style: italic; }
    .card .value .delta {
      font-family: var(--serif);
      font-style: italic;
      font-weight: 700;
      margin-right: 4px;
    }
    .card .value .delta.pos { color: var(--positive); }
    .card .value .delta.neg { color: var(--negative); }
    .rank-bar {
      flex-basis: 100%;
      height: 3px;
      background: var(--line-soft);
      border-radius: 999px;
      overflow: hidden;
      margin-top: 2px;
    }
    .rank-bar > span {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: var(--accent);
    }
    .rank-bar.warm > span { background: var(--accent-2); }
    .destination-list { display: grid; gap: 0; margin-top: 12px; }
    .destination-list li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-size: 13.5px;
      color: var(--ink);
      list-style: none;
      padding: 8px 0;
      border-bottom: 1px dashed var(--line-soft);
    }
    .destination-list li:last-child { border-bottom: none; }
    .destination-list .dl-rank {
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      color: var(--paper);
      background: var(--accent);
      width: 22px;
      height: 22px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: none;
    }
    .destination-list li:nth-child(2) .dl-rank { background: var(--accent-bright); }
    .destination-list li:nth-child(3) .dl-rank { background: var(--accent-deep); opacity: .75; }
    .destination-list .dl-name { flex: 1; font-weight: 600; display: flex; align-items: baseline; gap: 7px; min-width: 0; }
    .destination-list .dl-code { font-family: var(--mono); font-size: 11.5px; color: var(--accent-deep); font-weight: 700; }
    .destination-list .dl-pct { font-variant-numeric: tabular-nums; color: var(--muted); font-weight: 700; font-size: 12.5px; white-space: nowrap; }
    .destination-list .dl-pct .dl-flow { color: var(--faint); font-weight: 500; margin-left: 4px; }
    .card-sub {
      font-size: 11.5px;
      font-weight: 600;
      color: var(--muted);
      margin-top: 10px;
      letter-spacing: .02em;
      line-height: 1.4;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }
    .card-sub .rank-pill {
      display: inline-flex;
      align-items: center;
      padding: 3px 9px;
      border-radius: 999px;
      font-family: var(--mono);
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: .03em;
      text-transform: uppercase;
    }
    .card-sub .mean-line { color: var(--muted); }
    .card-sub .card-note {
      flex-basis: 100%;
      color: var(--faint);
      font-weight: 500;
      font-style: italic;
      font-size: 11px;
      line-height: 1.4;
    }
    .card .label { display: inline-flex; align-items: center; gap: 7px; }
    .card-emoji { font-size: 16px; line-height: 1; }
    .note, .source-list, .sources { font-size: 13px; color: var(--muted); line-height: 1.5; }
    .equation {
      font-family: var(--serif);
      font-size: 18px;
      line-height: 2.05;
      color: var(--ink-strong);
      background: var(--soft);
      border: 1px solid var(--line);
      border-left: 3px solid var(--accent);
      border-radius: var(--radius);
      padding: 22px 26px;
      overflow-x: auto;
      margin: 16px 0;
    }
    .equation .gk { font-style: italic; }
    .equation .fx { color: var(--accent-deep); font-weight: 600; }
    .beta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
      gap: 14px;
      margin: 18px 0 4px;
    }
    .beta-grid .card { padding: 16px 18px 18px; min-height: 168px; }
    .beta-grid .card .label {
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .beta-grid .card .value {
      font-size: 18px;
      font-weight: 700;
      line-height: 1.3;
      color: var(--ink-strong);
      letter-spacing: -.01em;
    }
    .beta-grid .card .value .v-num {
      font-family: var(--mono);
      font-size: 22px;
      font-weight: 800;
      letter-spacing: 0;
    }
    .beta-grid .card .value .v-num.sig { color: var(--accent); }
    .beta-grid .card .value .v-num.nsg { color: var(--ink); }
    .beta-grid .card .value .v-num.pln { color: var(--muted); }
    .beta-grid .card .sub {
      margin-top: 10px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
    }
    .beta-grid .card .sub code { font-size: 11.5px; color: var(--accent-deep); }
    .beta-grid .card .effect-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      align-items: baseline;
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted);
      margin-top: 6px;
    }
    .beta-grid .card .effect-row b { color: var(--ink); font-weight: 700; }
    .beta-grid .card .effect-row .sig-tag {
      font-family: var(--mono);
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: .04em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .beta-grid .card .effect-row .sig-tag.sig { background: rgba(47,111,115,.14); color: var(--accent-deep); }
    .beta-grid .card .effect-row .sig-tag.nsg { background: var(--soft-2); color: var(--muted); }
    .beta-grid .card .effect-row .sig-tag.pln { background: rgba(180,78,90,.10); color: var(--accent-2-deep); }
    .equation .eq-term {
      text-decoration: none;
      color: inherit;
      border-bottom: 1px dotted var(--accent);
      padding: 0 2px;
      border-radius: 3px;
      transition: background .15s ease, color .15s ease;
      white-space: nowrap;
    }
    .equation .eq-term:hover {
      background: rgba(47, 111, 115, .10);
      color: var(--accent-deep);
    }
    .equation .eq-term.ctrl { border-bottom-color: #c9d7d5; white-space: normal; }
    .equation .eq-term.ctrl:hover { background: rgba(95, 107, 118, .10); color: var(--ink); }
    .equation .eq-term.coral { border-bottom-color: var(--accent-2); }
    .equation .eq-term.coral:hover { background: rgba(180, 78, 90, .10); color: var(--accent-2-deep); }
    .nav-main {
      display: flex; gap: 4px; padding: 6px 42px;
      background: rgba(238, 243, 241, .35);
      border-top: 1px solid var(--line-soft);
    }
    .nav-main-link {
      font-size: 13px; font-weight: 700; color: var(--muted);
      text-decoration: none; padding: 6px 14px; border-radius: 8px;
      border: 1px solid transparent; transition: all .15s ease;
    }
    .nav-main-link:hover { color: var(--accent-deep); background: var(--soft); }
    .nav-main-link.active {
      color: var(--accent-deep); background: #fff; border-color: #c9d7d5;
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }
    .nav-subs {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      padding: 4px 42px 10px;
      border-bottom: 1px solid var(--line-soft);
      background: rgba(238, 243, 241, .35);
      min-height: 28px;
    }
    .nav-subs:empty { display: none; }
    .nav-subs .sub-link {
      font-size: 11.5px;
      font-weight: 700;
      color: var(--muted);
      text-decoration: none;
      padding: 3px 10px;
      border-radius: 999px;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .nav-subs .sub-link .bsym {
      font-family: var(--serif);
      font-style: italic;
      font-weight: 700;
      color: var(--accent);
      font-size: 13px;
    }
    .nav-subs .sub-link.ctrl .bsym { color: var(--muted); font-family: var(--mono); font-style: normal; font-size: 10.5px; }
    .nav-subs .sub-link.coral .bsym { color: var(--accent-2); font-family: var(--mono); font-style: normal; font-size: 10.5px; }
    .nav-subs .sub-link.coral:hover, .nav-subs .sub-link.coral.active { color: var(--accent-2-deep); background: rgba(180,78,90,.10); border-color: rgba(180,78,90,.35); }
    .nav-subs .sub-link:hover, .nav-subs .sub-link.active {
      color: var(--accent-deep);
      background: var(--soft);
      border-color: #c9d7d5;
    }
    .nav-subs .sep { color: var(--faint); font-family: var(--mono); font-size: 11px; align-self: center; margin: 0 2px; }
    .info-btn {
      display: inline-flex; align-items: center; justify-content: center;
      width: 22px; height: 22px; border-radius: 50%;
      border: 1.4px solid var(--accent); background: #fff; color: var(--accent);
      font-size: 13px; line-height: 1; cursor: pointer; padding: 0;
      margin-left: 8px; vertical-align: middle; font-weight: 700;
      transition: background .15s ease, color .15s ease;
    }
    .info-btn:hover { background: var(--accent); color: #fff; }
    .info-popover {
      margin: 8px 0 14px; padding: 12px 14px;
      background: var(--soft); border-left: 3px solid var(--accent);
      border-radius: 6px; font-size: 13px; line-height: 1.5; color: var(--ink);
    }
    .info-popover code { font-family: var(--mono); font-size: 12px; color: var(--accent-deep); }
    .sec-kicker {
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .04em;
      color: var(--paper);
      background: var(--ink-strong);
      border-radius: 6px;
      padding: 4px 10px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      margin: 0 8px 8px 0;
    }
    /* Badge above title: stack the kicker on its own line over h2 text */
    section > h2, .collapsible summary h2 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0; }
    section > h2 > .sec-kicker:first-child,
    .collapsible summary h2 > .sec-kicker:first-child { flex: 0 0 100%; margin-bottom: 6px; }
    .sec-kicker.beta {
      background: var(--accent);
      color: var(--paper);
      font-family: var(--serif);
      font-style: italic;
      font-size: 14px;
      letter-spacing: 0;
      padding: 3px 11px;
    }
    .sec-kicker.ctrl { background: var(--soft); color: var(--muted); border: 1px solid #c9d7d5; }
    .sec-kicker.plain {
      background: none;
      color: var(--accent);
      border: 1px solid #c9d7d5;
      font-family: var(--sans);
      font-size: 11px;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .table-wrap, #destinationTable, #weightedTable, #redditTable, #orgFlowTable, #coeffTable, #resultsTable {
      overflow-x: auto;
      margin-top: 14px;
    }
    .data-table {
      border-collapse: collapse;
      width: 100%;
      min-width: 820px;
      font-size: 13.5px;
    }
    .data-table thead th, .data-table th {
      text-align: left;
      padding: 11px 14px;
      background: var(--soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 12px;
      letter-spacing: .02em;
      cursor: pointer;
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
      user-select: none;
    }
    .data-table tbody td, .data-table td { padding: 10px 14px; border-bottom: 1px solid var(--line-soft); }
    .data-table tbody tr:hover { background: var(--soft); }
    .data-table th:nth-child(n+3), .data-table td:nth-child(n+3) { text-align: right; }
    .data-table td[style*="text-align:left"], .data-table th[style*="text-align:left"] { text-align: left; }
    #map {
      height: 540px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--soft);
      margin-top: 14px;
    }
    .legend-dot {
      display: inline-block;
      border-radius: 50%;
      background: var(--accent);
      border: 2px solid #fff;
      box-shadow: 0 2px 8px -2px rgba(17,24,31,.4);
      vertical-align: middle;
      margin-right: 6px;
    }
    .chart-ramp { display: flex; border-radius: 6px; overflow: hidden; border: 1px solid var(--line); margin-top: 12px; max-width: 420px; }
    .chart-ramp div { flex: 1; height: 26px; }
    .ramp-axis { display: flex; justify-content: space-between; max-width: 420px; font-family: var(--mono); font-size: 11px; color: var(--faint); margin-top: 4px; }
    footer {
      background: var(--soft);
      border-top: 1px solid var(--line);
      padding: 34px 42px;
      color: var(--muted);
      font-size: 13px;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    footer b { color: var(--ink); font-weight: 700; }
    @media (max-width: 700px) {
      .pagehead, .tb-row1, .tb-row2, main, footer { padding-left: 18px; padding-right: 18px; }
      .hero-inner { grid-template-columns: 1fr; gap: 0; }
      .hero-orbits { display: none; }
      .tb-row1 { flex-wrap: wrap; gap: 12px; }
      .nav-toggle { display: inline-flex; }
      .tb-row1 .nav {
        order: 3;
        width: 100%;
        flex-direction: column;
        gap: 4px;
        padding: 6px 0 4px;
        border-top: 1px solid var(--line-soft);
        display: none;
      }
      .tb-row1 .nav.open { display: flex; }
      .tb-row1 .nav a { padding: 9px 12px; font-size: 14px; }
      .cg-fields.two { grid-template-columns: 1fr; }
      .tb-row2 { padding-top: 12px; padding-bottom: 16px; }
      .cs-grid { grid-template-columns: 1fr; }
      .ctrl-group { border-right: none; border-bottom: 1px solid var(--line-soft); }
      .ctrl-group:last-child { border-bottom: none; }
      .grid, .grid2, .duo { grid-template-columns: 1fr; }
      .summary-group { padding: 16px 14px 18px; }
      .summary-group .cards { grid-template-columns: 1fr; gap: 12px; }
      .summary-group .cards .card { padding: 14px 14px 16px; }
      .summary-group .cards .card .value { font-size: 24px; }
      .summary-group .grp-head .grp-hint { font-size: 13.5px; }
      .destination-list li { font-size: 13px; }
      .destination-list .dl-pct .dl-flow { display: none; }
      .nav-subs { padding: 4px 18px 10px; gap: 4px; }
      .nav-subs .sub-link { font-size: 11px; padding: 3px 8px; }
      .act { flex-wrap: wrap; gap: 10px; }
      .act .gd-sym { font-size: 22px; }
      select, input { min-width: 100%; }
      .toolbar-main { grid-template-columns: 1fr; }
      .topbar .brand { padding-right: 0; }
      .topbar nav { margin-left: 0; }
      .pagehead h1 { font-size: 32px; }
      main { padding-top: 24px; gap: 22px; }
      main > section, .grid > section { padding: 22px; }
      main > section.collapsible { padding: 0; }
      .collapsible summary { padding: 20px 22px; align-items: flex-start; }
      .collapsible summary h2 { font-size: 23px; }
      .collapse-body { padding: 0 22px 24px; }
    }

    /* Responsive navigation and analytical presentation share measured offsets. */
    :root{--nav-offset:150px}
    main>section[id],section[id],.act[id]{scroll-margin-top:var(--nav-offset)}
    .topbar .tb-row1{display:grid;grid-template-columns:auto minmax(160px,240px) 1fr;gap:24px;align-items:center}
    .quick-country{display:flex;align-items:center;gap:10px;font-size:13px!important;white-space:nowrap}
    .quick-country input{width:100%;min-width:0!important;font-size:14px;padding:8px 10px}
    .topbar .nav-main{justify-self:end}
    .topbar .nav-subs{flex-wrap:nowrap;overflow-x:auto;white-space:nowrap}
    .nav-subs a{flex-shrink:0;min-height:36px;box-sizing:border-box;align-items:center}
    .map-empty{padding:24px;background:var(--soft);border-radius:10px;line-height:1.6}
    [hidden]{display:none!important}
    #sec-explanatory>.cards{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}
    #sec-explanatory>.cards>.card{grid-column:span 3;min-width:0}
    #sec-explanatory>.cards>.card:nth-child(n+5){grid-column:span 4}
    #coeffTable,#resultsTable,#redditTable{overflow-x:auto}
    .effect-row{line-height:1.6;overflow-wrap:anywhere}
    .coverage-badge{display:inline-block;white-space:normal;max-width:100%;line-height:1.5;box-sizing:border-box;overflow-wrap:anywhere}
    @media(max-width:1000px){
      .topbar .tb-row1{gap:12px;grid-template-columns:auto minmax(140px,200px) 1fr}
      #sec-explanatory>.cards{grid-template-columns:repeat(2,minmax(0,1fr))}
      #sec-explanatory>.cards>.card,#sec-explanatory>.cards>.card:nth-child(n+5){grid-column:span 1}
      #sec-explanatory>.cards>.card:last-child{grid-column:1/-1}
    }
    @media(max-width:640px){
      .topbar .tb-row1{grid-template-columns:1fr auto;padding:10px 18px;gap:10px}
      .topbar .brand{grid-column:1;grid-row:1;font-size:20px}
      .topbar .nav-toggle{display:inline-flex;grid-column:2;grid-row:1;min-height:40px}
      .topbar .quick-country{grid-column:1/-1;grid-row:2;display:grid;grid-template-columns:60px minmax(0,1fr);max-width:none}
      .topbar .nav-main{display:none;grid-column:1/-1;justify-self:stretch;justify-content:space-between;padding:0}
      .topbar .nav-main.open{display:flex}
      .nav-subs{padding:4px 18px 8px;min-height:0}
      .nav-subs .sub-link{font-size:12px;min-height:36px}
      #sec-explanatory>.cards{grid-template-columns:1fr}
      .equation{font-size:17px;line-height:1.8;overflow-wrap:anywhere}
      #coeffTable table,#resultsTable table{min-width:700px}
      #coeffTable th:nth-child(2),#coeffTable td:nth-child(2),#resultsTable th:first-child,#resultsTable td:first-child{position:sticky;left:0;background:var(--panel);z-index:2;white-space:normal;min-width:145px;max-width:175px}
      #resultsTable .spec-detail td{position:static;max-width:none}
      .chart .axis-text{font-size:13px}
      .beta-grid{gap:14px}
      h2 .h2-row{display:block}
      .filter-chip{margin-top:8px}
    }


    #resultsTable table{table-layout:fixed;width:100%}
    #resultsTable th:first-child{width:30%}
    #resultsTable th:nth-child(2){width:26%}
    #resultsTable th:nth-child(3),#resultsTable th:nth-child(4),#resultsTable th:nth-child(5){width:8%}
    #resultsTable th:nth-child(6){width:20%}
    #resultsTable td:first-child,#resultsTable td:nth-child(2),#resultsTable td:nth-child(6){white-space:normal;overflow-wrap:anywhere}
    @media(min-width:641px) and (max-width:1000px){
      .topbar .tb-row1{grid-template-columns:auto minmax(180px,240px) auto}
      .topbar .nav-toggle{display:inline-flex;grid-column:3;grid-row:1;justify-self:end;min-height:40px}
      .topbar .nav-main{display:none;grid-column:1/-1;justify-self:stretch;justify-content:space-between;flex-wrap:nowrap}
      .topbar .nav-main.open{display:flex}
    }


    /* Primary and contextual menus share a column and a left edge. */
    .topbar{padding:12px 42px;gap:0}
    .topbar .tb-row1{grid-template-columns:auto minmax(0,1fr) 210px;gap:28px;padding:0}
    .topbar .brand{grid-column:1;grid-row:1;padding:0;font-size:22px}
    .nav-stack{grid-column:2;grid-row:1;display:flex;flex-direction:column;align-items:stretch;gap:4px;min-width:0}
    .topbar .nav-main{display:flex;justify-self:stretch;justify-content:flex-start;flex-wrap:nowrap;gap:8px;margin:0;padding:0;background:none;border:0}
    .topbar .nav-main-link{padding:8px;min-height:36px;box-sizing:border-box;white-space:nowrap;border-radius:0;border-width:0 0 2px;border-style:solid;border-color:transparent;font-size:14px;box-shadow:none}
    .topbar .nav-main-link.active{background:none;border-color:var(--accent);box-shadow:none;color:var(--accent-deep)}
    .topbar .nav-main-link:hover{background:var(--soft);text-decoration:none}
    .topbar .nav-subs{display:flex;flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;gap:8px;margin:0;padding:0;border:0;background:none;min-height:36px;min-width:0}
    .topbar .nav-subs .sub-link{flex-shrink:0;min-height:36px;padding:7px 8px;border:0;border-radius:4px;font-size:12px;box-sizing:border-box}
    .topbar .nav-subs .sub-link.active{background:var(--soft);color:var(--accent-deep)}
    .topbar .quick-country{grid-column:3;grid-row:1;display:grid;grid-template-columns:1fr;gap:4px;font-size:12px!important;max-width:none;line-height:1.3}
    .topbar .quick-country input{height:36px;box-sizing:border-box}
    .topbar .nav-toggle{display:none}
    @media(max-width:1199px){
      .topbar{padding:12px 24px}
      .topbar .tb-row1{grid-template-columns:1fr auto;gap:10px}
      .topbar .brand{grid-column:1;grid-row:1;font-size:21px}
      .topbar .nav-toggle{display:inline-flex;grid-column:2;grid-row:1;justify-self:end;min-height:40px}
      .topbar .quick-country{grid-column:1/-1;grid-row:2;grid-template-columns:115px minmax(0,1fr);align-items:center;gap:8px}
      .topbar .quick-country input{height:40px}
      .nav-stack{grid-column:1/-1;grid-row:3;width:100%;gap:4px}
      .topbar .nav-main{display:none}
      .topbar .nav-main.open{display:flex;justify-content:flex-start;flex-wrap:nowrap;padding:0}
      .topbar .nav-main-link{min-height:40px;display:flex;align-items:center}
    }
    @media(max-width:640px){
      .topbar{padding:10px 18px}
      .topbar .quick-country{grid-template-columns:108px minmax(0,1fr)}
      .topbar .nav-main-link{font-size:14px}
    }


    /* Research observatory: shared frame, flat surfaces and tabular evidence.
       1320px frame = 2 x 42px gutters + 1236px usable canvas at desktop. */
    :root{--paper:#f3f5f4;--line:#dce2df;--line-soft:#e8ecea;--soft:#eef2f0;--faint:#63716d;--radius:10px;--shadow:none}
    body{line-height:1.6}
    p{color:var(--ink)}
    a{color:var(--accent-deep);text-underline-offset:3px}
    :where(a,button,input,select,summary):focus-visible{outline:2px solid var(--accent);outline-offset:4px}
    .topbar,.topbar.stuck{background:var(--panel);box-shadow:none}
    .topbar .tb-row1{max-width:1236px;margin:auto;grid-template-columns:auto minmax(0,1fr) 210px;gap:36px}
    .topbar .brand{font-size:21px;letter-spacing:-.04em;gap:9px}
    .brand .g{color:var(--ink-strong)}
    .nav-stack{display:contents}
    .topbar .tb-row1{row-gap:10px}
    .topbar .nav-main{grid-column:2;grid-row:1}
    .topbar .nav-subs{grid-column:2/-1;grid-row:2}
    .topbar .nav-main{gap:20px}
    .topbar .nav-main-link{font-size:14px;font-weight:600;color:var(--muted);min-height:42px;padding:9px 14px;transition:color .15s,background .15s}
    .topbar .nav-main-link.active{color:var(--ink-strong);border-color:var(--ink-strong)}
    .topbar .nav-subs{gap:12px;min-height:40px;padding-bottom:2px}
    .topbar .nav-subs .sub-link{font-size:13px;font-weight:500;min-height:40px;color:var(--muted);border-radius:999px;padding:8px 14px}
    .topbar .nav-subs .sub-link.active{background:var(--soft);color:var(--ink-strong);font-weight:600}
    .topbar .quick-country{font-weight:500;color:var(--muted)}
    .topbar .quick-country input{background:var(--paper);border-color:transparent;border-radius:8px;height:38px;font-size:14px}
    .topbar .nav-toggle{color:var(--ink);background:var(--paper);border:0;border-radius:8px}
    .pagehead{padding:48px 42px 44px;background:var(--panel);border-bottom:1px solid var(--line)}
    .hero-inner{max-width:1236px;grid-template-columns:minmax(0,1.3fr) minmax(300px,.8fr);gap:70px;align-items:start}
    .pagehead h1{font-size:clamp(32px,3.4vw,48px);font-weight:600;line-height:1.08;letter-spacing:-.045em;max-width:none}
    .pagehead .rq{font-size:15px;line-height:1.65;max-width:66ch;margin-top:22px;color:var(--ink)}
    .meta-strip{gap:8px 16px;margin-top:22px;padding-top:0;border:0}
    .readout{font-size:12px}
    .scope-pill{padding:0;background:none;border:0;font-size:12px;font-weight:400;color:var(--muted)}
    .mobility-brief{padding:24px 26px;background:var(--paper);border-radius:14px;min-width:0}
    .brief-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:14px;font-weight:600}
    .brief-heading a{font-size:12px;font-weight:500;text-decoration:none;white-space:nowrap}
    .brief-heading a:hover{text-decoration:underline}
    .brief-total{font-size:40px;line-height:1.15;letter-spacing:-.04em;font-weight:500;margin-top:20px;font-variant-numeric:tabular-nums}
    .brief-caption{font-size:12px;color:var(--muted);margin-top:4px}
    .brief-destinations{margin-top:22px;display:grid;gap:13px}
    .brief-destination>div:first-child{display:flex;justify-content:space-between;gap:12px;font-size:13px;margin-bottom:5px}
    .brief-destination b{font-weight:500;font-variant-numeric:tabular-nums}
    .brief-track{height:4px;background:#dce4e0;border-radius:2px;overflow:hidden}
    .brief-track span{display:block;height:100%;background:var(--accent)}
    .brief-foot{font-size:11px;color:var(--muted);margin-top:16px}
    main{gap:24px;padding-top:32px;padding-bottom:48px}
    main>section,.grid>section,.duo>section{border:1px solid var(--line);border-radius:14px;box-shadow:none;padding:28px 30px;background:var(--panel);min-width:0}
    main>section.intro{border-left:1px solid var(--line)}
    main>section>h2,.grid>section>h2,.duo>section>h2,.collapsible summary h2{font-size:24px;font-weight:600;line-height:1.25;letter-spacing:-.025em;gap:10px}
    h3{font-size:16px;font-weight:600;line-height:1.45}
    section>p+p{margin-top:12px}
    .note,.source-list,.sources{font-size:13px;line-height:1.65}
    .sec-kicker,.sec-kicker.beta,.sec-kicker.dep,.sec-kicker.ctrl{font-family:var(--sans);font-size:12px;font-weight:500;font-style:normal;letter-spacing:0;text-transform:none;background:var(--soft);color:var(--muted);border:0;border-radius:3px;padding:3px 7px;flex:none!important}
    .sec-kicker .lab{font-size:11px;letter-spacing:0;text-transform:none}
    .equation{background:var(--paper);border:0;border-radius:8px;font-size:18px;line-height:1.9;padding:20px 24px;margin:20px 0}
    .card{background:var(--panel);border:1px solid var(--line-soft);border-radius:8px;padding:18px;box-shadow:none}
    .card .value{font-size:28px;font-weight:500;letter-spacing:-.025em}
    .card .label,.beta-grid .card .label{font-size:13px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--muted);line-height:1.45}
    #sec-explanatory>.cards{gap:12px;margin-top:22px}
    #sec-explanatory .card{background:var(--paper);border:0;padding:20px}
    #sec-explanatory .card .value{font-weight:600;line-height:1.35;margin-top:10px}
    #sec-explanatory .card .note{font-size:12px;line-height:1.65}
    .beta-grid .card{min-height:0;padding:20px;background:var(--paper);border:0}
    .beta-grid .card .value{font-weight:500}
    .beta-grid .card .value .v-num{font-family:var(--sans);font-size:26px;font-weight:500}
    .beta-grid .card .effect-row,.beta-grid .card .effect-row .sig-tag{font-family:var(--sans);font-size:12px;letter-spacing:0;text-transform:none}
    .act{margin:24px 0 0;padding:0 0 12px;border-bottom:1px solid var(--line);gap:14px}
    .act .gd-role{font-size:13px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--muted)}
    .act h3{font-size:23px;font-weight:600;line-height:1.3;margin-top:4px}
    .act .gd-sym{font-size:24px;color:var(--muted)}
    .summary-stack{gap:28px}
    .summary-group{padding:0;border:0;border-radius:0;background:none;gap:16px}
    .summary-group .grp-head{gap:5px}
    .summary-group .grp-head .grp-name{font-size:16px;font-weight:600;letter-spacing:0;text-transform:none;color:var(--ink)}
    .summary-group .grp-head .grp-hint{font-family:var(--sans);font-size:13px;font-style:normal;margin:0;color:var(--muted)}
    .summary-group .cards{gap:12px}
    .summary-group .cards .card{background:var(--paper);border:1px solid transparent;box-shadow:none;border-radius:8px;padding:18px;transition:border-color .15s}
    .summary-group .cards .card:hover,.summary-group .cards .card.open{box-shadow:none;transform:none;border-color:var(--accent)}
    .summary-group .cards .card .value{font-weight:500}
    .summary-group .grp-foot,.card-sub .card-note{font-size:12px;font-style:normal;color:var(--muted)}
    .card-sub,.card-sub .rank-pill,.destination-list .dl-rank,.destination-list .dl-code,.ramp-axis,.card-chart-axis{font-family:var(--sans);letter-spacing:0;text-transform:none}
    .rank-bar>span{background:var(--accent)}
    .rank-bar.warm>span{background:var(--accent-2)}
    .destination-list{padding-left:0}
    .destination-list li{border-bottom-style:solid;padding:10px 0}
    .destination-list .dl-rank,.destination-list li:nth-child(2) .dl-rank,.destination-list li:nth-child(3) .dl-rank{background:none;color:var(--muted);font-size:12px;border-radius:0;opacity:1}
    .filter-primary{background:var(--paper);border:0;border-radius:8px;padding:18px}
    select,input,.dest-filter-input{border-radius:8px;border-color:var(--line);font-family:var(--sans)}
    button{font-family:var(--sans)}
    .pill-toggle,.seg-btn{border-radius:8px;font-weight:500;border-width:1px;min-height:38px}
    .pill-toggle.on,.seg-btn.on{background:var(--ink);border-color:var(--ink);color:var(--panel)}
    .coverage-badge{background:var(--paper);color:var(--muted);border:0;font-weight:500}
    .filter-chip{background:var(--paper);color:var(--ink);border:0;border-radius:8px;padding:7px 9px}
    .filter-chip .lab{font-size:11px;letter-spacing:0;text-transform:none}
    .collapsible{padding:0!important}
    .collapsible summary{padding:22px 30px;border-radius:14px}
    .collapse-toggle{background:var(--paper);color:var(--muted);border:0;border-radius:8px;font-weight:500;min-height:34px}
    .data-table thead th,.data-table th{background:var(--panel);color:var(--muted);font-size:12px;font-weight:500;letter-spacing:0;text-transform:none;padding:12px 14px}
    .data-table tbody td,.data-table td{padding:12px 14px;font-size:13px}
    .data-table tbody tr:hover{background:var(--paper)}
    .axis,.gridline{stroke:var(--line-soft)}
    #map{border-radius:8px;border-color:var(--line-soft)}
    .legend-dot{box-shadow:none}
    footer{padding:32px max(42px,calc((100vw - 1236px)/2));background:var(--panel);font-size:13px;gap:8px}
    @media(max-width:1199px){
      .topbar .tb-row1{grid-template-columns:1fr auto;gap:12px}
      .nav-stack{display:flex;gap:10px}
      .topbar .nav-main{gap:16px}
      .topbar .nav-subs{gap:10px}
      .hero-inner{gap:36px;grid-template-columns:minmax(0,1.1fr) minmax(280px,.9fr)}
    }
    @media(max-width:800px){
      .pagehead{padding:32px 24px}
      .hero-inner{grid-template-columns:1fr;gap:26px}
      .mobility-brief{padding:20px 22px}
      .pagehead .rq{max-width:none}
      .brief-total{font-size:34px;margin-top:14px}
      .brief-destinations{grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:18px}
      .brief-destination>div:first-child{flex-wrap:wrap;gap:4px}
      main{padding:24px;gap:20px}
      main>section,.grid>section,.duo>section{padding:24px}
      .grid,.grid2,.duo{grid-template-columns:1fr}
    }
    @media(max-width:640px){
      .topbar .nav-main-link,.topbar .nav-subs .sub-link{min-height:44px;display:flex;align-items:center}
      .topbar .quick-country input{height:44px}
      .topbar .nav-toggle{min-height:44px}
      .pagehead{padding:28px 18px}
      .pagehead h1{font-size:34px}
      .pagehead .rq{font-size:14px;margin-top:18px}
      .mobility-brief{padding:18px}
      .brief-destinations{gap:14px}
      .brief-heading{font-size:13px}
      .brief-total{font-size:32px}
      .brief-destination>div:first-child{font-size:12px}
      main{padding:20px 18px 36px}
      main>section,.grid>section,.duo>section{padding:22px 18px}
      main>section>h2,.grid>section>h2,.duo>section>h2,.collapsible summary h2{font-size:22px}
      .act h3{font-size:20px}
      .act .gd-sym{font-size:20px}
      .collapsible summary{padding:20px 18px;gap:12px}
      .collapse-body{padding:0 18px 22px}
      .summary-group .cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
      .summary-group .cards .card{padding:14px 12px}
      .summary-group .cards .card .value{font-size:24px}
      .summary-group .cards .card .label{font-size:12px}
      .summary-group .cards .card[data-chartable="0"]{grid-column:1/-1}
      .summary-group .grp-head .grp-hint{font-size:13px}
      .card-sub{font-size:12px}
      .pill-toggle,.seg-btn,select,input,.collapse-toggle{min-height:44px}
      .equation{padding:16px;font-size:16px;line-height:1.9}
      footer{padding:26px 18px}
    }
    @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important}}
    main>section.collapsible,.collapsible summary{border-radius:14px}
    .pill-toggle,.collapse-toggle,.filter-chip{border-radius:999px}
    .topbar .quick-country input,.topbar .nav-toggle{border-radius:10px}
    .ctrl-surface{background:var(--paper);box-shadow:none;border-radius:8px}
    .field input,.field select{border-radius:8px}
    .field input:focus,.field select:focus{box-shadow:none;outline:2px solid var(--accent);outline-offset:2px}
    .field>span:first-child,.cs-head .t{font-size:12px;letter-spacing:0;text-transform:none;font-weight:500}
    .act .gd-sym{font-family:var(--sans);font-style:normal}
    /* One balanced header, with a complete topic picker on narrow screens. */
    .topbar{padding:10px 42px}
    .topbar .tb-row1{grid-template-columns:auto minmax(0,1fr) 210px;gap:28px;align-items:center}
    .topbar .brand{grid-column:1;grid-row:1;line-height:1.4;padding:0;align-self:center;width:max-content}
    .topbar .brand>svg{flex:none}
    .nav-stack{grid-column:2;grid-row:1;display:flex;flex-direction:column;gap:4px;min-width:0}
    .topbar .nav-main{display:flex;gap:4px;width:max-content;max-width:100%;padding:3px;background:var(--paper);border-radius:999px;align-self:start;justify-self:start}
    .topbar .nav-main-link{display:flex;align-items:center;min-height:32px;line-height:20px;padding:6px 16px;border:0;border-radius:999px;color:var(--muted)}
    .topbar .nav-main-link.active{background:var(--panel);color:var(--ink-strong);border:0}
    .topbar .nav-main-link:hover{background:var(--panel);color:var(--ink)}
    .topbar .nav-subs{display:flex;gap:8px;min-height:34px;overflow:visible;padding:0;grid-column:auto;grid-row:auto;align-self:stretch}
    .topbar .nav-subs .sub-link{min-height:34px;line-height:20px;padding:7px 12px;border-radius:999px;font-size:13px;font-weight:500;white-space:nowrap}
    .topbar .nav-subs .sub-link.active{background:var(--soft);color:var(--accent-deep);font-weight:600}
    .topbar .quick-country{grid-column:3;grid-row:1;grid-template-columns:1fr;gap:5px;align-self:center;line-height:16px}
    .topbar .quick-country input{height:36px;min-height:36px;line-height:20px;padding:8px 12px;background:var(--paper);border:1px solid var(--line-soft)}
    .topic-choice{display:none}
    @media(max-width:1199px){
      .topbar{padding:10px 24px}
      .topbar .tb-row1{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px 12px}
      .nav-stack{display:contents}
      .topbar .brand{grid-column:1;grid-row:1;font-size:21px}
      .topbar .nav-toggle{display:inline-flex;grid-column:2;grid-row:1;justify-self:end;min-height:40px;line-height:20px;padding:10px 12px;border-radius:999px}
      .topbar .quick-country{grid-column:1;grid-row:2;gap:5px;align-self:stretch}
      .topbar .quick-country input{height:38px;min-height:38px;font-size:16px;padding:8px 12px}
      .topbar .nav-subs{grid-column:2;grid-row:2;display:block;min-width:0;min-height:0;overflow:visible}
      .topbar .nav-subs .sub-link{display:none}
      .topic-choice{display:grid;gap:5px;font-size:12px;font-weight:500;line-height:16px;color:var(--muted);min-width:0}
      .topic-choice select{width:100%;min-width:0;max-width:100%;height:38px;min-height:38px;padding:8px 28px 8px 12px;font-family:var(--sans);font-size:16px;line-height:20px;color:var(--ink);background-color:var(--paper);border:1px solid var(--line-soft);border-radius:10px}
      .topbar .nav-main{display:none;grid-column:1/-1;grid-row:3;width:100%;align-self:stretch;padding:3px;gap:4px}
      .topbar .nav-main.open{display:flex;padding:3px;justify-content:space-between}
      .topbar .nav-main-link{flex:1;justify-content:center;min-height:40px;padding:8px 12px}
    }
    @media(max-width:640px){.topbar{padding:10px 18px}.topic-choice select{font-size:14px}.topbar .quick-country input{font-size:16px}}
  </style>
</head>
<body class="mode-free">
  <div class="topbar">
    <div class="tb-row1">
      <div class="brand">
        <svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true"><ellipse cx="13" cy="13" rx="11.5" ry="5" fill="none" stroke="#2f6f73" stroke-width="1.4" transform="rotate(-22 13 13)"/><circle cx="13" cy="13" r="3.1" fill="#b44e5a"/><circle cx="23.2" cy="9.4" r="1.7" fill="#2f6f73"/></svg>
        <span><span class="e">Erasmus</span><span class="g">Gravity</span></span>
      </div>
      <label class="quick-country" for="quickCountry">Sending country<input id="quickCountry" list="countryOptions" autocomplete="off" placeholder="Sending country or code"></label>
      <button class="nav-toggle" id="navToggle" type="button" aria-expanded="false" aria-controls="primaryNav">
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        Menu
      </button>
      <div class="nav-stack">
        <nav class="nav-main" id="primaryNav" aria-label="Main sections">
          <a class="nav-main-link" data-group="research" href="#sec-intro">Research</a>
          <a class="nav-main-link" data-group="model" href="#sec-overview">Model</a>
          <a class="nav-main-link" data-group="extra" href="#sec-time">Extra</a>
        </nav>
        <nav class="nav-subs" id="dynSubnav" aria-label="Current section topics"></nav>
      </div>
      <div class="modeswitch" role="group" aria-label="View mode" style="display:none">
        <button id="m-free" class="active" type="button">Read</button>
        <button id="m-explore" type="button">Explore</button>
      </div>
    </div>
    <select id="senderSelect" aria-hidden="true" tabindex="-1" style="display:none"></select>
  </div>
  <header class="pagehead">
    <div class="hero-inner">
      <div class="hero-text">
        <h1>Erasmus mobility,<br>explained.</h1>
        <p class="rq"><b>Research question:</b> what explains the size of Erasmus+ Higher Education flows from one country to another? We explore associations with perceived quality of life, institution quality, language affinity and distance, controlling for broad destination prosperity. These observational results do not establish causal effects.</p>
        <div class="meta-strip">
          <span class="readout" id="topStat"></span>
          <span class="scope-pill">KA1 study mobility · cross-border country pairs</span>
        </div>
      </div>
      <aside class="mobility-brief" aria-label="Selected country mobility summary">
        <div class="brief-heading"><span id="briefCountry">Sending country</span><a href="#sec-overview">Explore flows <span aria-hidden="true">↗</span></a></div>
        <div class="brief-total" id="briefTotal"></div>
        <p class="brief-caption">outgoing students in the selected flow sample</p>
        <div class="brief-destinations" id="briefDestinations"></div>
        <p class="brief-foot">Top destinations · share of selected outgoing flows</p>
      </aside>
    </div>
  </header>
  <main>
    <section class="intro" id="sec-intro">
      <h2>A gravity model of student flows</h2>
      <p>The implemented headline model is a cross-sectional PPML gravity specification on flow counts. Separate panel and COVID diagnostics examine different questions; they are not terms of one combined model.</p>
      <div class="equation">
        E[flow<sub>ij</sub> | X] = exp(<br>
        sending-country FE<sub>i</sub> +
        <a class="eq-term" href="#sec-salary">&beta;&#8321; &middot; GDP gap<sub>ij</sub></a> +
        <a class="eq-term" href="#sec-reddit">&beta;&#8322; &middot; Erasmusu rating<sub>j</sub></a> +
        <a class="eq-term" href="#sec-institution">&beta;&#8323; &middot; institution quality<sub>j</sub></a><br>
        + controls(<a class="eq-term ctrl" href="#sec-controls">log distance, language affinity</a>))
      </div>
      <p class="note">The destination j is a city; country-level covariates use its country. GDP gap is the headline prosperity control. Salary and price-level gaps enter a separate robustness specification. Reddit provides supporting text evidence and alternative specifications, not the main QoL regressor.</p>
      <p class="note"><a href="#sec-panel">Panel models</a> use separate origin, destination and year fixed effects. <a href="#sec-covid">COVID diagnostics</a> use destination&times;field, origin and year effects. Pair fixed effects and origin&times;year effects are proposed extensions, not controls implemented here.</p>
    </section>

    <section id="sec-explanatory">
      <h2>Explanatory Variables</h2>
      <p class="note">The implemented variables and their sources. Expected signs describe hypotheses, not findings; the estimates below may differ.</p>
      <div class="cards">
__VARIABLE_CARDS__
      </div>
    </section>

    <section id="sec-results">
      <h2>Model Results</h2>
      <h3>Every coefficient (&beta;) &mdash; headline PPML gravity model
        <button type="button" class="info-btn" aria-expanded="false" aria-controls="ppml-info" onclick="(function(b){var t=document.getElementById('ppml-info');var open=t.style.display!=='block';t.style.display=open?'block':'none';b.setAttribute('aria-expanded',open);})(this)" title="What is Poisson PPML?">&#9432;</button>
      </h3>
      <div id="ppml-info" class="info-popover" style="display:none">
        <strong>Poisson PPML</strong> fits the multiplicative gravity model on the <em>flow level</em> (number of students), not on log-flow. It handles zero flows and stays consistent under heteroskedasticity (Santos Silva &amp; Tenreyro, 2006). Read each coefficient as a semi-elasticity: a unit change in <em>x</em> multiplies expected flow by <code>exp(&beta;)</code> &mdash; i.e. <code>100&middot;(exp(&beta;&middot;&Delta;x) &minus; 1)%</code> change.
      </div>
      <p class="note">Estimated terms from Spec J-main, the cross-sectional PPML model on flow counts with sending-country fixed effects and city-clustered standard errors. Significant (p&lt;0.05) in <strong style="color:var(--accent)">accent</strong>. <strong>Natural-unit effect</strong> is the % change in flow for a tangible unit change &mdash; <code>+$10,000 GDP gap</code>, <code>+1 Erasmusu rating point</code>, <code>+10 QS score points</code>, <code>doubling distance</code>.</p>
      <div id="coeffTable"></div>

      <h3 style="margin-top:24px">Quality-of-life coefficient across specifications</h3>
      <p class="note">&beta;&#8322; across all specs. Outcome is <code>log(1+flow)</code> (OLS/WLS) or flow level (PPML); covariance choices vary by specification. <strong>Headline:</strong> the city-level two-stage (panel destination attractiveness explained by Erasmusu rating).</p>
      <div id="resultsTable"></div>
      <p class="note" style="margin-top:24px">Separate panel specifications and exploratory COVID diagnostics appear in the <a href="#sec-time" style="color:var(--accent)">Time &amp; Shocks</a> act below.</p>
    </section>

    <div class="act">
      <svg class="gd-glyph" width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><ellipse cx="15" cy="15" rx="13" ry="6" fill="none" stroke="#2f6f73" stroke-width="1.5" transform="rotate(-22 15 15)"/><circle cx="15" cy="15" r="4" fill="#b44e5a"/><circle cx="27" cy="11" r="2" fill="#2f6f73"/></svg>
      <div class="gd-main">
        <div class="gd-role">The dependent variable</div>
        <h3>What we are explaining &mdash; the flows themselves</h3>
      </div>
      <span class="gd-sym">flow<sub>ij</sub></span>
    </div>

    <section id="sec-flow-filters" class="collapsible">
      <details open>
        <summary>
          <h2 style="margin:0;font-size:18px;display:flex;align-items:center;gap:10px">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M5 8h6M7 12h2" stroke="#2f6f73" stroke-width="1.6" stroke-linecap="round"/></svg>
            Filter the flows
            <span class="filter-chip" id="flowFilterChip" style="display:none"><span class="fdot"></span><span class="lab">active</span> <span class="fc-active"></span></span>
          </h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <div class="filter-redesign">
            <div class="filter-primary">
              <div class="fp-label">
                <span class="fp-title"><span class="fp-emoji" aria-hidden="true"></span>Sending country</span>
                <span class="fp-hint">Default: Italy. Drives the summary cards, trend chart, scatter and map.</span>
              </div>
              <div class="fp-controls">
                <span class="ip">
                  <svg class="ic" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                  <input id="countrySearch" list="countryOptions" autocomplete="off" placeholder="Search country or code">
                </span>
                <datalist id="countryOptions"></datalist>
                <button id="mapViewAll" type="button" class="pill-toggle"> All outgoing countries</button>
              </div>
            </div>
            <div class="filter-optional">
              <div class="fo-head">
                <span class="fo-title">Narrow further <span style="font-weight:500;color:var(--muted);font-size:12px">(optional)</span></span>
                <button class="reset" type="button" id="resetControls">
                  <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><path d="M13 8a5 5 0 1 1-1.5-3.55M13 2v3h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  Reset all
                </button>
              </div>
              <p class="fo-explain">
                Picking an <b> outgoing university</b> narrows the map and table to flows leaving that institution. Picking an <b> incoming country</b> or <b> incoming university</b> keeps only flows arriving there. Filters AND-combine: the more you set, the smaller the view.
              </p>
              <div class="fo-grid">
                <label class="field"><span><span aria-hidden="true"></span>Outgoing university</span>
                  <span class="ip">
                    <svg class="ic" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                    <input id="outUniSearch" list="outUniOptions" autocomplete="off" placeholder="Sending university or city">
                  </span>
                  <datalist id="outUniOptions"></datalist>
                </label>
                <label class="field"><span><span aria-hidden="true"></span>Incoming country</span>
                  <span class="ip">
                    <svg class="ic" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                    <input id="inCountrySearch" list="inCountryOptions" autocomplete="off" placeholder="Destination country or code">
                  </span>
                  <datalist id="inCountryOptions"></datalist>
                </label>
                <label class="field"><span><span aria-hidden="true"></span>Incoming university</span>
                  <span class="ip">
                    <svg class="ic" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                    <input id="inUniSearch" list="inUniOptions" autocomplete="off" placeholder="Receiving university or city">
                  </span>
                  <datalist id="inUniOptions"></datalist>
                </label>
              </div>
            </div>
          </div>
          <select id="orgLevel" style="display:none">
            <option value="countryUni">Country &rarr; university</option>
            <option value="uniCountry">University &rarr; country</option>
            <option value="uniUni">University &rarr; university</option>
          </select>
          <select id="mapView" style="display:none">
            <option value="sender">Selected outgoing country</option>
            <option value="all">All outgoing countries</option>
          </select>
        </div>
      </details>
    </section>

    <section id="sec-overview">
      <h2><span class="h2-row">Selected Country Overview <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></span></h2>
      <div id="summaryCards"></div>
      <p class="note">Country-level totals; endpoint filters apply only to the map and university table. Main flow definition: Higher Education learners, study mobility activity, age 18+, cross-border flows only.</p>
    </section>

    <section id="sec-map">
      <h2><span class="h2-row">University Flow Map <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></span></h2>
      <div id="mapEmpty" class="map-empty" role="status" hidden>No flows match these filters. <button type="button" onclick="document.getElementById('resetControls').click()">Clear endpoint filters</button></div>
      <div id="map"></div>
      <div class="map-legend">
        <span><span class="legend-dot" style="width:10px;height:10px"></span> smaller flow</span>
        <span><span class="legend-dot" style="width:24px;height:24px"></span> larger flow</span>
        <span id="mapNote">One point per university endpoint, sized by students. Zoom out to aggregate nearby universities into clusters; click a cluster to zoom in and pick a university. Universities sit at their city coordinate; cities without a coordinate match fall back to their country centroid.</span>
      </div>
    </section>

    <section id="sec-trends">
      <h2><span class="h2-row">Mobility Over Time (2014&ndash;2023) <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></span></h2>
      <p class="note">Higher Education study mobility by calendar year of mobility start, from the spatially enriched Erasmus+ panel (V&auml;is&auml;nen et al. 2025). This is the temporal backbone for the panel gravity design.</p>
      <div class="grid">
        <div>
          <h3 style="margin:0 0 6px">All countries &mdash; total outgoing</h3>
          <div class="chart" id="trendTotal"></div>
          <p class="note">Total cross-border HE study participants per year. The 2020 drop reflects the COVID-19 disruption to mobility.</p>
        </div>
        <div>
          <h3 style="margin:0 0 6px" id="trendSenderTitle">Selected country &mdash; top destinations</h3>
          <div class="chart" id="trendSender"></div>
          <p class="note">Yearly flows from the selected sending country to its largest destinations. Use the sending-country selector in the top bar.</p>
        </div>
      </div>
    </section>

    <section id="sec-top-destinations" class="collapsible">
      <details>
        <summary>
          <h2><span class="h2-row">Top Destinations <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></span></h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <div class="chart" id="barChart"></div>
        </div>
      </details>
    </section>

    <section id="sec-destination-table" class="collapsible">
      <details>
        <summary>
          <h2><span class="h2-row">Destination table <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></span></h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <div class="dest-controls" style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px">
            <div class="seg-control" role="tablist" aria-label="Destination view" style="display:flex;flex-wrap:wrap;gap:6px">
              <button type="button" class="seg-btn on" data-view="country" role="tab" aria-selected="true">Country &rarr; Country</button>
              <button type="button" class="seg-btn" data-view="countryUni" role="tab" aria-selected="false">Country &rarr; University</button>
              <button type="button" class="seg-btn" data-view="uniCountry" role="tab" aria-selected="false">University &rarr; Country</button>
              <button type="button" class="seg-btn" data-view="uniUni" role="tab" aria-selected="false">University &rarr; University</button>
            </div>
            <input type="search" id="destTableFilter" placeholder="Filter rows&hellip;" class="dest-filter-input" autocomplete="off">
          </div>
          <p class="note" id="orgFlowNote" style="display:none"></p>
          <div id="destinationTable"></div>
          <div id="orgFlowTable" style="display:none"></div>
        </div>
      </details>
    </section>

    <section id="sec-heatmap" class="collapsible">
      <details>
        <summary>
          <h2>Flow Heatmap</h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <p class="note">Rows and columns use the same country order: countries are sorted by total Erasmus flow volume among the displayed top countries.</p>
          <div class="heatmap-wrap chart" id="heatmap"></div>
        </div>
      </details>
    </section>

    <div class="act ctrl" id="sec-controls">
      <svg class="gd-glyph" width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><ellipse cx="15" cy="15" rx="13" ry="6" fill="none" stroke="#8a949d" stroke-width="1.4" transform="rotate(-22 15 15)"/><circle cx="15" cy="15" r="3.2" fill="#8a949d"/></svg>
      <div class="gd-main">
        <div class="gd-role">Controls &amp; gravity frictions</div>
        <h3>What we hold constant &mdash; plus an exploratory economics block</h3>
      </div>
      <span class="gd-sym">controls</span>
    </div>

    <section id="sec-gdp-gap" class="collapsible">
      <details>
        <summary>
          <h2>GDP gap & mobility <span class="filter-chip"><span class="fdot"></span><span class="lab">Showing</span> <span class="fc-country">&mdash;</span></span></h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <div class="chart" id="scatterChart"></div>
          <p class="note"><strong>GDP gap</strong> = receiving-country GDP per capita minus sending-country GDP per capita (broad prosperity control, &beta;<sub>1</sub>). <strong>Flow share</strong> = flow to that destination divided by all outgoing flows from the selected sending country.</p>
        </div>
      </details>
    </section>

    <section id="sec-economics" class="collapsible">
      <details>
        <summary>
          <h2>Destination economics</h2>
          <span class="collapse-toggle" aria-hidden="true"></span>
        </summary>
        <div class="collapse-body">
          <p class="note"><strong>Reported as robustness, not headline controls.</strong> <code>salary_gap</code> and <code>price_level_gap</code> proxy the same rich-vs-poor-destination dimension as the headline <code>gdp_gap</code> (&beta;<sub>1</sub>): VIFs ≈ 5&ndash;7 in the full-controls PPML, so the three monetary gaps split one signal three ways. The full-economic-controls spec is kept here as an exploratory check because of this multicollinearity, not because the economics are uninteresting. See <code>reports/gravity_model.md &sect;4</code>.</p>
          <p class="note">Click column headers to sort. Destination metrics are weighted by each sending country's flow counts.</p>
          <div id="weightedTable"></div>
        </div>
      </details>
    </section>

    <div class="act">
      <svg class="gd-glyph" width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><ellipse cx="15" cy="15" rx="13" ry="6" fill="none" stroke="#2f6f73" stroke-width="1.5" transform="rotate(-22 15 15)"/><ellipse cx="15" cy="15" rx="8" ry="3.6" fill="none" stroke="#2f6f73" stroke-width="1.3" transform="rotate(-22 15 15)"/><circle cx="15" cy="15" r="3.2" fill="#b44e5a"/></svg>
      <div class="gd-main">
        <div class="gd-role">The explanatory variables</div>
        <h3>What pulls students toward a destination</h3>
      </div>
      <span class="gd-sym">&beta;&#8321; &middot; &beta;&#8322; &middot; &beta;&#8323;</span>
    </div>

    <section id="sec-salary">
      <h2>GDP-per-capita gap</h2>
      <p class="note">Destination minus origin GDP per capita (World Bank, current USD). Read as a <strong>broad prosperity control</strong>, not as a causal economic-pull effect. Salary gap and price-level gap are demoted to robustness because they overlap with GDP and produce an unstable monetary block (VIF ~6.5&ndash;7 in the full controls spec).</p>
      <div class="beta-grid">
        <div class="card"><div class="label"> Source</div><div class="value">World Bank GDP per capita (current USD)</div><div class="sub"><code>gdp_gap_usd_wb</code> &middot; pair-level destination minus origin, joined onto the KA1 2022 panel.</div></div>
        <div class="card"><div class="label"> Estimation</div><div class="value">PPML on bilateral flows, city-clustered SE</div><div class="sub">Cross-section Poisson with sending-country FE on the 2022 KA1 panel; gdp_gap enters as the only monetary term.</div></div>
        <div class="card" data-coef-card="GDP-per-capita gap"><div class="label"> Effect</div><div class="value"><span class="v-num">&mdash;</span></div><div class="effect-row"><span>loading&hellip;</span></div></div>
        <div class="card"><div class="label"> Evidence (robustness)</div><div class="value">NACE-sector earnings explorer</div><div class="sub">Pick a country &amp; unit below to compare monthly earnings by sector &mdash; the salary heterogeneity behind the demoted salary-gap robustness term. See full controls breakdown under <a href="#sec-controls" style="color:var(--accent)">Controls</a>.</div></div>
      </div>
      <div class="salary-controls" style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;margin:12px 0 6px">
        <label class="field" style="flex:1;min-width:180px"><span>Salary country</span><div class="selwrap"><select id="earnCountry"></select></div></label>
        <label class="field" style="flex:1;min-width:180px"><span>Salary unit</span>
          <div class="selwrap">
            <select id="earnUnit">
              <option value="eur">Euro (EUR)</option>
              <option value="pps">Purchasing power standard (PPS)</option>
            </select>
          </div>
        </label>
      </div>
      <div class="chart" id="earningsChart"></div>
      <p class="note">Mean monthly gross earnings by NACE economic sector, Structure of Earnings Survey 2018. This is a salary-by-sector reference, <strong>not</strong> salary by field of study (Eurostat does not publish earnings by field of study). Coverage is limited to the 17 countries that report this dataset.</p>
    </section>

    <section id="sec-reddit">
      <h2>Quality of life</h2>
      <p class="note">A text layer over r/Erasmus and a numeric layer from Erasmusu city ratings. Tests whether students are pulled toward places that read as friendlier, cheaper, livelier in student talk.</p>
      <div class="beta-grid">
        <div class="card"><div class="label"> Source</div><div class="value">Reddit r/Erasmus + Erasmusu city ratings</div><div class="sub"><span id="redditCoverage" class="coverage-badge"></span>Destinations extracted via OpenRouter (DeepSeek) + Pydantic &middot; sentiment, themes, city/country. Weighted-net sentiment uses confidence &times; log(1+upvotes) &times; <em>EWMA age-decay</em> (1-year half-life), so stale opinions fade as fresh ones arrive on re-scrape.</div></div>
        <div class="card"><div class="label"> Estimation</div><div class="value">City-level two-stage</div><div class="sub">Stage 1: PPML with separate origin, destination-city and year effects. Stage 2: opinion-weighted regression of city effects on Erasmusu ratings, with country-clustered standard errors. The coefficient is on estimated log-attractiveness, not a causal flow response.</div></div>
        <div class="card" data-coef-card="Two-stage CITY: Erasmusu rating"><div class="label"> Effect</div><div class="value"><span class="v-num">&mdash;</span></div><div class="effect-row"><span>loading&hellip;</span></div></div>
        <div class="card"><div class="label"> Evidence</div><div class="value">Per-country sentiment table</div><div class="sub">Net sentiment = (pos &minus; neg) / mentions &middot; small per-country counts, treat as qualitative signal. See table below.</div></div>
      </div>
      <p class="note" style="margin-top:14px">Destination mentions extracted from r/Erasmus posts and comments. <strong>Score-weighted net</strong> also weights by extraction confidence and log Reddit score. Click headers to sort.</p>
      <div id="redditTable"></div>
    </section>

    <section id="sec-institution">
      <h2>Institution quality</h2>
      <p class="note">Each destination university enters as a ranking score. The headline cross-sectional model conditions on GDP gap, distance, language affinity and Erasmusu ratings. QS scores proxy academic attractiveness and may also reflect institutional scale and networks.</p>
      <div class="beta-grid">
        <div class="card"><div class="label"> Source</div><div class="value">QS World University Rankings 2023</div><div class="sub">QS <strong>overall score</strong> (0&ndash;100 composite of research, teaching, employability, internationalisation). Each Erasmus city gets its best-ranked university's score. European institutions geocoded via Nominatim and snapped to the nearest Erasmus city within 35&nbsp;km &middot; <code>institution_quality.csv</code>.</div></div>
        <div class="card"><div class="label"> Estimation</div><div class="value">PPML, ranking score on destination city</div><div class="sub">Same gravity spec as &beta;&#8321; with the destination's best-ranked university score added as a city-level regressor.</div></div>
        <div class="card" data-coef-card="Institution quality"><div class="label"> Effect</div><div class="value"><span class="v-num">&mdash;</span></div><div class="effect-row"><span>loading&hellip;</span></div></div>
        <div class="card"><div class="label"> Evidence</div><div class="value">Crowd cross-check: StudyPortals</div><div class="sub">User ratings of universities, scraped from Wayback. Independent crowd-vs-expert signal &middot; <code>user_institution_quality.csv</code>.</div></div>
      </div>
      <p class="note" style="margin-top:14px">Comparing specifications can change both the sample and the controls, so coefficient differences alone do not isolate an institution-quality effect. See <a href="#sec-results" style="color:var(--accent)">Model Results</a> for the full coefficient table.</p>
    </section>

    <div class="act" id="sec-time">
      <svg class="gd-glyph" width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><ellipse cx="15" cy="15" rx="13" ry="6" fill="none" stroke="#2f6f73" stroke-width="1.5" transform="rotate(-22 15 15)"/><ellipse cx="15" cy="15" rx="13" ry="6" fill="none" stroke="#b44e5a" stroke-width="1.2" transform="rotate(22 15 15)"/><circle cx="15" cy="15" r="3.4" fill="#b44e5a"/></svg>
      <div class="gd-main">
        <div class="gd-role">Time &amp; shocks</div>
        <h3>The model run through every year &mdash; and the 2020 break</h3>
      </div>
      <span class="gd-sym">&Sigma;<sub>t</sub></span>
    </div>

    <section id="sec-panel">
      <h2>Panel gravity, 2014&ndash;2023</h2>
      <p class="note">
        We refit the gravity PPML on the <strong>panel</strong> of country-pair flows by year (2014&ndash;2023), with separate <strong>origin, destination and year fixed effects</strong>. These absorb stable origin/destination differences and common annual variation, not all bilateral ties. The plotted series shows year effects relative to 2014. This Stage-1 fit uses default GLM covariance; subsequent models have their own clustering choices.
      </p>
      <p class="note" style="margin-top:8px">
        A flat line would say "Erasmus volume is stable once you control for gravity". Instead we see a steady positive drift through 2019 (program scale-up), the sharp <strong style="color:var(--accent-2)">2020 collapse</strong> when borders closed, a partial 2021 rebound, and a return above the 2019 baseline by 2023 &mdash; this is a descriptive common time pattern, not proof that composition changes or other confounders have been eliminated.
      </p>
      <div class="chart" id="yearChart"></div>
      <p class="note" style="margin-top:8px;font-size:12px"><strong>How to read:</strong> dot = year FE coefficient &middot; dashed line = 2014 baseline (0) &middot; <span style="color:var(--accent-2)">coral 2020 marker</span> = COVID shock year.</p>

      <h3 style="margin-top:24px">Time-varying destination indicators</h3>
      <p class="note">When we let a regressor itself vary by year (instead of absorbing time into a single FE), within-destination movement over time identifies it. Three time-varying panels are estimated. Two of the three say something; one says nothing &mdash; that null is itself worth reading.</p>
      <p class="note" style="font-size:12px"><strong>What is a "life-satisfaction point"?</strong> The OWID series uses the <em>Cantril ladder</em> from the Gallup World Poll / World Happiness Report: respondents rate their current life on a 0&ndash;10 scale ("worst possible life" to "best possible life"). The country score is the mean response. A "+1 life-satisfaction point" means moving the destination's annual mean one full rung up the ladder &mdash; e.g. roughly the Spain↔Switzerland gap in 2022. Source: <code>data/processed/owid_country_year.csv</code>.</p>
      <div class="beta-grid">
        <div class="card" data-coef-card="Panel time-varying: Quality of life">
          <div class="label">&beta;&#8322; time-varying QoL</div>
          <div class="value"><span class="v-num">&mdash;</span></div>
          <div class="effect-row"><span>loading&hellip;</span></div>
          <div class="sub">OWID life satisfaction (Cantril ladder), 99 countries &times; 10 years. Origin + destination + year FE, dest-clustered SE.</div>
        </div>
        <div class="card" data-coef-card="Panel time-varying: Education spending">
          <div class="label">edu spending %GDP</div>
          <div class="value"><span class="v-num">&mdash;</span></div>
          <div class="effect-row"><span>loading&hellip;</span></div>
          <div class="sub">OWID government education spending. Same FE structure as life satisfaction. Insignificant &mdash; a useful null.</div>
        </div>
        <div class="card" data-coef-card="Panel time-varying: Institution quality">
          <div class="label">&beta;&#8323; time-varying QS</div>
          <div class="value"><span class="v-num">&mdash;</span></div>
          <div class="effect-row"><span>loading&hellip;</span></div>
          <div class="sub">QS World Rankings 2014/2017/2018/2023 (Wayback editions), snapped to Erasmus cities. Dest-city + origin + year FE.</div>
        </div>
      </div>
      <p class="note" style="margin-top:12px;font-size:12px"><strong>Read:</strong> only <strong>life satisfaction</strong> identifies cleanly as time-varying &mdash; +25.4% per life-satisfaction point, p=0.035. The other two are null. The QS null reflects QS-score stickiness (within-city year-to-year variance is tiny); the education-spending null suggests within-country temporal drift in public-education investment doesn't move Erasmus flows.</p>
    </section>

    <section id="sec-covid">
      <h2>The 2020 shock</h2>
      <p class="note">We move from the smooth year-FE path to a real, date-pinned shock. Each ISCED-F broad field of study is mapped to one NACE sector, then we ask: did flows into (destination, field) cells whose mapped sector was hit harder in 2020 fall by more, relative to 2019? We run it twice &mdash; once with wage-based hit (LCI), once with employment-based hit (LFS) &mdash; because wage subsidies may affect the interpretation of the LCI wage series.</p>
      <div class="beta-grid">
        <div class="card"><div class="label"> Source</div><div class="value">Two hit measures, same panel</div><div class="sub"><b>LCI</b> <code>covid_sector_hit.csv</code> &mdash; sector wage growth deviation, 2015&ndash;2019 baseline. <b>LFS</b> <code>covid_employment_hit.csv</code> &mdash; sector employment growth deviation, same baseline. Field &rarr; NACE map in <code>src/erasmusgravity/fields.py</code>.</div></div>
        <div class="card"><div class="label"> Estimation</div><div class="value">PPML, dest&times;field + sending + year FE, cell-clustered SE</div><div class="sub">268&ndash;328 (destination, field) cells &middot; 39 origins &middot; 2014&ndash;2023 &middot; Turkey dropped (hyperinflation). Same FE structure across both measures so coefficients are directly comparable.</div></div>
        <div class="card" data-coef-card="COVID DiD"><div class="label"> Effect</div><div class="value"><span class="v-num">&mdash;</span></div><div class="effect-row"><span>loading&hellip;</span></div><div class="effect-row" data-emp-row><span>loading employment hit&hellip;</span></div></div>
        <div class="card"><div class="label">Evidence</div><div class="value">Sensitivity to the shock measure</div><div class="sub">The reported wage-based and employment-based results differ. Wage subsidies are a possible explanation, not an identified mechanism. Insignificant employment estimates do not establish a uniform lockdown effect or rule out field-specific responses. Read these as exploratory diagnostics, with the fitted estimates below.</div></div>
      </div>
      <div class="chart" id="covidEventStudyChart"></div>
      <p class="note" style="margin-top:8px;font-size:12px"><strong>How to read:</strong> two series of year&times;hit interactions (2019 as reference). <span style="color:var(--accent-2)"><b>Coral</b></span> = LCI wage-based hit. <span style="color:var(--accent)"><b>Teal</b></span> = LFS employment-based hit. Filled dots = p&lt;0.05. Dashed horizontal line at zero. Dashed vertical line marks 2019 reference. LCI on a different y-scale from LFS &mdash; coefficients in the Effect card read as "% flow change per 1 pp harder hit sector".</p>
    </section>

    <section id="sec-data">
      <h2>Data Sources and Measurement Notes</h2>
      <ul class="source-list">
        <li><strong>Erasmus flows:</strong> <code>Erasmus-KA1-Mobility-Data-2022.xlsx</code>, sheet <code>KA1 mobilities 2022</code>. Filtered to Higher Education study mobility.</li>
        <li><strong>Flow scope:</strong> Erasmus mobility is modeled as cross-border origin&ndash;destination movement. Same-country rows in the KA1 file are extremely rare and treated as coding artifacts, not as a domestic Erasmus layer.</li>
        <li><strong>HE grants:</strong> <code>annual-report-2024-statistical-annex.xlsx</code>, sheet <code>KA1_estimated paxs</code>, Call Year 2022, Higher Education rows.</li>
        <li><strong>GDP per capita:</strong> World Bank current US$ is used for the dashboard GDP-gap plot because it covers more Erasmus partner countries; Eurostat GDP remains in the processed dataset.</li>
        <li><strong>Price levels and net earnings:</strong> Eurostat API. Missing values are shown as <code>n/a</code>.</li>
        <li><strong>Scholarship proxy:</strong> grant per participant is applicant-country-level, not the exact grant received by individual students or country pairs. Treat the social-elevator angle as descriptive, not causal.</li>
        <li><strong>Quality of life (built):</strong> Erasmusu city ratings are the main city-level regressor. Reddit destination sentiment and themes extracted via DeepSeek and Pydantic provide supporting text evidence and alternative specifications. OWID life satisfaction is a separate country-year panel proxy. These sources are not interchangeable.</li>
        <li><strong>Institution quality (built):</strong> QS scores matched to destination cities, with StudyPortals ratings as a cross-check. Scores may reflect capacity and networks as well as academic quality.</li>
        <li><strong>Language affinity (built):</strong> shared-language-family indicator used as an origin&ndash;destination control, not an instrument or a causal mechanism.</li>
      </ul>
    </section>
  </main>
  <footer>
    <div style="font-size:16px"><b>ErasmusGravity</b> · Economic Attractiveness and Erasmus Mobility</div>
    <div>Text Analysis and Spatial Data for Economists · SP 2026 · Leonardo Palanca</div>
  </footer>
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
    const redditMeta = payload.redditMeta || {};
    const timeSeries = payload.timeSeries || [];
    const regressionResults = payload.regressionResults || [];
    const panelYears = payload.panelYears || [];
    const covidEventStudy = payload.covidEventStudy || [];
    const covidEventStudyEmployment = payload.covidEventStudyEmployment || [];
    const modelCoefficients = payload.modelCoefficients || [];
    const senderSelect = document.getElementById('senderSelect');
    const countrySearch = document.getElementById('countrySearch');
    const countryOptions = document.getElementById('countryOptions');
    const orgLevelSelect = document.getElementById('orgLevel');
    const mapViewSelect = document.getElementById('mapView');
    const outUniSearch = document.getElementById('outUniSearch');
    const outUniOptions = document.getElementById('outUniOptions');
    const inCountrySearch = document.getElementById('inCountrySearch');
    const inCountryOptions = document.getElementById('inCountryOptions');
    const inUniSearch = document.getElementById('inUniSearch');
    const inUniOptions = document.getElementById('inUniOptions');
    const earnCountrySelect = document.getElementById('earnCountry');
    const earnUnitSelect = document.getElementById('earnUnit');
    const tooltip = document.getElementById('tooltip');
    let weightedSort = { key: 'outgoing', dir: -1 };
    let destinationSort = { key: 'flow_count', dir: -1 };
    let redditSort = { key: 'mentions', dir: -1 };
    let redditExpanded = false;
    const REDDIT_MIN_MENTIONS = 10;
    const REDDIT_TOP_N = 3;

    const fmtInt = value => value == null ? 'n/a' : Math.round(value).toLocaleString('en-US');
    const fmtMoney = value => value == null ? 'n/a' : Math.round(value).toLocaleString('en-US');
    const fmtOne = value => value == null ? 'n/a' : Number(value).toLocaleString('en-US', { maximumFractionDigits: 1 });
    const fmtPct = value => value == null ? 'n/a' : (value * 100).toLocaleString('en-US', { maximumFractionDigits: 1 }) + '%';

    function formatCoefficient(value, digits = 3) {
      if (value == null || !Number.isFinite(Number(value))) return '—';
      const n = Number(value);
      return n !== 0 && Math.abs(n) < 0.001 ? n.toExponential(2) : n.toFixed(digits);
    }
    function formatP(value) {
      if (value == null || !Number.isFinite(Number(value))) return 'not reported';
      return Number(value) < 0.001 ? '&lt;0.001' : Number(value).toFixed(3);
    }

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

    function senderRowsFiltered(code) {
      const uniInput = (typeof outUniSearch !== 'undefined' && outUniSearch) ? outUniSearch.value : '';
      const uniQ = norm(uniInput);
      if (!uniQ) return senderRows(code);
      const src = (orgFlowTables && orgFlowTables.uniCountry) || [];
      const matched = src.filter(r => r.sending_code === code &&
        (norm(r.sending_org).includes(uniQ) || norm(r.sending_city).includes(uniQ)));
      if (!matched.length) return [];
      const agg = new Map();
      matched.forEach(r => {
        const prev = agg.get(r.receiving_code) || { receiving_code: r.receiving_code, receiving_country: r.receiving_country, flow_count: 0 };
        prev.flow_count += r.flow_count;
        agg.set(r.receiving_code, prev);
      });
      const flowsByPair = new Map(flows.map(row => [`${row.sending_code}|${row.receiving_code}`, row]));
      const out = [...agg.values()].map(r => {
        const ref = flowsByPair.get(`${code}|${r.receiving_code}`) || {};
        return { ...ref, ...r, sending_code: code };
      });
      const total = out.reduce((s, r) => s + r.flow_count, 0);
      out.forEach(r => { r.flow_share = total ? r.flow_count / total : 0; });
      return out;
    }

    const norm = value => String(value ?? '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '');
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

    const SENDER_STATS = (() => {
      const out = new Map();
      const wsum = (acc, key, weight, val) => {
        if (val == null || !Number.isFinite(val)) return;
        acc[key + 'W'] = (acc[key + 'W'] || 0) + weight * val;
        acc[key + 'D'] = (acc[key + 'D'] || 0) + weight;
      };
      flows.forEach(row => {
        const code = row.sending_code;
        let agg = out.get(code);
        if (!agg) {
          agg = {
            outgoing: 0,
            destinations: new Set(),
            richerFlow: 0,
            grants: row.sender_he_grants_eur ?? null,
            grantPerEstimated: row.sender_he_grant_per_estimated_participant_eur ?? null,
            topOut: [],
          };
          out.set(code, agg);
        }
        agg.outgoing += row.flow_count;
        agg.destinations.add(row.receiving_code);
        if (row.gdp_gap_usd_wb > 0) agg.richerFlow += row.flow_count;
        wsum(agg, 'gdpGap', row.flow_count, row.gdp_gap_usd_wb);
        wsum(agg, 'earnGap', row.flow_count, row.earnings_gap);
        wsum(agg, 'priceGap', row.flow_count, row.price_level_gap);
        agg.topOut.push({ code: row.receiving_code, country: row.receiving_country, flow: row.flow_count });
      });
      // incoming-side aggregates (this code as receiver)
      const inAgg = new Map();
      flows.forEach(row => {
        const code = row.receiving_code;
        let agg = inAgg.get(code);
        if (!agg) { agg = { incoming: 0, origins: new Set(), topIn: [] }; inAgg.set(code, agg); }
        agg.incoming += row.flow_count;
        agg.origins.add(row.sending_code);
        agg.topIn.push({ code: row.sending_code, country: row.sending_country, flow: row.flow_count });
      });
      const finalStats = new Map();
      const allCodes = new Set([...out.keys(), ...inAgg.keys()]);
      allCodes.forEach(code => {
        const o = out.get(code) || {};
        const i = inAgg.get(code) || {};
        const outgoing = o.outgoing || 0;
        const incoming = i.incoming || 0;
        const topOut = (o.topOut || []).sort((a, b) => b.flow - a.flow).slice(0, 3)
          .map(d => ({ ...d, share: outgoing ? d.flow / outgoing : 0 }));
        const topIn = (i.topIn || []).sort((a, b) => b.flow - a.flow).slice(0, 3)
          .map(d => ({ ...d, share: incoming ? d.flow / incoming : 0 }));
        finalStats.set(code, {
          outgoing,
          incoming,
          net: outgoing - incoming,
          destinations: (o.destinations && o.destinations.size) || 0,
          richerShare: outgoing ? (o.richerFlow || 0) / outgoing : null,
          gdpGapMean: o.gdpGapD ? o.gdpGapW / o.gdpGapD : null,
          earnGapMean: o.earnGapD ? o.earnGapW / o.earnGapD : null,
          priceGapMean: o.priceGapD ? o.priceGapW / o.priceGapD : null,
          grants: o.grants ?? null,
          grantPerEstimated: o.grantPerEstimated ?? null,
          topOut,
          topIn,
        });
      });
      return finalStats;
    })();

    function metricSummary(key) {
      const values = [];
      SENDER_STATS.forEach(s => { if (s[key] != null && Number.isFinite(s[key])) values.push(s[key]); });
      values.sort((a, b) => b - a);
      const mean = values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : null;
      return { values, mean, n: values.length };
    }

    function rankIn(values, value) {
      if (value == null || !Number.isFinite(value)) return null;
      const i = values.findIndex(v => v <= value);
      return i === -1 ? values.length + 1 : i + 1;
    }

    function rankTint(rank, n) {
      if (rank == null || !n) return { bg: 'var(--soft-2)', fg: 'var(--muted)' };
      const pct = (rank - 1) / Math.max(n - 1, 1);
      if (pct <= 0.20) return { bg: 'rgba(47,111,115,.18)', fg: 'var(--accent-deep)' };
      if (pct <= 0.45) return { bg: 'rgba(47,111,115,.10)', fg: 'var(--accent)' };
      if (pct <= 0.70) return { bg: 'var(--soft-2)', fg: 'var(--muted)' };
      return { bg: 'rgba(180,78,90,.10)', fg: 'var(--accent-2-deep)' };
    }

    function rankLine(value, key, fmt) {
      const { values, mean, n } = metricSummary(key);
      const rank = rankIn(values, value);
      if (!n) return '';
      const meanStr = mean == null ? 'n/a' : fmt(mean);
      const { bg, fg } = rankTint(rank, n);
      const rankStr = rank == null ? 'n/a' : `top ${rank} of ${n}`;
      const pct = rank == null ? 0 : 1 - (rank - 1) / Math.max(n - 1, 1);
      const warm = rank != null && (rank - 1) / Math.max(n - 1, 1) > 0.65 ? ' warm' : '';
      const barFill = Math.max(4, Math.round(pct * 100));
      return `<div class="card-sub">
        <span class="rank-pill" style="background:${bg};color:${fg}">${rankStr}</span>
        <span class="mean-line">mean ${meanStr}</span>
        <span class="rank-bar${warm}"><span style="width:${barFill}%"></span></span>
      </div>`;
    }

    function meanOnlyLine(value, key, fmt, note) {
      const { mean, n } = metricSummary(key);
      if (!n) return '';
      const meanStr = mean == null ? 'n/a' : fmt(mean);
      const noteHTML = note ? `<span class="card-note">${note}</span>` : '';
      return `<div class="card-sub"><span class="mean-line">mean ${meanStr}</span>${noteHTML}</div>`;
    }

    function vsMeanLine(value, key, fmt) {
      const { mean, n } = metricSummary(key);
      if (!n || mean == null || value == null || !Number.isFinite(value)) return '';
      const diff = value - mean;
      const cls = diff > 0 ? 'pos' : diff < 0 ? 'neg' : 'neu';
      const sign = diff > 0 ? '+' : diff < 0 ? '−' : '';
      const pillBg = diff > 0 ? 'rgba(47,111,115,.14)' : diff < 0 ? 'rgba(180,78,90,.12)' : 'var(--soft-2)';
      const pillFg = diff > 0 ? 'var(--accent-deep)' : diff < 0 ? 'var(--accent-2-deep)' : 'var(--muted)';
      return `<div class="card-sub">
        <span class="rank-pill" style="background:${pillBg};color:${pillFg}">${sign}${fmt(Math.abs(diff))} vs mean</span>
        <span class="mean-line">mean ${fmt(mean)}</span>
      </div>`;
    }

    function fmtCompact(v) {
      if (v == null || !Number.isFinite(v)) return '';
      const a = Math.abs(v);
      if (a >= 1e6) return (v / 1e6).toFixed(1) + 'M';
      if (a >= 1e3) return (v / 1e3).toFixed(1) + 'k';
      if (a < 1 && a > 0) return v.toFixed(2);
      return Math.round(v).toLocaleString('en-US');
    }

    function distChart(value, key, fmt) {
      const { values, mean, n } = metricSummary(key);
      if (!n || value == null || !Number.isFinite(value)) return '';
      const sorted = [...values].sort((a, b) => a - b);
      const min = sorted[0];
      const max = sorted[sorted.length - 1];
      if (min === max) return '';
      const w = 320, h = 44, pad = 6;
      const x = v => pad + ((v - min) / (max - min)) * (w - 2 * pad);
      const dots = sorted.map(v => `<circle cx="${x(v).toFixed(1)}" cy="${h / 2}" r="2.3" fill="rgba(47,111,115,.32)"/>`).join('');
      const meanX = x(mean).toFixed(1);
      const myX = x(value).toFixed(1);
      const fmtAxis = (typeof fmt === 'function') ? v => fmtCompact(v) : v => v;
      return `<div class="card-chart">
        <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
          <line x1="${pad}" y1="${h / 2}" x2="${w - pad}" y2="${h / 2}" stroke="#e7ebef" stroke-width="1"/>
          ${dots}
          <line x1="${meanX}" y1="6" x2="${meanX}" y2="${h - 6}" stroke="#5f6b76" stroke-width="1" stroke-dasharray="3 2"/>
          <circle cx="${myX}" cy="${h / 2}" r="5" fill="#b44e5a" stroke="#fff" stroke-width="2"/>
        </svg>
        <div class="card-chart-axis">
          <span>${fmtAxis(min)}</span>
          <span class="mean-tick">mean ${fmtAxis(mean)}</span>
          <span>${fmtAxis(max)}</span>
        </div>
        <div class="card-chart-hint">Each dot is one sending country &middot; coral = current selection &middot; dashed line = mean.</div>
      </div>`;
    }

    const fmtSigned = value => {
      if (value == null || !Number.isFinite(value)) return 'n/a';
      return Math.abs(Math.round(value)).toLocaleString('en-US');
    };
    const fmtSignedMoney = value => fmtSigned(value);

    function valueWithDelta(value, fmt) {
      if (value == null || !Number.isFinite(value)) return fmt(value);
      if (value === 0) return fmt(0);
      const cls = value > 0 ? 'pos' : 'neg';
      const sym = value > 0 ? '+' : '−';
      return `<span class="delta ${cls}">${sym}</span>${fmt(value)}`;
    }

    function renderCard(card) {
      let sub;
      if (card.subMode === 'meanOnly') sub = meanOnlyLine(card.value, card.key, card.fmt, card.note);
      else if (card.subMode === 'vsMean') sub = vsMeanLine(card.value, card.key, card.fmt);
      else sub = rankLine(card.value, card.key, card.fmt);
      const valHTML = card.signed ? valueWithDelta(card.value, card.fmt) : card.fmt(card.value);
      const chart = card.noChart ? '' : distChart(card.value, card.key, card.fmt);
      return `<div class="card" data-chartable="${chart ? '1' : '0'}"><div class="label">${card.label}</div><div class="value">${valHTML}</div>${sub}${chart}</div>`;
    }

    function renderTopList(items, emptyMsg) {
      if (!items || !items.length) return `<div class="card-sub"><span class="card-note">${emptyMsg}</span></div>`;
      return `<ol class="destination-list">` + items.map((d, i) =>
        `<li><span class="dl-rank">${i + 1}</span><span class="dl-name"><span class="dl-code">${d.code}</span>${escapeHtml(d.country || d.code)}</span><span class="dl-pct">${fmtPct(d.share)}<span class="dl-flow">&middot; ${fmtInt(d.flow)}</span></span></li>`
      ).join('') + `</ol>`;
    }

    function renderGroup(num, total, name, emoji, hint, cardsHTML, footHTML) {
      const foot = footHTML ? `<div class="grp-foot">${footHTML}</div>` : '';
      return `<div class="summary-group"><div class="grp-head"><span class="grp-name">${name}</span><span class="grp-hint">${hint}</span></div><div class="cards">${cardsHTML}</div>${foot}</div>`;
    }

    function renderSummary(rows) {
      const code = senderSelect.value;
      const stats = SENDER_STATS.get(code) || {};
      const flow = [
        { emoji: '', label: 'Outgoing students', key: 'outgoing', value: stats.outgoing, fmt: fmtInt },
        { emoji: '', label: 'Incoming students', key: 'incoming', value: stats.incoming, fmt: fmtInt },
        { emoji: '', label: 'Net (out − in)', key: 'net', value: stats.net, fmt: fmtSigned, signed: true },
        { emoji: '', label: 'Destinations reached', key: 'destinations', value: stats.destinations, fmt: fmtInt },
      ].map(renderCard).join('');

      const money = [
        { emoji: '', label: 'Weighted dest. GDP-pc gap, USD', key: 'gdpGapMean', value: stats.gdpGapMean, fmt: fmtSignedMoney, signed: true, subMode: 'vsMean' },
        { emoji: '', label: 'Weighted dest. earnings gap, EUR', key: 'earnGapMean', value: stats.earnGapMean, fmt: fmtSignedMoney, signed: true, subMode: 'vsMean' },
        { emoji: '', label: 'Weighted dest. price-level gap', key: 'priceGapMean', value: stats.priceGapMean, fmt: fmtSigned, signed: true, subMode: 'vsMean' },
        { emoji: '', label: 'Share to richer GDP-pc countries', key: 'richerShare', value: stats.richerShare, fmt: fmtPct, subMode: 'vsMean' },
      ].map(renderCard).join('');

      const destinations = `
        <div class="card" data-chartable="0"><div class="label">Top 3 outflows</div>${renderTopList(stats.topOut, 'No outgoing flows.')}</div>
        <div class="card" data-chartable="0"><div class="label">Top 3 inflows</div>${renderTopList(stats.topIn, 'No incoming flows.')}</div>
      `;

      const grant = [
        { emoji: '', label: 'HE grants, EUR', key: 'grants', value: stats.grants, fmt: fmtMoney, subMode: 'vsMean' },
        { emoji: '', label: 'Grant per estimated participant', key: 'grantPerEstimated', value: stats.grantPerEstimated, fmt: fmtMoney, subMode: 'vsMean' },
      ].map(renderCard).join('');

      const moneyFoot = 'No <em>top X</em> on this group &mdash; each variable lives on its own scale and units, so a ranked position would mislead more than it helps. Compare each card to its own <em>mean</em>; tap a card for the full distribution.';
      const grantFoot = 'Grants are absolute national budgets, so rank reflects country size more than generosity. We show only the gap vs the European mean.';

      document.getElementById('summaryCards').innerHTML = `<div class="summary-stack">
        ${renderGroup('01', '04', 'Flow', '', 'Volume on each side of the gate.', flow)}
        ${renderGroup('02', '04', 'Money', '', 'What students step into &mdash; weighted by where they go.', money, moneyFoot)}
        ${renderGroup('03', '04', 'Destinations', '', 'The top-3 partners on each side of the flow.', destinations)}
        ${renderGroup('04', '04', 'Grant', '', 'National Erasmus budget &mdash; absolute, not per student.', grant, grantFoot)}
      </div>`;
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

    const COEF_ORDER = [
      'GDP-per-capita gap',
      'Quality of life',
      'Institution quality',
      'Language affinity',
      'Distance',
      'Salary gap',
      'Price-level gap',
    ];
    function coefRank(row) {
      const v = String(row.variable || '');
      for (let i = 0; i < COEF_ORDER.length; i++) {
        if (v.startsWith(COEF_ORDER[i])) return i;
      }
      return COEF_ORDER.length + 1;
    }
    function symbolRank(row) {
      const s = String(row.symbol || '');
      if (s === 'β₁') return 0;
      if (s === 'β₂') return 1;
      if (s === 'β₃') return 2;
      return 10;
    }
    function orderedCoefficients() {
      return [...modelCoefficients].sort((a, b) => {
        const da = symbolRank(a), db = symbolRank(b);
        if (da !== db) return da - db;
        return coefRank(a) - coefRank(b);
      });
    }

    function invNormCDF(p) {
      if (!(p > 0 && p < 1)) return NaN;
      const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
      const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
      const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
      const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
      const pLow = 0.02425, pHigh = 1 - pLow;
      let q, r;
      if (p < pLow) {
        q = Math.sqrt(-2 * Math.log(p));
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
      } else if (p <= pHigh) {
        q = p - 0.5; r = q * q;
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
      } else {
        q = Math.sqrt(-2 * Math.log(1 - p));
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
      }
    }

    function approxSE(beta, p) {
      if (beta == null || p == null) return null;
      if (p <= 0 || p >= 1) return null;
      const z = Math.abs(invNormCDF(p / 2));
      if (!Number.isFinite(z) || z === 0) return null;
      return Math.abs(beta) / z;
    }

    function fillCovidDiDCard() {
      const card = document.querySelector('[data-coef-card="COVID DiD"]');
      if (!card) return;
      const lci = regressionResults.find(r => String(r.spec || '').startsWith('COVID DiD:'));
      const emp = regressionResults.find(r => String(r.spec || '').startsWith('COVID DiD (employment)'));
      const valBox = card.querySelector('.value .v-num');
      const rows = card.querySelectorAll('.effect-row');
      const renderRow = (r, label) => {
        if (!r || r.beta == null) return `<span><b>${label}</b></span><span class="sig-tag pln">not estimated</span>`;
        const beta = +r.beta, p = r.p == null ? null : +r.p;
        const se = r.se == null ? null : Number(r.se);
        const sig = p != null && p < 0.05;
        return `
          <span><b>${label}</b></span>
          <span>β <b>${(beta >= 0 ? '+' : '') + beta.toFixed(4)}</b></span>
          ${se != null ? `<span>SE <b>${formatCoefficient(se,4)}</b></span>` : ''}
          <span>p <b>${formatP(p)}</b></span>
          <span class="sig-tag ${sig ? 'sig' : 'nsg'}">${sig ? 'sig p&lt;.05' : 'n.s.'}</span>
        `;
      };
      if (valBox && lci && lci.beta != null) {
        const beta = +lci.beta, sig = +lci.p < 0.05;
        valBox.textContent = (beta >= 0 ? '+' : '') + beta.toFixed(4);
        valBox.className = 'v-num ' + (sig ? 'sig' : 'nsg');
      }
      if (rows[0]) rows[0].innerHTML = renderRow(lci, 'LCI');
      if (rows[1]) rows[1].innerHTML = renderRow(emp, 'LFS');
    }

    function renderCovidEventStudy() {
      const el = document.getElementById('covidEventStudyChart');
      if (!el) return;
      if (!covidEventStudy.length && !covidEventStudyEmployment.length) {
        el.innerHTML = '<p class="note">No event-study coefficients yet.</p>'; return;
      }
      const W = 760, H = 320, left = 56, right = 16, top = 36, bottom = 48;
      const rowsLci = [...covidEventStudy].sort((a, b) => a.year - b.year);
      const rowsEmp = [...covidEventStudyEmployment].sort((a, b) => a.year - b.year);
      const allYears = Array.from(new Set([...rowsLci.map(r => +r.year), ...rowsEmp.map(r => +r.year), 2019]))
        .sort((a, b) => a - b);
      const yearMin = Math.min(...allYears), yearMax = Math.max(...allYears);
      const x = yr => left + (W - left - right) * ((yr - yearMin) / Math.max(yearMax - yearMin, 1));
      // each series is normalised to its own max |β| so both fit a [-1, 1] vertical band
      function normalize(rows) {
        if (!rows.length) return { rows: [], scale: 1 };
        const maxAbs = Math.max(...rows.map(r => Math.abs(+r.beta)), 1e-9);
        return { rows: rows.map(r => ({ ...r, beta_n: (+r.beta) / maxAbs })), scale: maxAbs };
      }
      const lci = normalize(rowsLci);
      const emp = normalize(rowsEmp);
      const yMin = -1.15, yMax = 1.15;
      const y = v => top + (H - top - bottom) * (1 - (v - yMin) / (yMax - yMin));
      function seriesPath(arr, key) {
        if (!arr.length) return '';
        let buf = '';
        arr.forEach((r, i) => {
          buf += `${i === 0 ? 'M' : 'L'}${x(+r.year).toFixed(1)},${y(r[key]).toFixed(1)} `;
        });
        return buf.trim();
      }
      function seriesDots(arr, key, color, sigColor) {
        return arr.map(r => {
          const sig = +r.p < 0.05;
          const fill = sig ? sigColor : color;
          const radius = sig ? 5 : 3.6;
          const tip = `${r.year} &middot; β = ${formatCoefficient(r.beta, 4)} &middot; p = ${formatP(r.p)}<br>${sig ? '<b>significant</b> at p&lt;0.05' : 'not significant'}`;
          return `<circle cx="${x(+r.year).toFixed(1)}" cy="${y(r[key]).toFixed(1)}" r="${radius}" fill="${fill}" stroke="#fff" stroke-width="1.6" data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()"></circle>`;
        }).join('');
      }
      const yearLabels = allYears.map(yr =>
        `<text x="${x(yr).toFixed(1)}" y="${H - 28}" text-anchor="middle" class="axis-text" ${yr >= 2020 ? 'style="font-weight:700;fill:var(--accent-2-deep)"' : ''}>${yr}</text>`
      ).join('');
      const refLine = `<line x1="${x(2019).toFixed(1)}" y1="${top}" x2="${x(2019).toFixed(1)}" y2="${H - bottom}" stroke="var(--ink-strong)" stroke-width="1" stroke-dasharray="4 3"></line>
        <text x="${x(2019).toFixed(1)}" y="${H - 12}" text-anchor="middle" class="axis-text" style="font-weight:700">2019 reference</text>`;
      const zeroY = y(0);
      const legend = `<g transform="translate(${left}, ${top - 16})" font-family="-apple-system,sans-serif" font-size="11.5">
        <circle cx="6" cy="0" r="4" fill="var(--accent-2)"></circle>
        <text x="14" y="4" fill="var(--ink)" font-weight="700">LCI (wage-based, scale ${lci.scale.toFixed(3)})</text>
        <circle cx="240" cy="0" r="4" fill="var(--accent)"></circle>
        <text x="248" y="4" fill="var(--ink)" font-weight="700">LFS (employment-based, scale ${emp.scale.toFixed(2)})</text>
      </g>`;
      el.innerHTML = `<svg viewBox="0 0 ${W} ${H}">
        <line x1="${left}" y1="${zeroY}" x2="${W - right}" y2="${zeroY}" stroke="#1f2933" stroke-width="1.2" stroke-dasharray="6 3"></line>
        <text x="${W - right - 4}" y="${zeroY - 4}" text-anchor="end" class="axis-text" style="font-weight:700">zero / placebo</text>
        ${refLine}
        ${rowsLci.length ? `<path d="${seriesPath(lci.rows, 'beta_n')}" fill="none" stroke="var(--accent-2)" stroke-width="1.8" opacity=".7"></path>` : ''}
        ${rowsEmp.length ? `<path d="${seriesPath(emp.rows, 'beta_n')}" fill="none" stroke="var(--accent)" stroke-width="1.8" opacity=".7"></path>` : ''}
        ${seriesDots(lci.rows, 'beta_n', 'var(--accent-2-deep)', 'var(--accent-2)')}
        ${seriesDots(emp.rows, 'beta_n', '#a8b8be', 'var(--accent)')}
        ${yearLabels}
        ${legend}
        <text x="${left - 44}" y="${top - 4}" class="axis-text" style="font-weight:700">β/max|β|</text>
      </svg>`;
    }

    const NATURAL_UNITS = {
      rating_10:        { label: '+1 Erasmusu rating point', mult: 1 },
      gdp_gap_usd_wb:   { label: '+$10,000 GDP-per-capita gap', mult: 10000 },
      earnings_gap:     { label: '+€1,000 net salary gap (robustness)', mult: 1 },
      price_level_gap:  { label: '+1 price-level index point (robustness)', mult: 1 },
      log_distance:     { label: 'doubling distance',         mult: Math.log(2) },
      same_language:    { label: 'shared language family',    mult: 1 },
      inst_quality:     { label: '+10 QS score points',       mult: 10 },
      life_satisfaction:{ label: '+1 life-satisfaction point',mult: 1 },
      edu_spend_gdp:    { label: '+1 pp of GDP on education', mult: 1 },
      best_score:       { label: '+10 QS score points',       mult: 10 },
      covid_post:       { label: '+1 pp harder LCI hit (post-2020)', mult: 1 },
      covid_emp_post:   { label: '+1 pp harder employment hit (post-2020)', mult: 1 },
      user_inst_quality:{ label: '+1 user-rating point',      mult: 1 },
      qol_city:         { label: '+1 city QoL point',         mult: 1 },
      qol_combined:     { label: '+1 combined-QoL point',     mult: 1 },
      qol_erasmusu:     { label: '+1 Erasmusu rating point',  mult: 1 },
      qol_reddit:       { label: '+1 Reddit-sentiment point', mult: 1 },
    };
    const PANEL_UNITS = {
      'Panel time-varying: Quality of life':         { label: '+1 life-satisfaction point' },
      'Panel time-varying: Education spending':      { label: '+1 percentage-point of GDP' },
      'Panel time-varying: Institution quality':     { label: '+10 QS score points', mult: 10 },
    };
    function naturalEffectText(term, beta) {
      const u = NATURAL_UNITS[term];
      if (!u) return '';
      const pct = (Math.exp(beta * u.mult) - 1) * 100;
      return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% per ${u.label}`;
    }
    function panelEffectText(specKey, beta) {
      const u = PANEL_UNITS[specKey];
      if (!u) return '';
      const mult = u.mult || 1;
      const pct = (Math.exp(beta * mult) - 1) * 100;
      return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% per ${u.label}`;
    }

    function fillBetaEffectCards() {
      const byVar = new Map();
      modelCoefficients.forEach(c => { byVar.set(String(c.variable || '').trim(), c); });
      document.querySelectorAll('[data-coef-card]').forEach(card => {
        const key = card.getAttribute('data-coef-card');
        if (key === 'COVID DiD') return;  // filled by fillCovidDiDCard
        // Panel time-varying cards live in regressionResults, keyed by spec
        let c, isPanel = false;
        if (key === 'Two-stage CITY: Erasmusu rating') {
          const r = regressionResults.find(rr => rr.spec === key);
          if (r) c = {beta:r.beta, p:r.p, term:r.term, se:r.se};
        } else if (key.startsWith('Panel time-varying')) {
          isPanel = true;
          const r = regressionResults.find(rr => String(rr.spec || '').startsWith(key));
          if (r) c = { beta: r.beta, p: r.p, term: null, note: r.note };
        } else {
          c = [...byVar.entries()].find(([k]) => k.startsWith(key))?.[1];
        }
        const valBox = card.querySelector('.value .v-num');
        const row = card.querySelector('.effect-row');
        if (!c || c.beta == null) {
          if (valBox) { valBox.textContent = 'planned'; valBox.className = 'v-num pln'; }
          if (row) row.innerHTML = `<span class="sig-tag pln">not estimated</span>`;
          return;
        }
        const beta = +c.beta, p = c.p == null ? null : +c.p;
        const se = c.se == null ? null : Number(c.se);
        const sig = p != null && p < 0.05;
        if (valBox) {
          valBox.textContent = (beta >= 0 ? '+' : '') + formatCoefficient(beta);
          valBox.className = 'v-num ' + (sig ? 'sig' : 'nsg');
        }
        const eff = key === 'Two-stage CITY: Erasmusu rating' ? `${formatCoefficient(beta)} log-attractiveness units per rating point` : isPanel ? panelEffectText(key, beta) : naturalEffectText(c.term, beta);
        const cleanedNote = c.note ? String(c.note).replace(/,?\\s*per[-\\s]SD[^,;]*/i, '').trim() : '';
        const noteText = (!eff && cleanedNote) ? cleanedNote : '';
        if (row) {
          row.innerHTML = `
            ${se != null ? `<span>SE <b>${formatCoefficient(se)}</b></span>` : ''}
            <span>p <b>${formatP(p)}</b></span>
            ${eff ? `<span>effect <b>${eff}</b></span>` : ''}
            ${noteText ? `<span>${escapeHtml(noteText)}</span>` : ''}
            <span class="sig-tag ${sig ? 'sig' : 'nsg'}">${sig ? 'sig p&lt;.05' : 'n.s.'}</span>
          `;
        }
      });
    }

    function renderCoeffs() {
      const el = document.getElementById('coeffTable');
      if (!el) return;
      if (!modelCoefficients.length) { el.innerHTML = '<p class="note">No coefficients yet. Run scripts/run_regression.py.</p>'; return; }
      const body = orderedCoefficients().map(c => {
        const planned = c.beta === null || c.beta === undefined;
        const sig = !planned && c.p < 0.05;
        const beta = planned ? '&mdash;' : formatCoefficient(c.beta, 4);
        const pCell = planned ? '<span class="note">planned</span>'
          : (sig ? `<strong style="color:var(--accent)">${formatP(c.p)}</strong>` : formatP(c.p));
        let eff = '';
        if (!planned) {
          const txt = naturalEffectText(c.term, +c.beta);
          eff = txt || '';
        }
        return `<tr>
          <td><strong>${escapeHtml(c.symbol)}</strong></td>
          <td>${escapeHtml(c.variable)}</td>
          <td>${beta}</td>
          <td>${pCell}</td>
          <td>${eff}</td>
          <td>${escapeHtml(c.expected_sign || '')}</td>
        </tr>`;
      }).join('');
      el.innerHTML = `<table class="data-table">
        <thead><tr><th>&beta;</th><th>Variable</th><th>Estimate</th><th>p</th><th>Natural-unit effect</th><th>Expected</th></tr></thead>
        <tbody>${body}</tbody></table>`;
    }

    const HEADLINE_SPECS = new Set([
      'Spec H: Erasmusu PPML (cross-sectional)',
      'Spec J-main: headline gravity (gdp_gap only, no salary/price)',
      'Two-stage CITY: Erasmusu rating',
      'Panel time-varying: Quality of life (OWID life satisfaction, time-varying)',
      'Panel time-varying: Institution quality (QS multi-year)',
      'COVID DiD (employment): sector hit x post-2020',
    ]);
    function specNaturalEff(r) {
      if (String(r.spec).startsWith('Two-stage')) return `${formatCoefficient(r.beta)} log-attractiveness units per QoL point`;
      const beta = +r.beta;
      if (!isFinite(beta)) return '';
      const u = NATURAL_UNITS[r.term];
      if (u) {
        const pct = (Math.exp(beta * u.mult) - 1) * 100;
        return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% per ${u.label}`;
      }
      return '';
    }
    function specRowHtml(r, idx) {
      const sig = r.p < 0.05;
      const pCell = sig ? `<strong style="color:var(--accent)">${formatP(r.p)}</strong>` : formatP(r.p);
      const cleanNote = r.note ? String(r.note).replace(/,?\\s*per[-\\s]SD[^,;]*/i, '').trim() : '';
      const eff = specNaturalEff(r);
      const detailRow = `<tr class="spec-detail" id="spec-detail-${idx}" style="display:none"><td colspan="6">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;padding:6px 2px 2px">
          <div><b>Term</b><div>${escapeHtml(r.term || '—')}</div></div>
          <div><b>&beta;</b><div>${formatCoefficient(r.beta, 4)}</div></div>
          <div><b>p</b><div>${pCell}</div></div>
          <div><b>N</b><div>${fmtInt(r.n)}</div></div>
          ${eff ? `<div><b>Natural-unit effect</b><div>${eff}</div></div>` : ''}
          <div><b>Estimator</b><div>${escapeHtml(r.kind)}</div></div>
        </div>
        ${cleanNote ? `<div class="note" style="margin-top:8px">${escapeHtml(cleanNote)}</div>` : ''}
      </td></tr>`;
      return `<tr class="spec-row" data-detail="spec-detail-${idx}" style="cursor:pointer">
        <td>${escapeHtml(r.spec)}</td>
        <td>${escapeHtml(r.kind)}</td>
        <td>${formatCoefficient(r.beta)}</td>
        <td>${pCell}</td>
        <td>${fmtInt(r.n)}</td>
        <td>${eff ? `<span>${eff}</span>` : `<span class="note">${escapeHtml(cleanNote)}</span>`}</td>
      </tr>${detailRow}`;
    }
    function renderResults() {
      const el = document.getElementById('resultsTable');
      if (!el) return;
      if (!regressionResults.length) { el.innerHTML = '<p class="note">No results yet. Run scripts/run_regression.py.</p>'; return; }
      const headline = [], other = [];
      regressionResults.forEach((r, i) => (HEADLINE_SPECS.has(r.spec) ? headline : other).push({ r, i }));
      const head = `<thead><tr><th>Specification</th><th>Estimator</th><th>&beta;</th><th>p</th><th>N</th><th>Effect</th></tr></thead>`;
      const headlineBody = headline.map(x => specRowHtml(x.r, x.i)).join('');
      const otherBody = other.map(x => specRowHtml(x.r, x.i)).join('');
      el.innerHTML = `
        <p class="note" style="margin:0 0 8px"><b>Click any row</b> for its term, estimate, p-value, sample size and estimator.</p>
        <table class="data-table">${head}<tbody>${headlineBody}</tbody></table>
        ${other.length ? `<details style="margin-top:12px"><summary style="cursor:pointer;font-weight:700;color:var(--accent-deep)">More robustness specs (${other.length})</summary>
          <table class="data-table" style="margin-top:8px">${head}<tbody>${otherBody}</tbody></table></details>` : ''}
      `;
      el.querySelectorAll('.spec-row').forEach(tr => {
        tr.addEventListener('click', () => {
          const det = document.getElementById(tr.dataset.detail);
          if (det) det.style.display = det.style.display === 'none' ? 'table-row' : 'none';
        });
      });
    }

    function renderYearChart() {
      const el = document.getElementById('yearChart');
      if (!el) return;
      if (!panelYears.length) { el.innerHTML = '<p class="note">No panel year effects.</p>'; return; }
      const rows = [...panelYears].sort((a, b) => a.year - b.year);
      const W = 760, H = 260, left = 56, right = 16, top = 28, bottom = 36;
      const vals = rows.map(r => +r.year_fe);
      const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
      const x = i => left + (W - left - right) * (i / Math.max(rows.length - 1, 1));
      const y = v => top + (H - top - bottom) * (1 - (v - lo) / ((hi - lo) || 1));
      const path = rows.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(+r.year_fe).toFixed(1)}`).join(' ');
      const covidIdx = rows.findIndex(r => r.year === 2020);
      const dots = rows.map((r, i) => {
        const covid = r.year === 2020;
        const yv = (+r.year_fe).toFixed(2);
        const tip = `${r.year} &middot; year FE = ${yv}<br>(${(+r.year_fe >= 0 ? '+' : '') + ((Math.exp(+r.year_fe) - 1) * 100).toFixed(1)}% vs 2014 baseline)`;
        return `<circle cx="${x(i).toFixed(1)}" cy="${y(+r.year_fe).toFixed(1)}" r="${covid ? 5.5 : 3.8}" fill="${covid ? 'var(--accent-2)' : 'var(--accent)'}" data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()"></circle>
          <text x="${x(i).toFixed(1)}" y="${H - 16}" text-anchor="middle" class="axis-text">${r.year}</text>`;
      }).join('');
      const zeroY = y(0);
      const covidLine = covidIdx >= 0 ? `<line x1="${x(covidIdx).toFixed(1)}" y1="${top}" x2="${x(covidIdx).toFixed(1)}" y2="${H - bottom}" stroke="var(--accent-2)" stroke-width="1" stroke-dasharray="3 3" opacity=".6"></line>
        <text x="${x(covidIdx).toFixed(1)}" y="${top - 8}" text-anchor="middle" class="axis-text" style="fill:var(--accent-2);font-weight:700">COVID</text>` : '';
      const tickVals = [lo, (lo + hi) / 2, hi];
      const ticks = tickVals.map(v => `<text x="${left - 6}" y="${y(v) + 4}" text-anchor="end" class="axis-text">${v.toFixed(1)}</text>
        <line x1="${left}" y1="${y(v).toFixed(1)}" x2="${W - right}" y2="${y(v).toFixed(1)}" stroke="#e7ebef" stroke-width="1"></line>`).join('');
      el.innerHTML = `<svg viewBox="0 0 ${W} ${H}">
        ${ticks}
        <line x1="${left}" y1="${zeroY}" x2="${W - right}" y2="${zeroY}" stroke="#1f2933" stroke-width="1.2" stroke-dasharray="6 3"></line>
        <text x="${W - right - 4}" y="${zeroY - 4}" text-anchor="end" class="axis-text" style="font-weight:700">2014 baseline</text>
        ${covidLine}
        <path d="${path}" fill="none" stroke="var(--accent)" stroke-width="2.4"></path>
        ${dots}
        <text x="${left - 44}" y="${top + 4}" class="axis-text" style="font-weight:700">log change vs 2014</text>
      </svg>`;
    }

    function renderHeatmap() {
      const order = countries.filter(country => country.total > 0).slice(0, 30);
      const codes = order.map(country => country.code);
      const byPair = new Map(flows.map(row => [`${row.sending_code}|${row.receiving_code}`, row]));
      const max = Math.max(...flows.filter(row => codes.includes(row.sending_code) && codes.includes(row.receiving_code)).map(row => row.flow_count), 1);
      const cell = 18, left = 26, top = 64, width = left + codes.length * cell + 8, height = top + codes.length * cell + 24;
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

    function renderRedditCoverage() {
      const el = document.getElementById('redditCoverage');
      if (!el) return;
      const m = redditMeta || {};
      if (!m.earliestUtc || !m.latestUtc) { el.textContent = ''; return; }
      const fmt = (u) => new Date(u * 1000).toISOString().slice(0, 10);
      const corpStart = fmt(m.earliestUtc);
      const corpEnd = fmt(m.latestUtc);
      const inN = m.inWindowCount != null ? m.inWindowCount : m.mentions;
      el.textContent = `Coverage: ${corpStart} → ${corpEnd} · ${inN} mentions · 15y EWMA half-life 1y`;
      const dropped = (m.droppedFuture || 0) + (m.droppedOld || 0);
      const dropMsg = dropped ? `\nDropped ${dropped} outside 15-year window.` : '';
      el.title = `Reddit r/Erasmus text layer:\n• Coverage: ${corpStart} → ${corpEnd}\n• Lookback: 15 years back from build time\n• EWMA half-life: 1 year — recent posts dominate, older opinions carry residual weight${dropMsg}`;
    }

    function renderRedditTable() {
      if (!redditByCountry.length) {
        document.getElementById('redditTable').innerHTML = '<p class="note">No extracted mentions found. Run scripts/extract_reddit.py first.</p>';
        return;
      }
      const filtered = redditByCountry.filter(r => (+r.mentions || 0) >= REDDIT_MIN_MENTIONS);
      const sorted = sortRows(filtered, redditSort);
      const total = sorted.length;
      const visible = redditExpanded ? sorted : sorted.slice(0, REDDIT_TOP_N);
      const effSum = sorted.reduce((s, r) => s + (+r.effectiveMentions || 0), 0);
      const caption = `<p class="note" style="margin:0 0 8px"><strong>Showing destinations with &ge;${REDDIT_MIN_MENTIONS} Reddit mentions.</strong> n = ${total}. Weighted-net uses age-decay (1y half-life); effective n &approx; ${effSum.toFixed(0)}.</p>`;
      const toggleLabel = redditExpanded
        ? `Show top ${REDDIT_TOP_N}`
        : `Show more (${Math.max(total - REDDIT_TOP_N, 0)})`;
      const toggleHtml = total > REDDIT_TOP_N
        ? `<div style="margin:8px 0 0"><button id="redditToggle" type="button" class="pill-toggle">${toggleLabel}</button></div>`
        : '';
      const body = visible.map(row => `<tr>
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
      document.getElementById('redditTable').innerHTML = `${caption}<table class="data-table">
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
        </tr></thead><tbody>${body}</tbody></table>${toggleHtml}`;
      const tbtn = document.getElementById('redditToggle');
      if (tbtn) tbtn.addEventListener('click', () => { redditExpanded = !redditExpanded; renderRedditTable(); });
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

    function outUniQ() { return norm(outUniSearch ? outUniSearch.value : ''); }
    function inCountryQ() { return norm(inCountrySearch ? inCountrySearch.value : ''); }
    function inUniQ() { return norm(inUniSearch ? inUniSearch.value : ''); }

    function rowMatchesEndpointFilters(row) {
      const ou = outUniQ();
      if (ou && !(norm(row.sending_org).includes(ou) || norm(row.sending_city).includes(ou))) return false;
      const ic = inCountryQ();
      if (ic && !(norm(row.receiving_country).includes(ic) || norm(row.receiving_code).includes(ic))) return false;
      const iu = inUniQ();
      if (iu && !(norm(row.receiving_org).includes(iu) || norm(row.receiving_city).includes(iu))) return false;
      return true;
    }

    function pointMatchesEndpointFilters(point) {
      const ou = outUniQ();
      if (ou) {
        const hay = `${point.so || ''} ${point.sc || ''}`;
        if (!norm(hay).includes(ou)) return false;
      }
      const ic = inCountryQ();
      if (ic) {
        const hay = `${point.n || ''} ${point.dc || ''}`;
        if (!norm(hay).includes(ic)) return false;
      }
      const iu = inUniQ();
      if (iu) {
        const hay = `${point.o || ''} ${point.c || ''}`;
        if (!norm(hay).includes(iu)) return false;
      }
      return true;
    }

    function currentOrgRows() {
      const level = orgLevelSelect.value;
      return (orgFlowTables[level] || [])
        .filter(row => row.sending_code === senderSelect.value)
        .filter(rowMatchesEndpointFilters)
        .sort((a, b) => b.flow_count - a.flow_count);
    }

    function populateOrgOptions() {
      const level = orgLevelSelect.value;
      const rows = (orgFlowTables[level] || [])
        .filter(row => mapViewSelect.value === 'all' || row.sending_code === senderSelect.value);
      const outUni = new Set();
      const inCountry = new Set();
      const inUni = new Set();
      rows.forEach(row => {
        if (row.sending_org) outUni.add(String(row.sending_org).trim());
        if (row.sending_city) outUni.add(String(row.sending_city).trim());
        if (row.receiving_country) inCountry.add(`${row.receiving_code} - ${row.receiving_country}`.trim());
        if (row.receiving_org) inUni.add(String(row.receiving_org).trim());
        if (row.receiving_city) inUni.add(String(row.receiving_city).trim());
      });
      const fill = (el, set, cap) => {
        if (!el) return;
        el.innerHTML = [...set].filter(Boolean).sort((a, b) => a.localeCompare(b)).slice(0, cap)
          .map(v => `<option value="${escapeHtml(v)}"></option>`).join('');
      };
      fill(outUniOptions, outUni, 1200);
      fill(inCountryOptions, inCountry, 200);
      fill(inUniOptions, inUni, 1200);
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
      const points = view === 'all'
        ? levelRecords.all
        : levelRecords.points.filter(point => point.s === senderSelect.value);
      const filteredPoints = points.filter(pointMatchesEndpointFilters);
      document.getElementById('mapNote').textContent = mapNotes[level];
      const empty = !filteredPoints.length;
      document.getElementById('mapEmpty').hidden = !empty;
      document.querySelector('#sec-map .map-legend').hidden = empty;
      document.getElementById('map').hidden = empty;
      if (empty) return;
      map.invalidateSize();
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
      const active = [
        outUniSearch && outUniSearch.value ? `out uni: "${outUniSearch.value}"` : null,
        inCountrySearch && inCountrySearch.value ? `in country: "${inCountrySearch.value}"` : null,
        inUniSearch && inUniSearch.value ? `in uni: "${inUniSearch.value}"` : null,
      ].filter(Boolean);
      const filteredText = active.length ? ` (${active.join(', ')})` : '';
      const note = `Showing ${rows.length} ${orgLevelLabels[level]} rows${filteredText} for the selected outgoing country. Organization names come from the Erasmus KA1 file and are normalized only lightly.`;
      document.getElementById('orgFlowNote').textContent = note;
      if (!rows.length) {
        document.getElementById('orgFlowTable').innerHTML = '<p class="note">No university-level flows match this country and the active endpoint filters.</p>';
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

    const TREND_COLORS = ['#2f6f73', '#b44e5a', '#c98a2b', '#4a6fa5', '#63716d', '#a1aaa6'];
    const trendYears = [...new Set(timeSeries.map(row => row.y))].sort((a, b) => a - b);

    function lineChartSvg(series, years) {
      const width = Math.max(280, Math.min(520, document.getElementById('trendTotal').clientWidth)), height = width < 400 ? 220 : 300, left = 54, right = 16, top = 16, bottom = 34;
      const maxY = Math.max(1, ...series.flatMap(s => s.points.map(p => p.y)));
      const minX = years[0], maxX = years[years.length - 1];
      const px = x => scale(x, minX, maxX, left, width - right);
      const py = y => scale(y, 0, maxY, height - bottom, top);
      let grid = '';
      for (let i = 0; i <= 4; i++) {
        const v = maxY * i / 4;
        const yy = py(v);
        grid += `<line x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}" stroke="var(--line)" stroke-width="1"></line>`;
        grid += `<text x="${left - 6}" y="${yy + 4}" text-anchor="end" class="axis-text">${fmtInt(v)}</text>`;
      }
      const xlabels = years.filter((yr,i) => width >= 400 || i % 3 === 0 || i === years.length-1).map(yr =>
        `<text x="${px(yr)}" y="${height - bottom + 18}" text-anchor="middle" class="axis-text">${yr}</text>`
      ).join('');
      const lines = series.map(s => {
        const d = s.points.map((p, i) => `${i ? 'L' : 'M'}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join(' ');
        const dots = s.points.map(p =>
          `<circle cx="${px(p.x).toFixed(1)}" cy="${py(p.y).toFixed(1)}" r="3" fill="${s.color}" data-tip="${escapeHtml(s.label)} ${p.x}<br><strong>${fmtInt(p.y)}</strong> students" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()"></circle>`
        ).join('');
        return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"></path>${dots}`;
      }).join('');
      return `<svg viewBox="0 0 ${width} ${height}" role="img">${grid}${xlabels}${lines}</svg>`;
    }

    function legendHtml(series) {
      return '<div class="trend-legend">' + series.map(s =>
        `<span><span class="legend-swatch" style="background:${s.color}"></span>${escapeHtml(s.label)}</span>`
      ).join('') + '</div>';
    }

    function renderTrendTotal() {
      const el = document.getElementById('trendTotal');
      if (!timeSeries.length) { el.innerHTML = '<p class="note">No panel data.</p>'; return; }
      const byYear = new Map(trendYears.map(y => [y, 0]));
      timeSeries.forEach(row => byYear.set(row.y, byYear.get(row.y) + row.f));
      const series = [{ label: 'All countries', color: '#2f6f73', points: trendYears.map(y => ({ x: y, y: byYear.get(y) })) }];
      el.innerHTML = lineChartSvg(series, trendYears);
    }

    function renderTrendSender(code) {
      const el = document.getElementById('trendSender');
      const title = document.getElementById('trendSenderTitle');
      const selected = countries.find(country => country.code === code);
      if (title) title.innerHTML = (selected ? escapeHtml(selected.country) : 'Selected country') + ' &mdash; top destinations';
      const rows = timeSeries.filter(row => row.s === code);
      if (!rows.length) { el.innerHTML = '<p class="note">No panel data for this country.</p>'; return; }
      const totals = new Map();
      const names = new Map();
      rows.forEach(row => { totals.set(row.d, (totals.get(row.d) || 0) + row.f); names.set(row.d, row.dn); });
      const topDest = [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(entry => entry[0]);
      const series = topDest.map((d, i) => {
        const byYear = new Map(trendYears.map(y => [y, 0]));
        rows.filter(row => row.d === d).forEach(row => byYear.set(row.y, byYear.get(row.y) + row.f));
        return { label: names.get(d) || d, color: TREND_COLORS[i % TREND_COLORS.length], points: trendYears.map(y => ({ x: y, y: byYear.get(y) })) };
      });
      el.innerHTML = lineChartSvg(series, trendYears) + legendHtml(series);
    }

    function updateCountry() {
      const rows = senderRowsFiltered(senderSelect.value);
      const total = rows.reduce((sum, row) => sum + row.flow_count, 0);
      const selected = countries.find(country => country.code === senderSelect.value);
      const uniLabel = (typeof outUniSearch !== 'undefined' && outUniSearch && outUniSearch.value) ? ` · uni filter: <em>${escapeHtml(outUniSearch.value)}</em>` : '';
      document.getElementById('topStat').innerHTML = selected
        ? `Currently showing <b>${escapeHtml(selected.country)}</b> · ${fmtInt(total)} outgoing students${uniLabel}`
        : '';
      document.getElementById('briefCountry').textContent = selected ? selected.country : senderSelect.value;
      document.getElementById('briefTotal').textContent = fmtInt(total);
      const destinations = new Map();
      rows.forEach(row => {
        const key = row.receiving_country || row.receiving_code;
        destinations.set(key, (destinations.get(key) || 0) + row.flow_count);
      });
      const leading = [...destinations].sort((a, b) => b[1] - a[1]).slice(0, 3);
      document.getElementById('briefDestinations').innerHTML = leading.length
        ? leading.map(([name, count]) => `<div class="brief-destination"><div><span>${escapeHtml(name)}</span><b>${fmtPct(total ? count / total : 0)}</b></div><div class="brief-track"><span style="width:${total ? count / total * 100 : 0}%"></span></div></div>`).join('')
        : '<p class="note">No outgoing flows match the current filters.</p>';
      const chipLabel = selected ? selected.country : senderSelect.value;
      document.querySelectorAll('.filter-chip .fc-country').forEach(node => {
        node.textContent = chipLabel;
      });
      renderSummary(rows);
      renderBar(rows);
      renderScatter(rows);
      renderDestinationTable(rows);
      renderTrendSender(senderSelect.value);
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
      earnCountrySelect.value = seen.has('IT') ? 'IT' : (seen.has('ES') ? 'ES' : options[0][0]);
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
      const width = Math.max(300, document.getElementById('earningsChart').clientWidth), rowH = 30, left = width < 500 ? 140 : 240, right = 65;
      const height = 30 + reversed.length * rowH;
      const max = Math.max(...reversed.map(row => row[unit]), 1);
      const unitLabel = unit === 'eur' ? 'EUR' : 'PPS';
      const bars = reversed.map((row, i) => {
        const y = 16 + i * rowH;
        const w = scale(row[unit], 0, max, 0, width - left - right);
        const tip = `${escapeHtml(row.label)}<br>${fmtMoney(row[unit])} ${unitLabel}/month`;
        return `<g data-tip="${tip}" onmousemove="showTip(event, this.dataset.tip)" onmouseleave="hideTip()">
          <text x="${left - 8}" y="${y + 14}" text-anchor="end" class="axis-text">${escapeHtml(row.label.length > (width < 500 ? 20 : 38) ? row.label.slice(0, width < 500 ? 19 : 37) + '…' : row.label)}</text>
          <rect class="bar" x="${left}" y="${y}" width="${w}" height="17" rx="3"></rect>
          <text x="${left + w + 6}" y="${y + 13}" class="axis-text">${fmtMoney(row[unit])}</text>
        </g>`;
      }).join('');
      document.getElementById('earningsChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${bars}</svg>`;
    }

    function setMode(mode) {
      document.body.classList.toggle('mode-free', mode === 'free');
      document.body.classList.toggle('mode-explore', mode === 'explore');
      document.getElementById('m-free')?.classList.toggle('active', mode === 'free');
      document.getElementById('m-explore')?.classList.toggle('active', mode === 'explore');
      try { localStorage.setItem('eg-mode', mode); } catch (err) {}
    }

    document.getElementById('m-free')?.addEventListener('click', () => setMode('free'));
    document.getElementById('m-explore')?.addEventListener('click', () => setMode('explore'));
    try {
      const savedMode = localStorage.getItem('eg-mode');
      if (savedMode === 'explore') setMode('explore');
    } catch (err) {}

    window.addEventListener('scroll', () => {
      document.querySelector('.topbar')?.classList.toggle('stuck', window.scrollY > 6);
    }, { passive: true });

    document.getElementById('summaryCards')?.addEventListener('click', event => {
      const card = event.target.closest('.card');
      if (!card) return;
      if (card.dataset.chartable === '0') return;
      card.classList.toggle('open');
    });

    (function setupNavToggle() {
      const toggle = document.getElementById('navToggle');
      const nav = document.getElementById('primaryNav');
      if (!toggle || !nav) return;
      const close = () => { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); };
      toggle.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    })();


    document.getElementById('resetControls')?.addEventListener('click', () => {
      if (outUniSearch) outUniSearch.value = '';
      if (inCountrySearch) inCountrySearch.value = '';
      if (inUniSearch) inUniSearch.value = '';
      mapViewSelect.value = 'sender';
      orgLevelSelect.value = 'countryUni';
      const btn = document.getElementById('mapViewAll');
      if (btn) { btn.classList.remove('on'); btn.textContent = ' All outgoing countries'; }
      setCountry(countries.find(c => c.code === 'IT') ? 'IT' : senderSelect.options[0].value);
      autoPickLevel();
      updateFilterChip();
      populateOrgOptions();
      renderOrgFlowTable();
      renderMap();
      renderEarnings();
    });

    populateSelect();
    wireSorting();
    renderTrendTotal();
    updateCountry();
    renderCoeffs();
    renderResults();
    renderYearChart();
    renderCovidEventStudy();
    fillBetaEffectCards();
    fillCovidDiDCard();
    renderHeatmap();
    renderWeightedTable();
    populateEarnCountries();
    renderEarnings();
    earnCountrySelect.addEventListener('change', renderEarnings);
    earnUnitSelect.addEventListener('change', renderEarnings);
    renderRedditTable();
    renderRedditCoverage();

    // Both navigation rows use the same section state and shared layout column.
    const NAV_GROUPS = {
      research: [
        {id:'sec-intro', label:'Overview'},
        {id:'sec-explanatory', label:'Explanatory variables'},
        {id:'sec-results', label:'Results'},
      ],
      model: [
        {id:'sec-overview', label:'Flows'},
        {id:'sec-salary', label:'GDP gap'},
        {id:'sec-reddit', label:'Quality of life'},
        {id:'sec-institution', label:'Institution quality'},
        {id:'sec-controls', label:'Controls'},
      ],
      extra: [
        {id:'sec-panel', label:'Panel'},
        {id:'sec-covid', label:'2020 shock'},
        {id:'sec-data', label:'Data & measurement'},
      ],
    };
    const SECTION_GROUP = {
      'sec-intro':'research','sec-explanatory':'research','sec-results':'research',
      'sec-flow-filters':'model','sec-overview':'model','sec-map':'model','sec-trends':'model',
      'sec-top-destinations':'model','sec-destination-table':'model','sec-heatmap':'model',
      'sec-controls':'model','sec-gdp-gap':'model','sec-economics':'model',
      'sec-salary':'model','sec-reddit':'model','sec-institution':'model',
      'sec-time':'extra','sec-panel':'extra','sec-covid':'extra','sec-data':'extra',
    };
    const SUBSECTION_FOR = {
      'sec-flow-filters':'sec-overview','sec-map':'sec-overview','sec-trends':'sec-overview',
      'sec-top-destinations':'sec-overview','sec-destination-table':'sec-overview','sec-heatmap':'sec-overview',
      'sec-gdp-gap':'sec-controls','sec-economics':'sec-controls','sec-time':'sec-panel',
    };
    let activeNavGroup = null, activeNavTopic = null;
    document.getElementById('dynSubnav').addEventListener('change', event => {
      if (event.target.id !== 'topicPicker') return;
      const link = document.querySelector(`#dynSubnav a[href="#${event.target.value}"]`);
      if (link) link.click();
    });
    function setActiveGroup(group, section) {
      document.querySelectorAll('.nav-main-link').forEach(link => {
        const active = link.dataset.group === group;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current','location');
        else link.removeAttribute('aria-current');
      });
      const topics = NAV_GROUPS[group] || [];
      const topic = SUBSECTION_FOR[section] || section || topics[0]?.id;
      if (group === activeNavGroup && topic === activeNavTopic) return;
      activeNavGroup = group; activeNavTopic = topic;
      const pickerNames = {'sec-explanatory':'Variables','sec-institution':'Institutions','sec-data':'Data & sources'};
      document.getElementById('dynSubnav').innerHTML = topics.map(item =>
        `<a class="sub-link${item.id === topic ? ' active' : ''}" href="#${item.id}"${item.id === topic ? ' aria-current="location"' : ''}>${item.label}</a>`
      ).join('') + `<label class="topic-choice" for="topicPicker">Explore topic<select id="topicPicker">${topics.map(item => `<option value="${item.id}"${item.id === topic ? ' selected' : ''}>${pickerNames[item.id] || item.label}</option>`).join('')}</select></label>`;
    }
    function scrollSpy() {
      const ids = Object.keys(SECTION_GROUP);
      const offset = document.querySelector('.topbar').offsetHeight + 20;
      let bestId = null, bestDist = Infinity;
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        const top = el.getBoundingClientRect().top - offset;
        if (top <= 0 && -top < bestDist) { bestDist = -top; bestId = id; }
      }
      if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) bestId = 'sec-data';
      if (!bestId) bestId = ids[0];
      const group = SECTION_GROUP[bestId];
      setActiveGroup(group, bestId);
    }
    window.addEventListener('scroll', scrollSpy, { passive: true });
    window.addEventListener('resize', scrollSpy);
    scrollSpy();

    function applyDestView(view) {
      const segBtns = document.querySelectorAll('.seg-btn[data-view]');
      segBtns.forEach(b => {
        const on = b.dataset.view === view;
        b.classList.toggle('on', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      const destTable = document.getElementById('destinationTable');
      const orgTable = document.getElementById('orgFlowTable');
      const orgNote = document.getElementById('orgFlowNote');
      if (view === 'country') {
        if (destTable) destTable.style.display = '';
        if (orgTable) orgTable.style.display = 'none';
        if (orgNote) orgNote.style.display = 'none';
      } else {
        if (destTable) destTable.style.display = 'none';
        if (orgTable) orgTable.style.display = '';
        if (orgNote) orgNote.style.display = '';
        if (orgLevelSelect.value !== view) orgLevelSelect.value = view;
        populateOrgOptions();
        renderOrgFlowTable();
      }
      try { localStorage.setItem('destView', view); } catch (e) {}
    }
    document.querySelectorAll('.seg-btn[data-view]').forEach(b => {
      b.addEventListener('click', () => applyDestView(b.dataset.view));
    });
    function applyDestFilter() {
      const q = (document.getElementById('destTableFilter')?.value || '').toLowerCase().trim();
      ['destinationTable','orgFlowTable'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.querySelectorAll('tbody tr').forEach(tr => {
          const text = tr.textContent.toLowerCase();
          tr.style.display = (!q || text.includes(q)) ? '' : 'none';
        });
      });
    }
    const _destFilterInput = document.getElementById('destTableFilter');
    if (_destFilterInput) _destFilterInput.addEventListener('input', applyDestFilter);
    const _destObserver = new MutationObserver(applyDestFilter);
    ['destinationTable','orgFlowTable'].forEach(id => {
      const el = document.getElementById(id);
      if (el) _destObserver.observe(el, { childList: true, subtree: true });
    });
    const savedDestView = (() => { try { return localStorage.getItem('destView'); } catch (e) { return null; } })();
    if (savedDestView && ['country','countryUni','uniCountry','uniUni'].includes(savedDestView)) {
      applyDestView(savedDestView);
    }

    orgLevelSelect.addEventListener('change', () => {
      populateOrgOptions();
      renderOrgFlowTable();
      renderMap();
    });
    mapViewSelect.addEventListener('change', () => {
      populateOrgOptions();
      renderMap();
    });
    function autoPickLevel() {
      const hasOut = !!(outUniSearch && outUniSearch.value);
      // outgoing uni alone -> uniUni (precise uni-to-uni map). incoming-only keeps countryUni.
      const level = hasOut ? 'uniUni' : 'countryUni';
      if (orgLevelSelect && orgLevelSelect.value !== level) orgLevelSelect.value = level;
    }
    const mapViewAllBtn = document.getElementById('mapViewAll');
    if (mapViewAllBtn) {
      mapViewAllBtn.addEventListener('click', () => {
        const next = mapViewSelect.value === 'all' ? 'sender' : 'all';
        mapViewSelect.value = next;
        mapViewAllBtn.classList.toggle('on', next === 'all');
        mapViewAllBtn.textContent = next === 'all' ? ' Showing all · click for one' : ' All outgoing countries';
        populateOrgOptions();
        renderMap();
      });
    }
    function updateFilterChip() {
      const chip = document.getElementById('flowFilterChip');
      if (!chip) return;
      const parts = [
        outUniSearch && outUniSearch.value ? `out: ${outUniSearch.value}` : null,
        inCountrySearch && inCountrySearch.value ? `to: ${inCountrySearch.value}` : null,
        inUniSearch && inUniSearch.value ? `in: ${inUniSearch.value}` : null,
      ].filter(Boolean);
      if (!parts.length) { chip.style.display = 'none'; return; }
      chip.style.display = '';
      chip.querySelector('.fc-active').textContent = parts.join(' · ');
    }
    [outUniSearch, inCountrySearch, inUniSearch].forEach(el => {
      if (!el) return;
      el.addEventListener('input', () => {
        autoPickLevel();
        updateFilterChip();
        populateOrgOptions();
        renderOrgFlowTable();
        renderMap();
        if (el === outUniSearch) updateCountry();
      });
    });

    const quickCountry = document.getElementById('quickCountry');
    quickCountry.value = countrySearch.value;
    quickCountry.addEventListener('change', () => {
      countrySearch.value = quickCountry.value;
      countrySearch.dispatchEvent(new Event('change', {bubbles:true}));
      quickCountry.value = countrySearch.value;
    });
    countrySearch.addEventListener('change', () => {quickCountry.value = countrySearch.value;});
    senderSelect.addEventListener('change', () => {quickCountry.value = countrySearch.value;});
    function updateNavOffset() {
      document.documentElement.style.setProperty('--nav-offset', `${document.querySelector('.topbar').offsetHeight + 16}px`);
    }
    new ResizeObserver(updateNavOffset).observe(document.querySelector('.topbar'));
    updateNavOffset();
    document.addEventListener('click', event => {
      const link = event.target.closest('a[href^="#"]');
      if (!link) return;
      const id = link.getAttribute('href').slice(1), target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      document.getElementById('primaryNav').classList.remove('open');
      document.getElementById('navToggle').setAttribute('aria-expanded','false');
      if (SECTION_GROUP[id]) setActiveGroup(SECTION_GROUP[id], id);
      updateNavOffset();
      target.scrollIntoView({behavior:'instant',block:'start'});
      history.replaceState(null,'','#'+id);
    });
    window.addEventListener('resize', () => {renderEarnings(); renderTrendTotal(); renderTrendSender(senderSelect.value);});

    autoPickLevel();
    updateFilterChip();
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
    import argparse
    import re
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT_PATH, help='Generated HTML destination')
    parser.add_argument('--snapshot', type=Path, help='Reuse the embedded analytical payload from a generated HTML file')
    args = parser.parse_args()
    if args.snapshot:
        snapshot = args.snapshot.read_text(encoding='utf-8')
        match = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', snapshot, re.S)
        if match is None:
            raise ValueError('Snapshot has no dashboard-data payload')
        output = render_dashboard(json.loads(match.group(1)))
    else:
        output = build_dashboard()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(args.output)



if __name__ == "__main__":
    main()
