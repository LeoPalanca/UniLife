# UniLife - Final Project

**Course:** Text Analysis for Economics  
**Deliverable:** `Palanca_Leonardo.zip` - notebook + report + raw/processed data

---

## Working Title

**Economic Attractiveness and Erasmus Mobility: A Descriptive Analysis of European Student Flows**

---

## Research Question

> How are Erasmus student mobility flows distributed across economic gaps between sending and receiving countries?

The project asks whether students from different origin countries tend to choose destinations that are richer, poorer, cheaper, more expensive, or economically similar to their home country.

This is a descriptive and exploratory project. It does **not** claim causal inference. The goal is to document patterns in official Erasmus mobility flows and connect them to economic indicators such as GDP per capita, wages, and cost of living.

---

## Motivation

The initial observation comes from the Erasmus+ 2024 statistical annex. In the `Youth Mobility` sheet, Italian participants appear to choose several relatively lower-income or lower-cost destinations, while Luxembourg participants appear to concentrate more on richer neighboring countries.

For the core analysis, the better Erasmus student measure is likely:

> `HE-Learn Mobility` = Higher Education learner mobilities

This sheet is closer to university student Erasmus mobility than the broader `Youth Mobility` sheet.

---

## Main Hypothesis

Students' destination choices are associated with the economic position of destination countries relative to their home country.

Possible descriptive hypotheses:

- Students from richer countries are more likely to choose richer and higher-cost destinations.
- Students from lower-income countries may be more sensitive to destination cost of living.
- Geographic proximity and country popularity still matter strongly, so economic gaps should be interpreted as associations, not causal effects.

---

## Core Data Sources

| Source | What | Role |
|--------|------|------|
| `annual-report-2024-statistical-annex.xlsx` | Erasmus+ country-to-country mobility matrix | Main flow data |
| `HE-Learn Mobility` sheet | Higher Education learner flows | Preferred outcome |
| GDP per capita | Sending and receiving country income | Economic gap |
| Average wages / salaries | Labor-market attractiveness | Economic gap |
| Cost-of-living index | Affordability of destination | Economic gap |
| Distance between countries | Gravity-style control | Baseline mobility friction |

Optional text layer:

| Source | What | Role |
|--------|------|------|
| Reddit `r/Erasmus` | Student discussions of destinations | Qualitative perception layer |
| Gemini + Pydantic extraction | City/country, sentiment, themes | Text-analysis extension |

---

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

---

## Analysis Plan

### Step 1 - Load Erasmus Flow Matrix

- Read `HE-Learn Mobility` from the Excel annex.
- Extract the sending-country rows and receiving-country columns.
- Convert the matrix to long format.
- Remove same-country flows for the main cross-border analysis.

Output:

```text
data/processed/erasmus_flows_long.csv
```

### Step 2 - Add Economic Indicators

- Add GDP per capita, wages/salaries, and cost-of-living indicators.
- Compute origin-destination gaps.
- Keep source URLs and raw files for reproducibility.

Output:

```text
data/processed/erasmus_flows_with_economics.csv
```

### Step 3 - Descriptive Flow Patterns

- Top destinations by sending country.
- Top sending countries by destination.
- Heatmap of the country-to-country flow matrix.
- Compare examples such as Italy and Luxembourg.

### Step 4 - Economic Gradient

For each sending country, compute the flow-weighted average destination value:

```text
weighted_destination_gdp =
    sum(flow_to_destination * destination_gdp) / total_outgoing_flow
```

Repeat for:

- GDP per capita
- Average wages
- Cost of living

This gives a clean way to ask whether students from each country tend to move toward richer, poorer, cheaper, or more expensive destinations.

### Step 5 - Regression as Descriptive Evidence

Use a simple gravity-style model:

```text
log(1 + flow_ij) =
    beta1 * gdp_gap_ij
  + beta2 * cost_gap_ij
  + beta3 * distance_ij
  + sending_country fixed effects
  + receiving_country fixed effects
  + error_ij
```

This is not causal. It is a structured descriptive model that checks whether economic gaps are associated with larger or smaller flows after accounting for broad origin and destination differences.

### Step 6 - Optional Reddit / LLM Text Layer

If the core flow analysis is working, add a text-analysis extension:

- Scrape or collect Reddit posts/comments mentioning Erasmus destinations.
- Use Gemini + Pydantic to extract:

```python
from pydantic import BaseModel, Field
from typing import Literal

class DestinationMention(BaseModel):
    city: str | None = None
    country: str
    sentiment: Literal["positive", "neutral", "negative"]
    themes: list[str] = Field(
        description="Examples: cost, housing, nightlife, academics, safety, bureaucracy"
    )
    confidence: float = Field(ge=0.0, le=1.0)

class PostExtraction(BaseModel):
    mentions: list[DestinationMention]
```

Recommended evaluation:

- Manually label 40-50 mentions.
- Compare LLM outputs against the manual labels.
- Discuss where the model succeeds or fails.

This connects directly to the course's LLM information-extraction assignment.

---

## Visualizations

Core figures:

1. Erasmus flow heatmap: sending country x receiving country.
2. Italy vs Luxembourg destination profiles.
3. Scatter plot: destination GDP gap vs flow share.
4. Flow-weighted destination GDP/cost by sending country.
5. Optional choropleth: inbound Erasmus flows by country.

Optional text figures:

1. Most frequent Reddit themes by country.
2. Sentiment distribution by destination.
3. Comparison between economic indicators and Reddit themes.

---

## Report Structure

1. **Introduction** - Erasmus mobility and the research question.
2. **Data** - Erasmus flow matrix and economic indicators.
3. **Methods** - matrix reshaping, joins, flow shares, economic gaps, descriptive regression.
4. **Results** - flow patterns, Italy/Luxembourg example, economic-gradient results.
5. **Conclusion** - main descriptive findings, limitations, possible Reddit/LLM extension.

---

## Deliverable Checklist

```text
Palanca_Leonardo.zip
├── unilife.ipynb
├── report.pdf
├── data/
│   ├── raw/
│   │   └── annual-report-2024-statistical-annex.xlsx
│   └── processed/
│       ├── erasmus_flows_long.csv
│       └── erasmus_flows_with_economics.csv
└── README.md or UNILIFE_PROJECT.md
```

If the optional text layer is added:

```text
data/
├── raw/reddit_raw.json
└── processed/reddit_destination_mentions.json
```

---

## Current Position

Use the official Erasmus Excel file as the backbone of the project. Build the flow dataset first. Add Reddit and LLM extraction only after the flow/economic analysis is clean and reproducible.
