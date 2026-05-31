# ErasmusGravity - Final Project

**Course:** Text Analysis for Economics  
**Deliverable:** `Palanca_Leonardo.zip` - notebook + report + raw/processed data

---

## Working Title

**Economic Attractiveness and Erasmus Mobility: A Descriptive Analysis of European Student Flows**

---

## Research Question

> What explains the size of Erasmus Higher Education mobility flows from one country to another?

We frame origin-to-destination choice as a gravity-style model in which flow size responds to the **salary gap**, **perceived quality of life**, **institution quality**, and **language affinity** between origin and destination, controlling for income, cost of living, and distance.

This is a descriptive and exploratory project. It does **not** claim causal inference. Following the grading rubric, the regression is the project's **step-3 design**: the executed work is the spatial flow analysis plus the Reddit text layer; the regression itself is described, not estimated.

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
| Average wages / salaries (Eurostat) | Labor-market attractiveness | β₁ salary gap |
| QS World 2023 score (geocoded → destination city) | Academic pull of destination | β₃ institution quality (built) |
| GDP per capita | Sending and receiving country income | Control: income gap |
| Cost-of-living index | Affordability of destination | Control: price-level gap |
| Distance (origin centroid → destination city) | Gravity friction | Control (built) |
| Language-family groupings (shared family dummy) | Origin–destination language affinity | Control (built) |

Text layer (β₂ quality of life):

| Source | What | Role |
|--------|------|------|
| Reddit `r/Erasmus` | Student discussions of destinations | Qualitative perception layer |
| OpenRouter (DeepSeek) + Pydantic extraction | City/country, sentiment, themes | β₂ quality of life (text analysis) |

---

## Unit of Analysis

The main analytical dataset is a country-pair table:

```text
sending_country, sending_code, receiving_country, receiving_code, flow_count
```

For the interactive dashboard, the detailed KA1 file is also aggregated to:

```text
country -> university
university -> country
university -> university
```

These organization-level views support the planned institution-quality layer (β₃), but the project should still be described as Erasmus cross-border mobility. True within-country Erasmus is not a meaningful layer in this file; the few same-country rows are treated as coding anomalies rather than a domestic mobility outcome.

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

### Step 5 - Regression Design (step-3 deliverable, not estimated)

The gravity-style specification that the collected data would feed:

```text
log(1 + flow_ij) =
    beta1 * salary_gap_ij            # Eurostat net earnings (built)
  + beta2 * quality_of_life_j        # Reddit sentiment/themes (text layer)
  + beta3 * institution_quality_j    # QS 2023 score, geocoded -> destination city (built)
  + controls(gdp_gap_ij, price_level_gap_ij, distance_ij, language_affinity_ij)
  + sending_country fixed effects
  + receiving_country fixed effects
  + error_ij
```

Language affinity (Med / Anglo-Saxon / Germanic groupings) is a **gravity control**, not an instrument: it directly shapes bilateral flows, so it fails the IV exclusion restriction. Per the grading rubric, this regression is **described, not implemented**: the executed analysis is the spatial flow pipeline plus the Reddit text layer (β₂). Origin and destination fixed effects absorb broad country differences. The estimate would be descriptive, not causal. Expected signs: salary gap +, quality of life +, institution quality +, price-level gap −, distance −, language affinity +.

### Step 6 - Optional Reddit / LLM Text Layer

If the core flow analysis is working, add a text-analysis extension:

- Scrape or collect Reddit posts/comments mentioning Erasmus destinations.
- Use OpenRouter (DeepSeek) + Pydantic to extract:

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
├── erasmusgravity.ipynb
├── report.pdf
├── data/
│   ├── raw/
│   │   └── annual-report-2024-statistical-annex.xlsx
│   └── processed/
│       ├── erasmus_flows_long.csv
│       └── erasmus_flows_with_economics.csv
└── README.md or ERASMUSGRAVITY_PROJECT.md
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
