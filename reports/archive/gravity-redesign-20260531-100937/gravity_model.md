# A Gravity Model of Erasmus Student Flows

Methodology note for the final report: the gravity framework, its literature, and how we adapt
it to explain Erasmus Higher Education mobility between origin and destination.

## 1. The gravity model

The gravity model borrows Newton's law of gravitation: the interaction between two bodies grows
with their "masses" and falls with the distance between them. Tinbergen (1962) first applied it
to bilateral trade; it is now the workhorse for any bilateral flow — trade, migration, capital,
and student mobility. In its canonical multiplicative form, the flow from origin *i* to
destination *j* is

```
Flow_ij = G · (M_i^α · M_j^β) / D_ij^θ
```

where `M_i`, `M_j` are origin/destination "masses" (size, income, capacity) and `D_ij` is a
friction (distance, and by extension language, borders, cost). Taking logs gives a linear,
estimable form.

## 2. Structural gravity and multilateral resistance

Anderson & van Wincoop (2003) gave the model microfoundations and showed that bilateral flows
depend not only on `i`–`j` frictions but on each side's friction relative to *all* partners —
**multilateral resistance**. The practical implication, which we follow, is that
**origin and destination fixed effects** should absorb these multilateral-resistance terms and
all other origin- or destination-specific levels (size, wealth, overall popularity).

This is exactly the tension in our results: destination fixed effects are theoretically correct,
but they also absorb most of the destination-level quality-of-life variation we want to study
(see §6 and `qol_methodology_notes.md`).

## 3. Estimation: log-OLS vs PPML

### Why `log(1 + flow)` for the baseline

1. **Linearises the multiplicative model.** Gravity is multiplicative (§1); logs turn it additive,
   so `log Flow = log G + α log M_i + β log M_j − θ log D` is estimable by OLS.
2. **Coefficients read as % effects.** With a log outcome, a coefficient β is a semi-elasticity —
   roughly a `100·β %` change in flow per unit of the regressor (e.g. "+16% per Erasmusu point").
3. **Tames extreme skew.** Flows span 1–5 up to >11,000; logging stops a few huge corridors from
   dominating the fit and stabilises the error variance.
4. **The `+1` keeps zeros.** `log(0)` is undefined, but many origin→city pairs have zero students;
   `log(1+flow)` maps 0→0 so those pairs stay in the sample.

### Why it is only a baseline

The textbook approach log-linearises and estimates with OLS. Santos Silva & Tenreyro (2006),
"The Log of Gravity," show this is **biased** under heteroskedasticity (by Jensen's inequality,
`E[ln y] ≠ ln E[y]`) and cannot handle zero flows. Their recommended estimator is
**Poisson Pseudo-Maximum-Likelihood (PPML)**, run on the flow *level* (not its log), which is
consistent under heteroskedasticity and admits zeros.

The `+1` that lets us keep zeros is itself **arbitrary** — its value affects the estimate and
biases results when zeros are common, which is part of the same critique.

For this project we report descriptive `log(1 + flow)` OLS as the baseline (transparent, easy to
read), and PPML as the correct estimator for the headline numbers (Spec H: Erasmusu rating
β≈+0.28, ≈+32% per point, p<0.001). Our substantive conclusions (sign and rough magnitude of QoL)
do not flip between the two.

## 4. Gravity applied to student / Erasmus mobility

- **Rodríguez González, Bustillo Mesanza & Mariel (2011)** estimate a gravity model directly on
  Erasmus flows: distance, cost of living, university quality, country size, and language all
  matter. Closest precedent to our specification.
- **Beine, Noël & Ragot (2014)** model international student mobility with gravity, highlighting
  tuition/cost, network effects, and destination university quality.

Both treat student mobility as a gravity process driven by destination *pull* (quality, cost,
amenities) net of *friction* (distance, language). Our quality-of-life variable extends this
pull side with a text/web-derived amenity measure not used in prior work.

## 5. Our adaptation

**Unit of analysis.** Origin country *i* → destination *j*, where *j* is a receiving country
(macro model) or a receiving city (fine model, exploiting Erasmusu/Reddit city-level QoL).

**Outcome.** `flow_ij` = number of Erasmus HE study mobilities (PPML), or `log(1+flow_ij)` (OLS
baseline).

**Specification (working macro model).**

```
E[flow_ij] = exp(
      β1 · salary_gap_ij          # Eurostat net earnings (pull: labour-market return)
    + β2 · quality_of_life_j      # Erasmusu rating (primary) / Reddit sentiment (secondary)
    + β3 · institution_quality_j  # QS World 2023 score, snapped to destination city
    + γ1 · distance_ij            # friction: log great-circle distance
    + γ2 · language_affinity_ij   # friction: shared language family
    + δ_i                         # origin fixed effects (multilateral resistance, size)
)
```

`gdp_gap_ij` and `price_level_gap_ij` are **not** in the headline specification — they enter
the robustness block only. They proxy the same rich-vs-poor-destination dimension as
`salary_gap_ij` (VIFs 5–7 in the full-controls PPML) and are reported as exploratory rather
than identifying. See `qol_methodology_notes.md` for the VIF table and the parked
"collapse the monetary gaps" alternative.

**Quality of life (β₂)** is the project's text/spatial contribution, from two independent
sources treated separately (they correlate only ~0.2):
- **Erasmusu.com** per-city rating (0–10, dense — up to ~1,400 opinions/city): primary measure.
- **Reddit r/Erasmus** sentiment via OpenRouter/DeepSeek + Pydantic extraction: secondary,
  also yields theme breakdown (cost, housing, academics, safety, …).

**Identification choice.** Two readings, and we adopt the first as the working macro model:
- **Cross-sectional gravity (adopted):** origin FE only; destination economics controlled by the
  gap covariates. QoL is an *absolute* destination attractiveness level, compared across all
  destinations (Milan vs Berlin). Strong, significant QoL association (β≈+0.15, p<0.001).
- **Two-way FE (robustness):** add destination FE; QoL identified only *within* country across
  cities. Theoretically cleaner for multilateral resistance, but absorbs most QoL variation, so
  the estimate is faint. Reported as a conservative robustness check.

This is an **association**, not a causal estimate: without destination FE, popularity and
unobserved destination quality are only partly netted out by the gap controls. Causal
identification would need an instrument or a natural experiment, which the rubric's step-3
design only requires us to *describe*.

## 6. Why we prefer the macro (cross-sectional) reading

Most of the QoL↔flow relationship is **cross-country**: higher-quality, higher-amenity
destinations receive more students. Demanding within-country identification throws this away and
leaves a faint within-city signal. For a descriptive macro model of where Erasmus students go,
the cross-sectional gravity specification answers the research question directly, and its QoL
coefficient is robust in sign and significance across both data sources.

## References

- Tinbergen, J. (1962). *Shaping the World Economy.* Twentieth Century Fund.
- Anderson, J. E., & van Wincoop, E. (2003). Gravity with Gravitas. *American Economic Review*,
  93(1), 170–192.
- Santos Silva, J. M. C., & Tenreyro, S. (2006). The Log of Gravity. *Review of Economics and
  Statistics*, 88(4), 641–658.
- Rodríguez González, C., Bustillo Mesanza, R., & Mariel, P. (2011). The determinants of
  international student mobility flows: the Erasmus programme. *Higher Education*, 62(4), 413–430.
- Beine, M., Noël, R., & Ragot, L. (2014). Determinants of the international mobility of students.
  *Economics of Education Review*, 41, 40–54.
# Gravity Model Notes

Working notes for the report section that motivates the ErasmusGravity regression design.

## Baseline

The project treats Erasmus mobility as a gravity-style flow problem:

```text
flow_ij = f(origin push, destination pull, bilateral friction)
```

The implemented empirical version uses Higher Education study-mobility flows and keeps the
interpretation descriptive rather than causal.

## Preferred Estimator

The original step-3 design was written as `log(1 + flow_ij)`. The report should explain that
gravity applications usually prefer Poisson Pseudo-Maximum-Likelihood (PPML), following Santos
Silva and Tenreyro (2006), because PPML handles zero flows and heteroskedasticity more cleanly than
log-OLS.

## Variables

- `β1`: salary gap from Eurostat net earnings.
- `β2`: quality of life from Reddit/Erasmusu destination sentiment and ratings.
- `β3`: institution quality from QS/StudyPortals city-level university-quality measures.
- Controls (headline): distance and language affinity (bilateral gravity frictions).
- Robustness only: GDP gap, price-level gap — exploratory; collinear with `salary_gap`.
- Fixed effects: sending-country and receiving-country terms where the identifying variation allows.

## Interpretation

The model is exploratory. Coefficients are read as structured descriptive associations, not causal
effects. Receiving-country fixed effects absorb broad destination popularity, but time-invariant
destination variables such as country-level quality of life or university rankings cannot be
identified in the same specification unless they vary below the country level.

## Variable definitions

### Outcome

| Symbol | Definition | Used in |
|---|---|---|
| `flow_count` | KA1 Erasmus HE study mobilities, count of students from origin `i` to destination city/country `j` | PPML specs (H, I, J, K, panel, COVID DiD) |
| `y` | `log(1 + flow_count)`. The `+1` keeps zero-flow pairs in the sample; biased under heteroskedasticity (Santos Silva & Tenreyro 2006) but transparent as a baseline. | OLS/WLS specs (A, B, C, D, E, F, G) |

### Economic gaps (β₁ family)

| Variable | Construction | Source |
|---|---|---|
| `earnings_gap` | `(net_earnings_j − net_earnings_i) / 1000`, in €1,000 units so the PPML coefficient reads as "% per €1k of gap" | Eurostat `earn_nt_net` (Structure of Earnings Survey) |
| `gdp_gap` | `gdp_pc_i − gdp_pc_j`, EUR per capita | Eurostat `nama_10_pc` |
| `gdp_gap_usd_wb` | World Bank GDP per capita gap, USD (cross-check against Eurostat) | World Bank WDI |
| `price_level_gap` | `pli_j − pli_i`, where `pli` is the Eurostat Actual Individual Consumption price-level index, EU27 2020 = 100 | Eurostat `prc_ppp_ind` |

### Quality-of-life (β₂ family)

| Variable | Construction | Source |
|---|---|---|
| `rating_10` | Mean Erasmusu opinion score (0–10 scale), city-level, with `n_opinions ≥ 5` filter. Opinion-weighted in WLS specs. | Erasmusu.com |
| `n_opinions` | Number of opinions per city; used as WLS weight on `rating_10`. | Erasmusu.com |
| `qol_city` | Reddit per-city sentiment: weighted mean of mention sentiment scores with weights `confidence × log(1 + upvotes) × age_weight`, where `age_weight = exp(−ln 2 / 365d · age_sec)` (1-year EWMA half-life). | r/Erasmus → DeepSeek (OpenRouter) → Pydantic schema |
| `qol_country` | Same EWMA aggregator as `qol_city` but rolled up to receiving country. | r/Erasmus |
| `qol_combined` | `z(rating_10)` where available, else `z(qol_city)`, else `z(qol_country)` — z-scores combined with Erasmusu first, Reddit-city second, Reddit-country fallback. | derived |
| `life_satisfaction` | Cantril ladder (0–10), receiving country, panel year. | OWID / Gallup World Poll |

The two QoL sources are deliberately kept independent: Erasmusu rates city *liveability*; Reddit
captures unstructured *discussion sentiment*. They overlap on 103 cities with `corr ≈ 0.22`,
confirming they are not redundant.

### Institution quality (β₃ family)

| Variable | Construction | Source |
|---|---|---|
| `inst_quality` | `best_score`: maximum QS overall score (0–100) of any QS-ranked university within ~35 km of the destination city. `0` if no QS-ranked institution within radius. | QS World University Rankings 2023 |
| `user_inst_quality` | Analogue of `inst_quality` using StudyPortals student review scores. Cross-check on β₃ from the user side rather than the expert/metric side. | StudyPortals |

### Bilateral frictions (gravity controls)

| Variable | Construction | Source |
|---|---|---|
| `log_distance` | `ln(haversine(origin centroid → destination city centroid))`, km. Falls back to receiving-country centroid when city coordinates are missing. | `erasmusgravity.geo.country_distance` |
| `same_language` | Indicator equal to 1 if origin and destination share a language family (Romance / Germanic / Slavic / …), 0 otherwise. | `erasmusgravity.geo.same_language_family` |

### Panel and shock terms

| Variable | Construction | Source |
|---|---|---|
| `edu_spend_gdp` | Public education spending as % of GDP, receiving country. | OWID |
| `covid_hit_pp` | `Δ_2020 LCI wage growth − mean(Δ LCI growth, 2015–2019)`, percentage points, by `(country, NACE sector)`. Subsidy-contaminated: wrong-channel sign by design. | Eurostat `lc_lci_r2_a` |
| `covid_emp_hit_pp` | Same construction as `covid_hit_pp` but on employment levels rather than wages. Clean channel: students should avoid harder-hit sectors. | Eurostat `lfsa_egan22d` |
| `post` | Indicator: `1` if `year ≥ 2020`, else `0`. | derived |

## Specifications

```text
Spec A     y ~ earnings_gap + price_level_gap + gdp_gap_usd_wb
                + C(sending_code) + C(receiving_code)               [full FE OLS; QoL not identifiable]

Spec B     y ~ earnings_gap + price_level_gap + gdp_gap_usd_wb + qol
                + C(sending_code)                                   [sender FE only; country-level QoL]

Spec C     y ~ qol_city + C(sending_code) + C(receiving_code)       [Reddit, within-country identification]

Spec D     y ~ rating_10 + C(sending_code) + C(receiving_code)
                  WLS weight = n_opinions                           [Erasmusu, within-country]

Spec E     y ~ qol_combined + C(sending_code) + C(receiving_code)   [combined QoL, within-country]

Spec F     y ~ rating_10 + earnings_gap + price_level_gap + gdp_gap_usd_wb
                + C(sending_code),  WLS weight = n_opinions         [cross-sectional Erasmusu]

Spec G     y ~ qol_combined + earnings_gap + price_level_gap + gdp_gap_usd_wb
                + C(sending_code)                                   [cross-sectional combined]

Spec H     flow_count ~ rating_10 + earnings_gap + price_level_gap + gdp_gap_usd_wb
                      + C(sending_code)                  PPML       [HEADLINE: Erasmusu PPML]

Spec I     flow_count ~ rating_10 + earnings_gap + price_level_gap + gdp_gap_usd_wb
                      + log_distance + same_language + C(sending_code)
                                                          PPML       [full gravity frictions]

Spec J-main    flow_count ~ rating_10 + earnings_gap + log_distance + same_language
                          + inst_quality + C(sending_code)
                                                          PPML       [β₁ β₂ β₃; drops collinear gaps]

Spec J-robust  flow_count ~ rating_10 + earnings_gap + price_level_gap + gdp_gap_usd_wb
                          + log_distance + same_language + inst_quality + C(sending_code)
                                                          PPML       [exploratory, VIF ~5–7]

Spec K     flow_count ~ rating_10 + earnings_gap + price_level_gap + gdp_gap_usd_wb
                      + log_distance + same_language + user_inst_quality + C(sending_code)
                                                          PPML       [β₃ = StudyPortals]

Panel year-FE   flow_count ~ C(sending_code) + C(receiving_code) + C(year)
                                                          PPML
                Two-stage: dest_fe ~ qol_combined + receiver_gdp_pc + receiver_price_level

Panel time-varying   flow_count ~ best_score(t) + C(sending_code) + C(dest_id) + C(year)
                                                          PPML       [QS multi-year edition panel]

COVID DiD (wages)        flow_count ~ covid_hit_pp:post
                                    + C(sending_code) + C(dest_id, field) + C(year)   PPML
COVID DiD (employment)   flow_count ~ covid_emp_hit_pp:post + same FE structure       PPML
```

### Reading the coefficients

- **PPML** (`flow_count ~ exp(…)`): the coefficient `β` is a semi-elasticity. The natural-unit
  effect of a change `Δx` in the regressor on flows is `100 · (exp(β · Δx) − 1)` percent. This is
  what the dashboard's "Effect" cards render (e.g. β on `earnings_gap` × 1 → "% change in flow per
  €1k of gap"). The estimator is consistent under heteroskedasticity and admits zero flows
  (Santos Silva & Tenreyro 2006).
- **OLS / WLS on `log(1 + flow)`**: `β` ≈ semi-elasticity at small flows; biased under
  heteroskedasticity. Reported as baseline only; specs A–G are not the headline numbers.
- **Standard errors**: cluster-robust on city (Specs C–G), and HC1 robust otherwise. Where
  it matters, both city-level and country-level cluster SEs are persisted side by side, since
  Reddit-city sentiment can be highly correlated within a country.
