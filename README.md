# UniLife - Final Project

**Course:** Text Analysis for Economics  
**Deliverable:** `Palanca_Leonardo.zip` - notebook + report + raw/processed data

## Working Title

**Economic Attractiveness and Erasmus Mobility: A Descriptive Analysis of European Student Flows**

## Research Question

> What explains the size of Erasmus Higher Education mobility flows from one country to another?

We frame origin-to-destination choice as a gravity-style model in which flow size responds to the **salary gap**, **perceived quality of life**, **institution quality**, and **language affinity** between origin and destination, controlling for income, cost of living, and distance.

This is a descriptive and exploratory project. It does **not** claim causal inference. Per the grading rubric, the regression is the project's **step-3 design** (described, not estimated); the executed work is the spatial flow analysis plus the Reddit text layer.

### Model Design

| Term | Variable | Source | Status |
|------|----------|--------|--------|
| β₁ | salary gap | Eurostat net earnings | built |
| β₂ | quality of life | Reddit `r/Erasmus` sentiment/themes (Gemini + Pydantic) | planned (text layer) |
| β₃ | institution quality | university ranking score | planned |
| control | gdp gap, price-level gap, distance, language affinity | World Bank / Eurostat / distance / language groupings | built (distance + language planned) |

```text
log(1 + flow_ij) =
    beta1 * salary_gap_ij
  + beta2 * quality_of_life_j
  + beta3 * institution_quality_j
  + controls(gdp_gap_ij, price_level_gap_ij, distance_ij, language_affinity_ij)
  + sending_country fixed effects
  + receiving_country fixed effects
  + error_ij
```

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

The main analytical dataset is a country-pair table:

```text
sending_country, sending_code, receiving_country, receiving_code, flow_count
```

For the dashboard, the same KA1 file is also aggregated at three organization levels:

```text
country -> university
university -> country
university -> university
```

These are still Erasmus mobility flows, so the meaningful scope is cross-border country pairs. Same-country rows in the source are extremely rare and look like coding artifacts, not a real domestic Erasmus layer.

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
6. Design (do not estimate) the gravity-style regression — see [Model Design](#model-design).
7. Build the Reddit text layer for the quality-of-life variable (β₂).

## Build Commands

```bash
.venv/bin/python scripts/build_flows.py
.venv/bin/python scripts/build_indicators.py
.venv/bin/python scripts/build_org_flows.py
.venv/bin/python scripts/build_geocode.py
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

- sticky top-bar controls for sending country search, flow level, map aggregation, university/place search, and salary explorer settings
- selected-country destination chart and GDP-gap scatter
- destination table sortable by flow count, flow share, GDP gap, price gap, and earnings gap
- same-order sending/receiving heatmap
- university-level flow map and table for country→university, university→country, and university→university views
- sortable flow-weighted destination economics table
- Higher Education grant-per-participant metric from the annual annex
- Reddit destination sentiment/themes layer for the quality-of-life variable

VM deployment helpers:

```bash
./scripts/setup_unilife_nginx.sh
./scripts/deploy_dashboard.sh
```

See [Model Design](#model-design) above for the full gravity specification.

## Text Layer (β₂ quality of life)

The Reddit text layer supplies the quality-of-life variable (β₂) and is the executed text-analysis component. Built after the flow pipeline is clean:

- collect Reddit `r/Erasmus` posts/comments mentioning destinations
- use Gemini + Pydantic for structured extraction
- extract country/city, sentiment, and themes such as cost, housing, nightlife, academics, safety, and bureaucracy
- manually label 40-50 mentions to evaluate extraction quality

This connects the final project to the course's LLM information-extraction assignment.

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

Use the detailed KA1 Erasmus Excel file as the backbone of the project. Build the flow dataset first, then the Reddit text layer (β₂ quality of life). The gravity regression is documented as step-3 design, not estimated.
