# Prompt: ErasmusGravity Dashboard Mockup

Build a **full-page dashboard mockup** (`mockup.html`) for a research project
called **ErasmusGravity**.

## What this dashboard does

ErasmusGravity visualises Erasmus+ Higher Education student mobility flows
across Europe. It answers: "What explains the size of student flows from one
country to another?" The analytical frame is a **gravity model** — the
Newtonian analogy where bilateral flows are attracted by salary gaps, quality
of life, and institution quality, and dampened by distance and cost.

The dashboard is a data-journalism piece for an academic final project. It is
**not** a SaaS app. Tone: Our World in Data, FT visual stories, Pudding.cool.
Dense information presented with editorial care.

---

## Technical constraints

- **One self-contained HTML file**, inline CSS, no external JS/CSS deps.
- **System font stack only**: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- WCAG AA contrast.
- Responsive at **1440px, 1024px, 375px**.
- Use **placeholder data** throughout — static HTML, no working JS needed.
- Under 100 KB.

---

## Design tokens (use these CSS variables)

```css
:root {
  --ink: #1f2933;
  --muted: #5f6b76;
  --line: #d8dee4;
  --paper: #f7f7f4;
  --panel: #ffffff;
  --accent: #2f6f73;     /* "gravity teal" — primary */
  --accent-2: #b44e5a;   /* muted coral — secondary */
  --soft: #eef3f1;
  --positive: #2f6f73;
  --negative: #b44e5a;
  --neutral: #5f6b76;
}
```

Chart palette (6 series): `#2f6f73`, `#b44e5a`, `#c98a2b`, `#4a6fa5`, `#6b8f3a`, `#8a5a9e`.

---

## Page structure (16 sections, top to bottom)

### 1. Header

White background, bottom border. Contains:
- `<h1>unilife.ellep.it</h1>` (the domain — stays as-is)
- Subtitle paragraph: "**Research question:** what explains the size of
  Erasmus+ Higher Education flows from one country to another? We frame
  destination choice as a gravity-style model where flows respond to the salary
  gap, perceived quality of life, institution quality, and language affinity
  between origin and destination."

Padding: 30px 42px 22px.

### 2. Sticky Topbar

Position sticky, white background, bottom border, subtle box-shadow.

**Row 1** (5-column grid on desktop, stacked on mobile):
- Brand mark: **ErasmusGravity** — bold 22px, left-aligned. Consider a
  typographic treatment: e.g. "Erasmus" in regular weight + "Gravity" in bold,
  or a thin teal rule beneath, or a subtle letter-spacing difference.
- Input: "Sending country" with placeholder "Search country or code"
- Select: "Flow level" with options "Country → university", "University →
  country", "University → university"
- Input: "University / place" with placeholder "Search university, city, country"
- Button: "Clear"

**Row 2** (flex, wrapping):
- Scope pill: `KA1 study mobility · cross-border country pairs` — rounded pill,
  teal text on soft background.
- Select: "Map view" with options "Selected sending country", "All countries aggregate"
- Select: "Salary country" (show "Spain" selected)
- Select: "Salary unit" with options "Euro (EUR)", "Purchasing power standard (PPS)"
- Stat readout: "Italy: **12,847** outgoing students"
- Nav links (right-aligned): Map · Trends · Universities · Economics · Salary · Reddit

### 3. The Model

A section card (white panel, border, rounded corners, padding 22px).

Heading: "The Model"

Paragraph: "We model each origin–destination flow as a gravity-style regression.
This is the project's **step-3 design**: the specification below describes how
the collected text and spatial data would be used to answer the research
question. It is documented, not estimated."

**The equation** — displayed prominently with typographic care:
```
log(1 + flow_ij) = β₁·salary_gap_ij + β₂·quality_of_life_j + β₃·institution_quality_j
                 + controls(gdp_gap, price_level_gap, distance, language_affinity)
                 + origin FE + destination FE + ε_ij
```
Use `<code>` or a styled block. Subscripts should use `<sub>`. Greek letters as
Unicode. The equation should feel like a textbook specification — monospace or
serif-like, generous line height.

Note below: "Language affinity is a gravity control (a bilateral friction that
directly shapes flows), not an instrument. Origin and destination fixed effects
absorb broad country-level differences. The estimate is descriptive, not causal."

### 4. Explanatory Variables

Section card. Heading: "Explanatory Variables (the βs)"

Note: "Each term in the model and its data source. **built** = data already in
the processed pipeline; **planned** = part of the described design."

7 cards in a responsive grid (`repeat(auto-fit, minmax(180px, 1fr))`):

| Symbol | Name | Role | Status |
|--------|------|------|--------|
| β₁ | Salary gap | Labour-market pull | built |
| β₂ | Quality of life | Perceived liveability | built |
| β₃ | Institution quality | Academic pull | planned |
| control | Language affinity | Origin–destination language affinity | planned |
| control | GDP gap | Income difference | built |
| control | Price-level gap | Cost of living | built |
| control | Distance | Gravity friction | planned |

Each card: top line "β₁ · built" (built in teal, planned in muted grey),
title in 18px bold, then role/source/expected-sign as small text.

### 5. Selected Country Overview

Section card. Heading: "Selected Country Overview"

5 stat cards in a row:
- Outgoing students: **12,847**
- Destinations: **31**
- Share to richer GDP pc countries: **62.4%**
- HE grants, EUR: **421,500,000**
- Grant per estimated participant: **1,842**

Cards: soft background, border, 8px radius, label above value.

Note: "Use the sending-country selector in the top bar."

### 6. University Flow Map

Section card. Heading: "University Flow Map"

A placeholder rectangle 540px tall, background `var(--soft)`, border,
border-radius 8px. Inside, a centered label "Map placeholder — Leaflet with
clustered markers" in muted text.

Below: map legend with two dot sizes ("smaller flow" with 10px dot, "larger
flow" with 24px dot) and a note paragraph about how points represent university
endpoints.

### 7. Mobility Over Time (2014–2023)

Section card. Heading: "Mobility Over Time (2014–2023)"

Note: "Higher Education study mobility by calendar year."

**2-column grid** (`minmax(380px, 1fr)`):

**Left column:**
- Subheading: "All countries — total outgoing"
- A placeholder SVG line chart (one series, teal). X-axis: 2014–2023. Y-axis:
  student count (use approximate values: ~250k rising to ~350k with a dip at
  2020). Grid lines. Dot markers at data points.
- Note: "The 2020 drop reflects COVID-19 disruption."

**Right column:**
- Subheading: "Italy — top destinations"
- A placeholder SVG line chart with 5 series in chart-palette colours.
  X: 2014–2023. Show Spain, Germany, France, Portugal, UK as destination lines.
- Legend swatches below the chart.
- Note: "Yearly flows from the selected sending country."

### 8. University-Level Flow Detail

Section card. Heading: "University-Level Flow Detail"

Note describing the current view.

A data table with 5 placeholder rows. Columns:
Destination country | Receiving city | Receiving university | Students

Sample rows:
- ES - Spain | Madrid | Universidad Complutense de Madrid | 342
- DE - Germany | Munich | Technische Universitat Munchen | 287
- FR - France | Paris | Sorbonne Universite | 231
- PT - Portugal | Lisbon | Universidade de Lisboa | 198
- NL - Netherlands | Amsterdam | Universiteit van Amsterdam | 176

### 9. Top Destinations + GDP Gap Scatter (2-column grid)

Two section cards side by side.

**Left: Top Destinations**
Horizontal bar chart (SVG). 10 bars, tallest at top:
ES 4,231 | DE 2,108 | FR 1,876 | PT 1,542 | NL 987 | UK 876 | PL 654 |
AT 543 | BE 432 | CZ 321

Bars: `var(--accent)`, rounded corners. Country code labels left, counts right.

**Right: GDP Gap and Flow Share — control**
Scatter plot (SVG). ~10 bubbles. X-axis: "poorer destination ← GDP pc gap →
richer destination". Y-axis: "flow share". Vertical zero-line. Bubble size
varies. Fill: `#5d6f9f` opacity 0.68, white stroke.

Note: "**GDP gap** = receiving-country GDP per capita minus sending-country.
**Flow share** = flow to that destination divided by all outgoing."

### 10. Destination Table

Section card. Heading: "Selected Country Destination Table"

Full-width sortable data table. 8 columns:
Code | Destination | Students | Flow share | Receiver GDP pc US$ | GDP gap US$ | Price gap | Earnings gap EUR

Show 8 rows with realistic placeholder data. Sortable headers in
`var(--accent)`.

### 11. Flow Heatmap

Section card. Heading: "Flow Heatmap"

Note: "Rows and columns use the same country order."

An 8x8 SVG heatmap grid using these country codes on both axes:
ES, DE, FR, IT, PL, NL, PT, AT

Cells filled with `rgba(47, 111, 115, opacity)` — vary opacity to suggest
different flow magnitudes. Diagonal cells (same-country) should be empty/light.
Empty cells: `#f3f5f5`.

**Include a colour-ramp legend** strip below: a horizontal gradient bar from
transparent to full teal, with "0" on the left and "4,000+" on the right.

### 12. Flow-Weighted Destination Economics

Section card. Heading: "Flow-Weighted Destination Economics"

Note: "Click column headers to sort."

Sortable 8-column table:
Code | Sender | Outgoing students | Weighted dest GDP pc US$ | Weighted dest price level | Weighted dest earnings EUR | Grant per est. participant EUR | Grant per actual participant EUR

Show 6 rows: IT, DE, FR, ES, PL, NL with realistic placeholder numbers.

### 13. Salary Explorer

Section card. Heading: "Expected Earnings by Economic Sector — evidence for β₁ (salary gap)"

Horizontal bar chart (SVG). 8 bars representing NACE sectors:
- Financial and insurance activities: 4,820
- Information and communication: 4,210
- Professional, scientific, technical: 3,890
- Manufacturing: 3,120
- Construction: 2,980
- Wholesale and retail trade: 2,540
- Accommodation and food service: 1,890
- Administrative and support services: 1,760

Bars: `var(--accent)`, labels left (truncated at ~38 chars), values right.

Note: "Mean monthly gross earnings by NACE sector, Structure of Earnings
Survey 2018. Coverage limited to 17 countries."

### 14. Reddit Quality of Life

Section card. Heading: "Perceived Quality of Life — evidence for β₂ (Reddit r/Erasmus)"

Note: "Destination mentions extracted from r/Erasmus with OpenRouter (DeepSeek) +
Pydantic. **Net sentiment** = (positive − negative) / mentions. Per-country
counts are small; read as qualitative."

10-column sortable table:
Destination country | Mentions | Positive | Neutral | Negative | Net sentiment | Score-weighted net | Avg. score | Positive themes | Negative themes

Show 6 rows. Net sentiment and score-weighted net use **sentiment badges**:
positive values in teal with + sign, negative in coral with − sign. Themes
columns: left-aligned, wrapping text (e.g. "nightlife, academics, culture" /
"cost, housing, bureaucracy").

### 15. Data Sources

Section card. Heading: "Data Sources and Measurement Notes"

Bulleted list (`<ul>`) with 8 items:
- **Erasmus flows:** `Erasmus-KA1-Mobility-Data-2022.xlsx`, sheet `KA1 mobilities 2022`. Filtered to Higher Education study mobility.
- **Flow scope:** Cross-border origin–destination. Same-country rows are coding artifacts.
- **HE grants:** `annual-report-2024-statistical-annex.xlsx`, sheet `KA1_estimated paxs`, Call Year 2022.
- **GDP per capita:** World Bank current US$.
- **Price levels and net earnings:** Eurostat API.
- **Scholarship proxy:** Grant per participant is country-level, not individual.
- **Quality of life (built):** Reddit r/Erasmus, sentiment + themes via OpenRouter + Pydantic.
- **Institution quality (planned):** Destination university ranking score.

### 16. Footer

Full-width, `var(--soft)` background, top border. Contains:
- "ErasmusGravity — Economic Attractiveness and Erasmus Mobility"
- "Text Analysis and Spatial Data for Economists SP 2026 · Leonardo Palanca"
- "Data vintage: Erasmus KA1 2022, Eurostat 2022, Reddit r/Erasmus 2024–2025"

---

## Layout notes

- Main content: `padding: 28px 42px 48px`, sections stack vertically with 24px gap.
- Section cards: white panel, 1px border `var(--line)`, 8px radius, 22px padding.
- 2-column grids: `repeat(auto-fit, minmax(380px, 1fr))`, gap 24px.
- Stat cards grid: `repeat(auto-fit, minmax(180px, 1fr))`, gap 12px.
- Variable cards grid: same as stat cards.
- Mobile (< 700px): single column, padding 18px, topbar stacks vertically.
- Tables: `min-width: 820px` with `overflow-x: auto` on container.
