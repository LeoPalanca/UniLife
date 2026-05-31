# Quality-of-Life (β₂) — methodology notes for the report

Working notes on how the quality-of-life variable is measured, identified, and
reported. Intended to be folded into the methods/limitations sections.

## Two independent QoL proxies

| Source | What it measures | Construction | Coverage |
|--------|------------------|--------------|----------|
| Reddit `r/Erasmus` | Net *tone* of student discussion of a destination | DeepSeek (OpenRouter) + Pydantic extraction → per-mention sentiment (−1..+1) + themes; weighted mean per city (confidence × log upvotes) | ~900 mentions, sparse per city |
| Erasmusu.com | Overall *liveability rating* of a city | Scraped per-city rating (0–10) + opinion count | 322 cities, dense (median ~45–63 opinions, up to ~1,400) |

**They largely disagree: correlation ≈ 0.21** on ~103 overlapping cities. Interpretation:
they capture *different* constructs (discussion tone vs. overall satisfaction), so they are
reported as **separate** proxies, not merged. A combined z-score fallback spec exists but is
treated as coverage-only, not a primary measure.

## Identification design

Outcome: `log(1 + flow_ij)` at the city-pair level (sending country → receiving city).
QoL enters at the **receiving-city** level. Specification includes **sending-country** and
**receiving-country** fixed effects. Because QoL varies *within* country across cities, the
receiving-country FE can be kept — it absorbs country-level economics and popularity
(addressing the endogeneity where popular countries attract more—often more critical—chatter),
and β₂ is identified from **across-city, within-country** variation.

## Cross-sectional vs within-country (what variation identifies β₂)

The two readings differ in **which variation in QoL the model uses**:

- **Cross-sectional (no receiving FE):** uses the full QoL spread across all cities, most of which
  is *between countries*. Captures "students go to nicer **countries**". Large spread → strong β.
- **Within-country (receiving-country FE):** the FE subtracts each country's mean, so only
  city-vs-city deviations within a country identify β. The Spain↔Poland gap is erased; only
  small contrasts remain → faint β.

## Inference: cluster level

(FE choice changes *which variation identifies β* and so changes the coefficient; cluster choice
changes only how the SE is computed and so changes the p-value. The two are independent.)

QoL is a city-level (generated/aggregated) regressor, so errors are correlated among all
city-pairs sharing a destination. The correct cluster level is the **receiving city** (180–250
clusters), not the receiving country (~11–35 clusters, below the ~30–50 reliability threshold).
The "<30 clusters" concern applies to *countries*, not destinations — cities are plentiful.

Results under within-country identification (receiving-country FE), β₂ positive in all:

| Spec | β | p (city-cluster) | p (country-cluster) |
|------|---|------------------|---------------------|
| Reddit city sentiment | +0.067 | 0.27 | 0.38 |
| Erasmusu rating (n≥5, wtd) | +0.090 | 0.12 | 0.25 |
| Combined (z fallback) | +0.046 | 0.053 | 0.18 |

**Finding:** proper city-clustering lowers p-values but does **not** make the individual
sources significant; only the high-coverage combined spec reaches borderline (p≈0.05). So the
limitation is not merely cluster count — the **within-country signal is genuinely weak**.

## Why within-country is so demanding — and the cross-sectional result

Receiving-country FE removes all *cross-country* variation, which is where most of the QoL↔flow
relationship lives (richer, higher-QoL countries receive more students). Within-country
identification asks only whether, e.g., higher-rated Barcelona vs. Madrid tracks higher flows —
a faint signal.

A **cross-sectional spec** (no receiving-country FE; economics controlled by GDP gap in the
preferred narrative; sending-country FE; cluster by city) uses the strong cross-country variation:

| Spec | estimator | β | p (city-cluster) | flow effect / rating point |
|------|-----------|---|------------------|----------------------------|
| Erasmusu rating (n≥5, wtd) | log-OLS | +0.149 | <0.001 | ≈ +16% |
| Combined QoL | log-OLS | +0.042 | 0.013 | — |
| Erasmusu rating (n≥5) | **PPML (Poisson)** | +0.276 | <0.001 | **≈ +32%** |

Here β₂ is **strongly significant** under both estimators. PPML (the proper gravity estimator,
Santos Silva & Tenreyro 2006; on flow levels, handles heteroskedasticity) gives a larger effect
(+32% per rating point) than log-OLS (+16%). The trade-off: without receiving-country FE,
popularity/economic confounds are only partly netted out by the prosperity control, so this is a
**robust association, not causal**.

**Full-gravity controls (distance + language).** Adding the two remaining gravity terms to the
PPML — `log_distance` (origin-country centroid → destination city) and `same_language` (1 if the
origin and destination share a language family) — barely moves QoL: β₂(rating) = +0.271 (was
+0.276), still p<0.001. Of the two new controls, **language affinity is positive and significant**
(β=+0.158, p≈0.006; ≈+8% flow per SD — sharing a language family lifts flow), while **distance is
insignificant and wrong-signed** (β=+0.04, p≈0.55) in this cross-section: the sender-country FE
already absorbs origin location, and the Erasmusu-matched sample is dominated by a handful of
popular, often-distant destinations (Spain, etc.), so within-origin distance carries little signal
here. This pre-β₃ specification is useful only as a comparison point: once institution quality is
added, part of the apparent quality-of-life association is reallocated to academic pull.

**Why the monetary controls are simplified.** Salary gap, GDP gap, and price-level gap all proxy
the same rich-vs-poor-destination dimension. When all three enter together, the individual
coefficients become unstable and hard to interpret. A VIF check on the full economic-controls
PPML explains why:

| regressor | VIF |
|-----------|-----|
| earnings_gap (β₁) | 6.90 |
| price_level_gap | 6.52 |
| gdp_gap_usd_wb | 4.68 |
| rating_10 (β₂) | 1.14 |
| log_distance | 1.11 |
| same_language | 1.07 |

**Implication for the headline spec.** The redesigned headline model keeps only `gdp_gap_usd_wb`
as the broad economic prosperity control, plus the two bilateral gravity frictions
`log_distance` and `same_language`. Salary gap and price-level gap move to robustness. This avoids
making a fragile salary-specific story the centre of the project while still controlling for
economic differences between origin and destination.

**Alternative if more modelling is needed.** A later version could replace the monetary gaps with a
single standardized income/cost index, for example
`z(gdp_gap) + z(earnings_gap) - z(price_level_gap)`. That would be statistically tidy, but it adds a
constructed index whose weights need justification. For the final narrative, GDP gap is simpler:
it is a broad prosperity control, not a claimed causal pull factor.

**Institution quality (β₃) — now estimated.** QS World University Rankings 2023 give university +
country + an overall score but no city. To attach quality to destination *cities* without fuzzy-
matching the ~5,200 messy Erasmus institution names, each ranked European university is geocoded
(Nominatim, country-filtered) and **snapped to the nearest Erasmus receiving city** (≤35 km, using
`city_coordinates.csv`); `institution_quality = best QS score among universities in the city` (0 if
none ranked). This yields 143 cities (173 universities snapped). Added to the complete PPML (Spec J):

| term | β | p | effect / 1 SD |
|------|---|---|----------------|
| **β₃ institution quality** | **+0.0122** | **<0.001** | **+27.8%** (strongest driver) |
| β₂ QoL (Erasmusu rating) | +0.159 | <0.001 | +11.4% |
| language affinity | +0.179 | 0.002 | +8.6% |

(Headline Spec J-main uses `gdp_gap_usd_wb` as the single broad-prosperity control;
`earnings_gap` and `price_level_gap` are demoted to Spec J-robust because the three monetary
terms have pairwise VIF ≈ 5–7.)

β₃ is the **largest and most significant** term, with a clean VIF (1.08 — not collinear with QoL).
Caveats: a single year (2023, time-invariant like QoL, so it cannot enter the pair-FE panel — a
yearly QS series would be needed for that); geocoding occasionally snaps to a suburb/branch campus
(e.g. Imperial→Westminster, TUM→Garching), adding mild city-assignment noise.

### Cross-check: expert (QS) vs user (StudyPortals) institution quality

β₃ is measured two independent ways, mirroring the two-proxy QoL design:

| β₃ source | construction | Spec | β | p |
|-----------|--------------|------|---|---|
| **QS World 2023** (expert/metric) | best QS overall score per city, geocoded → city | J | +0.013 | <0.001 (+29%/SD) |
| **StudyPortals** (student/user) | best student star score (/5) per city, scraped via Wayback (Cloudflare-gated live) | K | +0.094 | 0.002 (+9.8%/pt) |

The two measures correlate only **0.31** across the 56 overlapping cities — they are *not*
redundant (prestige/research metrics vs lived student experience; e.g. Budapest, Lausanne and Vienna
top the student score, which is not the QS prestige order). Yet **both independently and
significantly predict Erasmus flows**, so the institution-quality effect is **robust to how quality is
measured** — expert ranking and crowd ratings agree on the *direction and significance* even while
disagreeing on the *ranking*. QS remains the recorded headline β₃ (denser coverage, 143 cities vs
StudyPortals' student-scored subset); StudyPortals is the user-based confirmation.

### Key finding: institution quality partly explains the quality-of-life effect

Adding β₃ to the model **attenuates β₂ by ~40%** — the QoL (Erasmusu rating) coefficient falls from
**+0.271** (Spec I, QoL + economics + distance + language) to **+0.159** (Spec J-main, same model
plus institution quality), while both stay significant at p<0.001.

| spec | controls | β₂ QoL | β₃ inst. quality |
|------|----------|--------|------------------|
| I | economics, distance, language | **+0.271** | not in model |
| J-main | + institution quality (gdp_gap only) | **+0.159** | +0.012 (p<0.001) |

Interpretation: the two are **not collinear** (β₃ VIF = 1.08; the raw city-level correlation between
Erasmusu rating and best-QS-score is low), so this is *not* a multicollinearity artefact — it is a
genuine **mediation/omitted-variable story**. Top-ranked universities cluster in cities that also
score well on liveability, so a regression *without* institution quality lets β₂ pick up part of the
**academic pull** that properly belongs to β₃. Once institution quality is in the model, the QoL
coefficient measures liveability *net of* university prestige and shrinks accordingly.

Substantive takeaway: roughly **two-fifths of the apparent "quality-of-life pull" on Erasmus flows
was actually academic pull**. Both effects are real and significant, but institution quality is the
stronger and previously-omitted driver — a concrete payoff from estimating β₃ rather than leaving it
as a designed-only term. (Direction of control matters here: this is an identification result from
*adding a regressor*, distinct from the FE/clustering knobs discussed above.)

VIF > 5 flags collinearity. The **monetary gaps are collinear** (≈4.7–6.9): their individual
insignificance reflects shared variance, not absence of an income/cost effect — they belong in the
model as controls regardless of their t-stats. By contrast **β₂ QoL, distance and language are
clean** (VIF ≈ 1.1), so their estimates stand on their own: QoL and language are genuinely
significant, and distance's flatness is *not* a collinearity artefact — it is the sender-country FE
absorbing origin location plus the popular-distant-destination sample. **Reporting stance: keep all
controls in** (standard gravity practice — controls guard against omitted-variable bias, they need
not be individually significant); only β₂ and language affinity are claimed as identified signals.

## Reporting stance and interpretation

β₂ (quality of life) is **consistently positive across two independent text/web sources**
(Reddit, Erasmusu) and across specifications. Headline reading:

> Destination QoL is **strongly and significantly associated** with Erasmus flows
> cross-sectionally across countries (Erasmusu β≈+0.15, p<0.001; ≈+16% flow per rating point),
> but the association **weakens once we demand within-country identification** (receiving-country
> FE, p≈0.12–0.27). The QoL↔flow link sits mainly at the **country** level. Three caveats:
> (i) the cross-country signal also carries country wealth, popularity, language, university
> count, visa ease — QoL is associated, not isolated; (ii) the within-country null may be low
> power, not true absence (few rated cities per country, two proxies correlate only ~0.2);
> (iii) Erasmus choice is institutionally constrained — students go where their home university
> has a bilateral agreement, which structurally flattens within-country city effects.

The defensible empirical claim is a **robust positive cross-sectional association**, not a
causal effect.

## Panel gravity (2014–2023) and the two-stage QoL test

With the multi-year Väisänen panel we add a proper panel gravity and a two-stage design, because
QoL is **time-invariant** (yoy infeasible: Reddit too sparse per year, Erasmusu has only a
cumulative rating, Wayback would still return a running average). A pair/destination-FE panel
absorbs static QoL, so QoL cannot enter the panel directly — instead:

- **Stage 1 — panel PPML** on the country×country×year panel (10,176 pair-years), with origin,
  destination, and year fixed effects. The structure validates cleanly: year FEs rise 2015→2019,
  show a **COVID dip in 2020 (−0.17)**, and recover from 2021. The destination FEs are a
  noise-averaged, multi-year measure of each destination's pull.
- **Stage 2 — cross-sectional**: regress the estimated destination attractiveness FEs on static QoL
  (+ destination economics).

**Granularity matters (and we go city-level).** Run at the **country** level, Stage 2 is
underpowered and null: only ~25–30 destination countries, QoL insignificant and unstably signed
(Erasmusu β=−0.42, p=0.69; Reddit β=−1.23, p=0.35). This is *not* the right test — it repeats the
coarse country aggregation we already rejected, and a country destination-FE bakes in size and
popularity that country-mean QoL does not track. The QoL signal we found lives at the **city**
level, so the two-stage must use **city destination FEs** (LAU city panel) matched to the ~322
Erasmusu city ratings (N in the hundreds). [Bridging LAU codes to city names is built from the
Väisänen individual file, which carries both `dest_LAU` and `Receiving city`.]

**City-level two-stage (causal-adjacent support).** Building the city-year HE-study panel from the Väisänen
individual file (130,968 origin×city×year rows, 2014–2023), Stage 1 PPML with origin + city-
destination + year FE yields **282 city attractiveness FEs** (restricted to Erasmusu-matched
cities). Stage 2 regresses these on the Erasmusu rating (opinion-weighted, country-clustered):

| Two-stage level | N | β(rating) | cluster-by-country p |
|-----------------|---|-----------|----------------------|
| Country | 25 | −0.42 | 0.69 (null) |
| **City** | **282** | **+0.79** | **<0.001** |

So at the committed **city** granularity, multi-year destination pull is **strongly and
significantly** explained by quality of life (robust to country clustering). The country-level null
was the wrong aggregation (N=25, destination FE already absorbing size/popularity). This is the
strongest QoL support result: a noise-averaged, panel-based destination-pull measure that
Erasmusu QoL explains at p<0.001. It supports the pull-factor narrative, but it is still a
second-stage association rather than a causal estimate.

**Takeaway:** the panel confirms the gravity *structure* and historical dynamics (COVID dip), and
its **city-level** two-stage delivers the robust QoL-attractiveness association; the country-level
version is underpowered and not the right test.

## Time-varying panel terms (OWID) — the multi-year QoL we *could* run

The Reddit/Erasmusu QoL and the QS/StudyPortals institution measures are all **time-invariant**, so
they only enter the cross-section. Our World in Data publishes open, **country-year** series that
vary over time, so they can enter the panel PPML directly. With additive **origin + destination +
year** fixed effects, a destination-year regressor is identified from how a destination moves
*relative to its own mean and the common year trend* — i.e. within-destination over time. This is
the multi-year QoL test that was infeasible at city level (Reddit too sparse per year; Erasmusu only
cumulative).

| OWID term | role | β | p (dest-clustered) | per-SD |
|-----------|------|---|--------------------|--------|
| **Life satisfaction** (Cantril ladder) | time-varying β₂ QoL | **+0.227** | **0.035** | **+18.5%** |
| Education spending (% GDP) | time-varying β₃ proxy | −0.035 | 0.161 | −4.1% |

**Finding — life satisfaction is a significant time-varying QoL driver.** As a destination's
self-reported life satisfaction rises over time (net of destination and year effects), its Erasmus
inflows rise (+18.5% per SD, p=0.035). This is the **only** specification in the project where a
QoL measure is identified *over time* rather than cross-sectionally, and it agrees in sign and
significance with the cross-sectional Erasmusu/Reddit results — a genuine multi-year corroboration of
β₂, just at country (not city) granularity.

**Null — education spending %GDP does not work as a time-varying β₃.** Insignificant and
wrong-signed: spending-as-%-of-GDP is a noisy *input* proxy (the ratio can rise precisely when GDP
falls), its within-country-over-time variation is small, and it does not track the *output* quality
that QS/StudyPortals capture cross-sectionally. So institution quality remains a **cross-sectional**
result (QS +29%/SD, StudyPortals p=0.002); we could not recover it as a time-varying term.

Caveats: OWID terms are **country-level**, coarser than the city granularity where the QoL/quality
signal is strongest; life-satisfaction coverage thins for a few small states and early years; and
additive FE (not origin×year / pair FE) is a lighter identification than full structural gravity —
treated as exploratory, directionally consistent evidence rather than a causal estimate.

## COVID-2020 sector DiD on field-level flows

The exploratory part of the project culminates in a focused event study: a real,
date-pinned shock applied to the (origin, destination, **ISCED-F broad field**, year)
flow panel. Each ISCED-F broad field is mapped to one NACE Rev2 sector (broad and
judgmental — Education→P, Arts→R, Business/Law→K, Sciences→M, ICT→J, Engineering→C,
Agriculture→A, Health→Q, Services→I; see `src/erasmusgravity/fields.py`). The
treatment intensity is the **2020 LCI deviation from each (country, sector)'s
2015–2019 baseline** (`covid_hit_pp`, more negative = harder hit). Turkey is dropped
(hyperinflation distortion). Specification:

```
flow_{ijft} ~ exp( beta * covid_hit_{j, s(f)} * Post_t
                 + alpha_{jf}   (destination x field FE)
                 + sigma_i      (sending FE)
                 + tau_t        (year FE) )                   (PPML)
```

268 (destination, field) cells, 39 origins, 2014–2023, ~46k cell-years.
Standard errors clustered by (destination, field).

**Headline DiD:** `beta = -0.0056, p = 0.10, ~-1.9% per SD`. Borderline.

**Event study (real story):**

| year | β(covid_hit × year) | p (cell-clustered) |
|------|---------------------|--------------------|
| 2015 | +0.0014 | 0.63 |
| 2016 | -0.0002 | 0.89 |
| 2017 | +0.0017 | 0.18 |
| 2018 | +0.0016 | 0.075 |
| **2020** | **−0.0103** | **0.004 ★** |
| **2021** | **−0.0047** | **0.012 ★** |
| 2022 | −0.0039 | 0.14 |
| 2023 | −0.0076 | 0.059 |

Three things to take from this:

1. **Parallel pre-trends hold.** 2015–2018 placebo coefficients are tiny and
   insignificant — the identification assumption passes. The DiD is methodologically
   sound.
2. **A genuine shock is identified at 2020–2021.** Sharp, large break in 2020
   (p=0.004) carrying into 2021 (p=0.012), fading by 2022. Exactly the event-study
   shape COVID would produce.
3. **The sign is counterintuitive — and that's an interpretation, not a failure.**
   `β < 0` combined with negative covid_hit_pp implies hard-hit cells had *higher*
   relative flow in 2020–2021, opposite to the "students avoid hit sectors"
   prior. The most likely explanation is that **2020 LCI is contaminated by
   wage-subsidy schemes** (e.g. the Netherlands NOW scheme produced LCI +30pp in
   accommodation — a measurement artifact, not a wage gain). Subsidy intensity
   correlates with lockdown severity, which crushed overall inbound mobility, so the
   coefficient is really picking up **country lockdown intensity proxied through
   LCI distortion**, not a sector→field channel.

So the data delivers the **right econometric structure** (parallel pre-trends, sharp
2020–2021 break, fade-out) but the **wrong channel measure** to interpret a sector
mechanism. A cleaner replication needs an **employment-based** hit (e.g. 2020 sector
employment deviation by NACE), which isn't distorted by wage subsidies. This is
documented honestly as a limitation rather than a finding about field-level
sensitivity to sector wages.

### Employment-based replication

`scripts/build_covid_employment_hit.py` produces `covid_emp_hit_pp` from Eurostat
`lfsa_egan2` (annual employment by NACE letter), with the same 2020-deviation-from-
2015–2019-baseline construction as the LCI version. `fit_covid_did_employment()` in
`run_regression.py` re-runs the same FE specification with this measure on
49,202 cell-years (328 destination×field cells, 39 origins, 2014–2023, Turkey dropped).

| Spec | Headline β | p | Per-SD effect | 2020 event-study β (p) |
|------|------------|---|---------------|-------------------------|
| LCI (wage) | −0.00555 | 0.10 | −1.9% | **−0.0103 (p=0.004 ★)** |
| LFS (employment) | +0.0184 | 0.95 | +0.1% | +0.378 (p=0.14, n.s.) |

The sign **flips back to positive** under the employment measure — consistent
with the prior that hard-hit sectors lose flows (covid_emp_hit_pp < 0 = harder
hit, and β > 0 with negative hit ⇒ negative effect on flow). But the entire
event-study series is statistically indistinguishable from zero — no significant
year, no parallel-pre-trend pattern.

Read together, the two specifications tell a clearer story than either alone:

- The **shape** of the LCI event study (clean placebos, sharp 2020 break,
  persistence into 2021, fade by 2022) is real. Something happened in 2020 that
  the LCI series detected.
- The **channel** the LCI series detected was **not** sector-specific damage to
  flows. When we swap to employment — which is not contaminated by wage subsidies
  — the signal disappears at the ISCED-broad-field-to-NACE-letter resolution.
- Conclusion: COVID's mobility shock on Erasmus was overwhelmingly
  **lockdown-wide**, not field-selective. The 2020 dip in the year-FE panel
  picks up the level effect; the LCI DiD was identifying the same lockdown
  intensity through a contaminated proxy, not a sector-of-study channel.

Honest framing in the dashboard's *Time & Shocks* section overlays both event
studies and states this conclusion in the Evidence card.

