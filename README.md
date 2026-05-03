# UniLife - Final Project

**Course:** Text Analysis for Economics  
**Deliverable:** `Palanca_Leonardo.zip` - notebook + report + raw/processed data

## Working Title

**Economic Attractiveness and Erasmus Mobility: A Descriptive Analysis of European Student Flows**

## Research Question

> How are Erasmus student mobility flows distributed across economic gaps between sending and receiving countries?

The project asks whether students from different origin countries tend to choose destinations that are richer, poorer, cheaper, more expensive, or economically similar to their home country.

This is a descriptive and exploratory project. It does **not** claim causal inference. The goal is to document patterns in official Erasmus mobility flows and connect them to economic indicators such as GDP per capita, wages, and cost of living.

## Core Data

The main backbone dataset is:

```text
data/raw/Erasmus-KA1-Mobility-Data-2022.xlsx
```

The main sheet is:

```text
KA1 mobilities 2022
```

The analysis filters this detailed KA1 file to Higher Education study mobilities:

- `Field == "Higher Education"`
- learner profile only
- study mobility activity only
- age 18+
- cross-border country pairs only

The annual report annex remains in `data/raw/` as a reference file.

## Unit of Analysis

The main dataset should be a country-pair table:

```text
sending_country, sending_code, receiving_country, receiving_code, flow_count
```

Then join country-level indicators:

```text
sender_gdp_per_capita
receiver_gdp_per_capita
gdp_gap = receiver_gdp_per_capita - sender_gdp_per_capita

sender_wage
receiver_wage
wage_gap = receiver_wage - sender_wage

sender_cost_of_living
receiver_cost_of_living
cost_gap = receiver_cost_of_living - sender_cost_of_living

distance_km
```

## Setup

This project uses `uv`.

```bash
uv sync
```

Then open:

```text
notebooks/unilife.ipynb
```

If needed, create a local environment file:

```bash
cp .env.example .env
```

Do not commit `.env`.

## Analysis Plan

1. Build the KA1 Higher Education study-flow table.
2. Add GDP, net earnings, and cost-of-living indicators.
3. Compute economic gaps between sending and receiving countries.
4. Add Higher Education grant-per-participant metrics from the annual annex.
5. Produce descriptive visualizations:
   - flow heatmap
   - Italy vs Luxembourg destination profiles
   - destination GDP/cost gap vs flow share
   - flow-weighted destination GDP/cost by sending country
6. Estimate a non-causal, gravity-style descriptive regression.

## Build Commands

```bash
.venv/bin/python scripts/build_flows.py
.venv/bin/python scripts/build_indicators.py
.venv/bin/python scripts/build_dashboard.py
```

The dashboard is generated at:

```text
dashboard/dist/index.html
```

It is deployed on the VM as:

```text
http://unilife.ellep.it
```

Current dashboard features:

- sending-country selector
- selected-country destination chart and GDP-gap scatter
- destination table sortable by flow count, flow share, GDP gap, price gap, and earnings gap
- same-order sending/receiving heatmap
- sortable flow-weighted destination economics table
- Higher Education grant-per-participant metric from the annual annex

VM deployment helpers:

```bash
./scripts/setup_unilife_nginx.sh
./scripts/deploy_dashboard.sh
```

Example descriptive model:

```text
log(1 + flow_ij) =
    beta1 * gdp_gap_ij
  + beta2 * cost_gap_ij
  + beta3 * distance_ij
  + sending_country fixed effects
  + receiving_country fixed effects
  + error_ij
```

## Optional Text Layer

If the official flow analysis is complete, add a course-relevant text extension:

- collect Reddit `r/Erasmus` posts/comments mentioning destinations
- use Gemini + Pydantic for structured extraction
- extract country/city, sentiment, and themes such as cost, housing, nightlife, academics, safety, and bureaucracy
- manually label 40-50 mentions to evaluate extraction quality

This optional section connects the final project to the course's LLM information-extraction assignment.

## Repository Structure

```text
.
├── README.md
├── UNILIFE_PROJECT.md
├── pyproject.toml
├── requirements.txt
├── data/
│   ├── raw/
│   │   ├── Erasmus-KA1-Mobility-Data-2022.xlsx
│   │   ├── Erasmus-KA2-Mobility-Data.xlsx
│   │   └── annual-report-2024-statistical-annex.xlsx
│   └── processed/
├── dashboard/
│   └── dist/
│       └── index.html
├── notebooks/
│   └── unilife.ipynb
├── reports/
│   └── figures/
└── src/
    └── unilife/
```

## Current Position

Use the detailed KA1 Erasmus Excel file as the backbone of the project. Build the flow dataset first. Add Reddit and LLM extraction only after the flow/economic analysis is clean and reproducible.
