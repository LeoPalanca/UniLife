# ErasmusGravity - Final Project

**Course:** Text Analysis for Economics  
**Deliverable:** `Palanca_Leonardo.zip` - notebook + report + raw/processed data

## Working Title

**Economic Attractiveness and Erasmus Mobility: A Descriptive Analysis of European Student Flows**

## Research Question

> What explains the size of Erasmus Higher Education mobility flows from one country to another?

We frame origin-to-destination choice as a gravity-style model in which flow size responds to **perceived quality of life**, **institution quality**, and **language affinity**, controlling for broad destination prosperity and distance.

This is a descriptive and exploratory project. It does **not** claim causal inference. Per the grading rubric, the regression is the project's **step-3 design** (described, not estimated); the executed work is the spatial flow analysis plus the Reddit text layer.

### Model Design

| Term | Variable | Source | Status |
|------|----------|--------|--------|
| control | GDP-per-capita gap | World Bank WDI | built |
| β₂ | quality of life | Reddit `r/Erasmus` sentiment/themes (OpenRouter DeepSeek + Pydantic) + Erasmusu city ratings | built (text layer) |
| β₃ | institution quality | QS World 2023 score, geocoded + snapped to destination city | built |
| control | distance, language affinity | country centroids / language-family groupings | built |
| robustness | salary gap, price-level gap | Eurostat | exploratory — see VIF note |

```text
E[flow_ij] = exp(
    beta2 * quality_of_life_j
  + beta3 * institution_quality_j
  + controls(gdp_gap_ij, distance_ij, language_affinity_ij)
  + sending_country fixed effects
)
# Robustness only:
#   + salary_gap_ij + price_level_gap_ij
```

`gdp_gap` is the headline economic control because it captures broad destination prosperity more
cleanly than a salary-specific story. `salary_gap` and `price_level_gap` are reported as robustness:
all three monetary variables proxy overlapping rich-vs-poor-destination differences. See
`reports/qol_methodology_notes.md › Why the monetary controls are flat`.

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
.venv/bin/python scripts/build_user_institution_quality.py  # beta3 cross-check: StudyPortals student ratings (Wayback)
.venv/bin/python scripts/build_owid_country_year.py  # time-varying terms: OWID life satisfaction + edu spending
.venv/bin/python scripts/build_field_flow_panel.py   # (o,d,ISCED broad field,year) HE-study panel for the COVID DiD
.venv/bin/python scripts/build_covid_sector_hit.py   # 2020 LCI wage-hit per (country, NACE)
.venv/bin/python scripts/build_covid_employment_hit.py  # 2020 LFS employment-hit per (country, NACE), subsidy-free
.venv/bin/python scripts/build_qs_multiyear.py       # time-varying β₃ panel: QS editions 2014/17/18/23 via Wayback
.venv/bin/python scripts/build_sector_wage_panel.py  # SES 2018 anchor + LCI growth -> annual (country, NACE, year) wage levels
.venv/bin/python scripts/build_covid_sector_hit.py   # 2020 LCI wage-deviation per (country, NACE sector)

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

### Returns to mobility and economic controls

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

### Institution-quality and time-varying data sources

- **QS World University Rankings 2023** — overall score per university; geocoded (Nominatim) and
  snapped to the destination city for β₃. <https://www.topuniversities.com>
- **StudyPortals** (mastersportal.com) — student review score per university (user-based β₃
  cross-check); read via the Internet Archive (live site Cloudflare-gated). <https://www.mastersportal.com>
- **Our World in Data** — country-year *life satisfaction* (Cantril ladder, World Happiness Report)
  and *government education expenditure (% GDP)* for the time-varying panel terms (CC-BY).
  <https://ourworldindata.org>

## Temporal Extension (panel design)

A single year (2022) only supports a cross-sectional gravity model, which cannot separate the
quality-of-life and institution-quality signal from omitted bilateral factors. The planned extension stacks the
Väisänen et al. (2025) data into an origin × destination × year panel and estimates by PPML:

```text
Flow_ijt = exp[ alpha_it + delta_ij + beta * X_ijt ] * error_ijt
```

- `alpha_it` origin × year fixed effects — push factors and origin-side multilateral resistance.
- `delta_ij` pair fixed effects — absorb distance, language, and all time-invariant bilateral ties.
- `X_ijt` time-varying terms of interest: life satisfaction, yearly destination sentiment
  where available, and time-varying institution-quality proxies.

Destination × year fixed effects (full structural gravity) are kept as a robustness check only,
because they absorb the destination-level economics the project is trying to measure.

### Temporal & shock evidence (built)

The panel extension is wired in `scripts/run_regression.py` and surfaced on the dashboard's
**Time & Shocks** act. Diagnostic numbers, all PPML with origin + destination/destination-city
+ year FE, cluster-robust SE:

| Layer | β | p | per-SD | Read |
|-------|---|---|--------|------|
| Year FE 2020 vs 2014 baseline | **−0.167** | — | — | sharp COVID dip; 2023 recovers above 2019 |
| β₂ time-varying (OWID life satisfaction) | **+0.227** | **0.035** | +18.5% | within-destination, over time |
| Education spending %GDP (OWID) | −0.035 | 0.161 | −4.1% | null — useful control |
| β₃ time-varying (QS 2014/17/18/23) | −0.004 | 0.567 | −5.5% | null — QS scores too sticky |
| COVID DiD, LCI wage hit | **−0.0056** | 0.10 | −1.9% | borderline; 2020 event β = −0.010 **p=0.004** |
| COVID DiD, LFS employment hit | +0.018 | 0.95 | +0.1% | null in every year — clean replication |

Read together: the time-varying β₂ confirms that life-satisfaction-type signal moves Erasmus
flows even within-destination. The QS null is exactly what the methodology notes predicted
(QS scores barely vary year-to-year within a city). The LCI vs LFS DiD comparison says
COVID's 2020 hit on Erasmus mobility was lockdown-wide, not field-of-study selective —
LCI's signal was wage-subsidy contamination correlated with lockdown intensity, not a real
sector→field channel.

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

## Future Extensions (parked)

Ideas explored or scoped but not implemented in this submission. Each is well-defined
enough to pick up later; the reason for parking is recorded so the decision is reviewable.

- **Lightly reframe the dashboard sections** to match the report's three-act arc
  (free-bird exploration → pull factors → COVID shock); rename Results → "Pull factors we
  found" and add a small COVID subsection.
- **Economic-control alternatives.** The headline narrative now uses GDP gap as the broad
  prosperity control. A later version could compare it with a standardized income/cost index
  `z(gdp_gap) + z(earnings_gap) - z(price_level_gap)`, but salary and price-level gaps should
  remain robustness terms unless that index is explicitly justified.
- **StudyPortals review counts.** Score parsed; the review *count* (which would let us
  opinion-weight β₃ user-side like Erasmusu) isn't in the meta description — needs a body
  parser to extract it.
- **Institution-capacity control for β₃.** The current QS `best_score` term captures
  academic/institutional attractiveness, but it may also proxy larger universities, denser
  Erasmus partnership networks, and more available exchange seats. A later version should add
  a destination-capacity control such as number of receiving institutions, total inbound
  Erasmus seats, university enrollment, or `n_ranked`/academic-cluster size, then test whether
  the QS effect remains after scale is separated from quality.
- **Sector-shock event study using the LCI-spliced wage panel** (`sector_wage_panel.csv`,
  built). The annual wage-level panel exists for 17 countries × 18 sectors × 10 years;
  a generic event-study scaffolding to detect idiosyncratic sector × year shocks is
  scoped but not wired into `run_regression.py`.
- **DeepSeek chatbot on country/uni selection.** Currently the dashboard surfaces
  pre-aggregated metrics only. A natural-language Q&A layer over the same data
  (Reddit mentions, β coefficients, flow tables) would let a reader ask "why is
  Bocconi over-represented for Spanish economics students?" and get a grounded
  answer. Three implementation options, ordered from least to most infra:
  1. **Build-time pre-bake.** One DeepSeek call per (country) and per top-N uni at
     `build_dashboard.py` time, results inlined into the JS payload as
     `chatbotBlurbs[code]`. No live key, no infra, deterministic. Loses Q&A —
     reader can only read a fixed blurb. Cheapest.
  2. **Bring-your-own-key.** A textarea on the dashboard takes the user's
     OpenRouter key (stored in `localStorage`) and calls the API directly from
     the browser. Free to host, but most readers won't have a key.
  3. **Serverless proxy.** A 30-line Cloudflare Worker / Vercel function holds the
     `OPENROUTER_API_KEY` and exposes `/api/chat?country=IT&uni=BO`. The dashboard
     hits the proxy. Cleanest UX, requires one piece of external infra and rate
     limiting to prevent key abuse.

  Decision deferred — depends on whether the final submission allows live API
  calls and what budget OpenRouter is left.

## Current Position

KA1 Erasmus Excel is the backbone; the spatial flow pipeline and the Reddit/Erasmusu text layer
(β₂ quality of life) are built. Per the rubric the gravity regression is a **step-3 design**, but
we also ran it as exploratory evidence (`scripts/run_regression.py`, results on the dashboard
**Results** tab). Status of each model term:

| Term | Variable | Status | Headline role |
|------|----------|--------|-------------------------------------------|
| β₃ | Institution quality (QS best score) | estimated | Main pull factor; interpret as academic/institutional attractiveness, not pure teaching quality |
| β₂ | Quality of life (Erasmusu rating + Reddit evidence) | estimated | Main pull factor; Erasmusu is the regression proxy, Reddit is the text-analysis evidence layer |
| control | Language affinity (shared family) | estimated | Main gravity friction / familiarity control |
| control | GDP-per-capita gap | estimated | Broad destination-prosperity control, not a causal prosperity effect |
| control | Distance (origin centroid → dest city) | estimated | Standard gravity friction, retained even if weak |
| robustness | Salary gap and price-level gap | estimated (exploratory) | Robustness only; monetary gaps overlap and should not drive the story |

The headline cross-sectional PPML should be read as a **descriptive pull-factor model**:
institution quality, perceived quality of life, and language familiarity are the core signals,
with GDP gap included only to absorb broad prosperity differences. Salary and price-level gaps
belong in robustness notes because they create a hard-to-explain economic-controls block rather
than a clean salary story. A **time-varying** panel test (OWID country-year,
origin+destination+year FE) adds the project's closest causal-adjacent QoL result:
**life satisfaction +18.5%/SD, p=0.035**. That panel is stronger than the cross-section because it
uses within-destination changes over time, but it is still not causal proof.

The cleanest single result remains the **city-level panel two-stage** (Stage-1 PPML
destination FEs ~ Erasmusu rating): **β=+0.79, p<0.001** over 282 cities / 24 countries.

COVID and QS time-panel specifications are kept as diagnostics/appendix material. They are useful
checks, but they answer different questions from the core destination-attractiveness narrative.
Honest claim: a **robust positive association of institution quality, quality of life, and shared
language with Erasmus flows across destinations**, plus causal-adjacent support from the
time-varying life-satisfaction panel — not a causal effect from the cross-sectional model.
