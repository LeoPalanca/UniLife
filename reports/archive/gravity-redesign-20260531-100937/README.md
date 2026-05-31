# ErasmusGravity - Final Project

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
| β₂ | quality of life | Reddit `r/Erasmus` sentiment/themes (OpenRouter DeepSeek + Pydantic) + Erasmusu city ratings | built (text layer) |
| β₃ | institution quality | QS World 2023 score, geocoded + snapped to destination city | built |
| control | gdp gap, price-level gap, distance, language affinity | World Bank / Eurostat / country centroids / language-family groupings | built |

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
notebooks/erasmusgravity.ipynb
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
# producers -> CSV exports in data/processed/
.venv/bin/python scripts/build_flows.py
.venv/bin/python scripts/build_indicators.py
.venv/bin/python scripts/build_org_flows.py
.venv/bin/python scripts/build_geocode.py
.venv/bin/python scripts/build_city_year_panel.py   # HE study city-year panel (from Vaisanen parquet)
.venv/bin/python scripts/build_institution_quality.py  # beta3: QS unis geocoded -> destination city

# consolidate every CSV into the SQLite store
.venv/bin/python scripts/build_db.py                # -> data/erasmusgravity.db (indexed)

# analysis / output read from the DB
.venv/bin/python scripts/run_regression.py
.venv/bin/python scripts/build_dashboard.py
```

Data layer: producer scripts write CSV exports to `data/processed/`; `build_db.py` loads them
into a single indexed SQLite file `data/erasmusgravity.db`; analysis (`run_regression.py`) and the
dashboard read from the DB.

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
./scripts/setup_erasmusgravity_nginx.sh
./scripts/deploy_dashboard.sh
```

See [Model Design](#model-design) above for the full gravity specification.

## Text Layer (β₂ quality of life)

The Reddit text layer supplies the quality-of-life variable (β₂) and is the executed text-analysis component. Built after the flow pipeline is clean:

- collect Reddit `r/Erasmus` posts/comments mentioning destinations
- use OpenRouter (DeepSeek) + Pydantic for structured extraction
- extract country/city, sentiment, and themes such as cost, housing, nightlife, academics, safety, and bureaucracy
- manually label 40-50 mentions to evaluate extraction quality

This connects the final project to the course's LLM information-extraction assignment.

## Literature

> The full gravity-model derivation, estimation discussion (log-OLS vs PPML), and our adapted
> specification live in [`reports/gravity_model.md`](reports/gravity_model.md). The QoL
> measurement, identification, and cross-sectional-vs-within-country results are in
> [`reports/qol_methodology_notes.md`](reports/qol_methodology_notes.md). The bibliography below
> is the reference list those notes draw on.

The project sits at the intersection of three strands: the gravity model of flows, its
application to student mobility, and text-as-data methods for economics.

### Gravity model — foundations and estimation

- **Tinbergen, J. (1962).** *Shaping the World Economy.* Twentieth Century Fund. — First use of the
  Newtonian gravity analogy for bilateral flows.
- **Anderson, J. E., & van Wincoop, E. (2003).** "Gravity with Gravitas: A Solution to the Border
  Puzzle." *American Economic Review*, 93(1), 170–192. — Structural gravity and *multilateral
  resistance*; the theory behind origin- and destination-side fixed effects.
- **Santos Silva, J. M. C., & Tenreyro, S. (2006).** "The Log of Gravity." *Review of Economics and
  Statistics*, 88(4), 641–658. — Why log-OLS (including `log(1+flow)`) is biased under
  heteroskedasticity and zero flows, and why **Poisson Pseudo-Maximum-Likelihood (PPML)** is the
  standard estimator. This motivates moving our step-3 design from log-OLS to PPML.

### Gravity applied to student and Erasmus mobility

- **Rodríguez González, C., Bustillo Mesanza, R., & Mariel, P. (2011).** "The determinants of
  international student mobility flows: an empirical study on the Erasmus programme." *Higher
  Education*, 62(4), 413–430. — Gravity model estimated directly on Erasmus flows; closest precedent
  to our specification.
- **Beine, M., Noël, R., & Ragot, L. (2014).** "Determinants of the international mobility of
  students." *Economics of Education Review*, 41, 40–54. — Cost, network, and university-quality
  drivers in a gravity framework.

### Returns to mobility (salary top-up, β₁)

- **Parey, M., & Waldinger, F. (2011).** "Studying Abroad and the Effect on International Labour
  Market Mobility: Evidence from the Introduction of Erasmus." *The Economic Journal*, 121(551),
  194–222. — Causal evidence that Erasmus participation raises later cross-border labour mobility.
- **Di Pietro, G. (2015).** "Do study abroad programs enhance the employability of graduates?"
  *Education Finance and Policy*, 10(2), 223–243.

### Text as data (β₂ Reddit layer, course method)

- **Gentzkow, M., Kelly, B., & Taddy, M. (2019).** "Text as Data." *Journal of Economic Literature*,
  57(3), 535–574. — The reference framework for using text as an economic variable; anchors the
  Reddit sentiment layer to the course.
- **Grimmer, J., & Stewart, B. M. (2013).** "Text as Data: The Promise and Pitfalls of Automatic
  Content Analysis Methods for Political Texts." *Political Analysis*, 21(3), 267–297. — Validation
  discipline (e.g. hand-labelling a sample) for automated extraction.

### Data source for the temporal panel

- **Väisänen, T., Malekzadeh, M., Inkeröinen, O., & Järv, O. (2025).** "Mobility of Erasmus+ students
  in Europe: Geolocated individual and aggregate mobility flows from 2014 to 2023." *Scientific
  Data*. DOI: [10.1038/s41597-025-04789-0](https://doi.org/10.1038/s41597-025-04789-0). Data on
  Zenodo (CC-BY-4.0): <https://zenodo.org/records/16737523>. — Spatially enriched Erasmus+ mobility
  (LAU city + NUTS3 region codes, 2014–2023), derived from the official EU raw data. Provides the
  temporal dimension and pre-built geocoding for a panel gravity model.

## Temporal Extension (panel design)

A single year (2022) only supports a cross-sectional gravity model, which cannot separate the
salary/quality-of-life signal from omitted bilateral factors. The planned extension stacks the
Väisänen et al. (2025) data into an origin × destination × year panel and estimates by PPML:

```text
Flow_ijt = exp[ alpha_it + delta_ij + beta * X_ijt ] * error_ijt
```

- `alpha_it` origin × year fixed effects — push factors and origin-side multilateral resistance.
- `delta_ij` pair fixed effects — absorb distance, language, and all time-invariant bilateral ties.
- `X_ijt` time-varying terms of interest: bilateral `salary_gap_ijt`, yearly Reddit sentiment
  (binned by post timestamp), institution quality.

Destination × year fixed effects (full structural gravity) are kept as a robustness check only,
because they absorb the destination-level economics the project is trying to measure.

## Repository Structure

```text
.
├── README.md
├── ERASMUSGRAVITY_PROJECT.md
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
│   └── erasmusgravity.ipynb
├── reports/
│   └── figures/
└── src/
    └── erasmusgravity/
```

## Current Position

KA1 Erasmus Excel is the backbone; the spatial flow pipeline and the Reddit/Erasmusu text layer
(β₂ quality of life) are built. Per the rubric the gravity regression is a **step-3 design**, but
we also ran it as exploratory evidence (`scripts/run_regression.py`, results on the dashboard
**Results** tab). Status of each model term:

| Term | Variable | Status | Headline estimate (PPML, city-clustered) |
|------|----------|--------|-------------------------------------------|
| β₃ | Institution quality (QS best score) | estimated | **+0.013, p<0.001** (+29%/SD) — significant, strongest driver |
| β₂ | Quality of life (Erasmusu rating) | estimated | **+0.17, p<0.001** (+12%/SD) — significant |
| control | Language affinity (shared family) | estimated | **+0.17, p=0.002** (+8%/SD) — significant |
| β₁ | Salary gap (net earnings) | estimated | −0.00002, p=0.02 — significant but wrong-signed (collinear, VIF≈7) |
| control | Distance (origin centroid → dest city) | estimated | +0.10, p=0.09 — borderline, wrong-signed |
| control | GDP-per-capita gap | estimated | +0.000003, p=0.55 — insignificant (collinear) |
| control | Price-level gap | estimated | +0.003, p=0.67 — insignificant (collinear) |

The full cross-sectional PPML (Spec J) identifies three signals: **institution quality (β₃, strongest,
+29%/SD), quality of life (β₂), and shared language**. **Key finding:** adding β₃ attenuates β₂ by
~40% (+0.276 → +0.166, both still p<0.001) — not collinearity (β₃ VIF≈1.08) but mediation: top
universities cluster in high-liveability cities, so ~two-fifths of the apparent "quality-of-life
pull" is actually academic pull (see [`reports/qol_methodology_notes.md`](reports/qol_methodology_notes.md)). The three monetary gaps are collinear
(VIF≈4.7–6.9), so β₁'s significant-but-wrong sign is not interpretable on its own — they stay as
controls. The cleanest single result remains the **city-level panel two-stage** (Stage-1 PPML
destination FEs ~ Erasmusu rating): **β=+0.79, p<0.001** over 282 cities / 24 countries. Honest
claim: a **robust positive association of institution quality, quality of life, and shared language
with Erasmus flows across destinations** — not causal (no receiving-country FE in the headline
cross-section).
