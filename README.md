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

The backbone dataset is:

```text
data/raw/annual-report-2024-statistical-annex.xlsx
```

The preferred sheet is:

```text
HE-Learn Mobility
```

This sheet captures Higher Education learner mobilities, which is closer to university Erasmus student mobility than the broader `Youth Mobility` sheet.

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

1. Load the `HE-Learn Mobility` sheet from the Erasmus+ statistical annex.
2. Reshape the sending x receiving country matrix into a long flow table.
3. Remove same-country flows for the main cross-border analysis.
4. Add GDP, wages, cost-of-living, and distance indicators.
5. Compute economic gaps between sending and receiving countries.
6. Produce descriptive visualizations:
   - flow heatmap
   - Italy vs Luxembourg destination profiles
   - destination GDP/cost gap vs flow share
   - flow-weighted destination GDP/cost by sending country
7. Estimate a non-causal, gravity-style descriptive regression.

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
│   │   └── annual-report-2024-statistical-annex.xlsx
│   └── processed/
├── notebooks/
│   └── unilife.ipynb
├── reports/
│   └── figures/
└── src/
    └── unilife/
```

## Current Position

Use the official Erasmus Excel file as the backbone of the project. Build the flow dataset first. Add Reddit and LLM extraction only after the flow/economic analysis is clean and reproducible.
