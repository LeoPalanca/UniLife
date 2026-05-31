# A Gravity Model of Erasmus Student Flows

Methodology note for the final report: the gravity framework, the preferred descriptive
specification, and the causal-adjacent panel design for pull-factor interpretation.

## 1. Gravity Framework

The gravity model treats student mobility as a bilateral flow: movement from origin `i` to
destination `j` rises with origin/destination "mass" and falls with bilateral friction. In its
canonical form:

```text
Flow_ij = G * (M_i^alpha * M_j^beta) / D_ij^theta
```

For Erasmus mobility, destination mass is not only economic size. It also includes perceived
quality of life, academic/institutional attractiveness, language familiarity, and existing
mobility networks.

The structural gravity literature also warns that origin and destination fixed effects absorb
multilateral resistance: each origin's and destination's position relative to all alternatives.
That is useful for controls, but it creates a tension for this project because destination fixed
effects also absorb most time-invariant destination pull factors.

## 2. Estimator

The original course design used:

```text
log(1 + flow_ij)
```

That remains useful as a transparent baseline, but the headline gravity estimator is **PPML**
(Poisson Pseudo-Maximum-Likelihood), following Santos Silva and Tenreyro (2006). PPML is preferred
because it estimates the flow count directly, handles zero flows, and is more robust to
heteroskedasticity than log-OLS.

PPML coefficients are semi-elasticities:

```text
% effect = 100 * (exp(beta * change_in_x) - 1)
```

All headline coefficients should be interpreted as **descriptive associations**, not causal
effects.

## 3. Preferred Descriptive Specification

The redesigned headline model uses one broad economic control, not three overlapping monetary
gaps:

```text
E[flow_ij] = exp(
      beta2 * quality_of_life_j
    + beta3 * institution_quality_j
    + gamma1 * gdp_gap_ij
    + gamma2 * log_distance_ij
    + gamma3 * language_affinity_ij
    + origin_FE_i
)
```

Operationally:

```text
flow_count ~ rating_10
           + gdp_gap_usd_wb
           + log_distance
           + same_language
           + inst_quality
           + C(sending_code)
```

`gdp_gap_usd_wb` should be scaled to `$1,000` units in tables so the coefficient is readable.
It is a **broad destination-prosperity control**, not the main pull-factor result.

The substantive pull-factor interpretation comes from:

- `rating_10`: perceived quality of life / student city liveability;
- `inst_quality`: academic/institutional attractiveness;
- `same_language`: familiar language environment;
- `log_distance`: standard gravity friction;
- `gdp_gap_usd_wb`: broad economic prosperity control.

## 4. Economic Controls: What Not To Overinterpret

The old headline model put `earnings_gap`, `gdp_gap_usd_wb`, and `price_level_gap` in the same
controls block. That is not a clean design because all three proxy the same rich-destination
dimension. The result was unstable and hard to explain.

The redesigned stance is:

- headline control: `gdp_gap_usd_wb`, as a broad prosperity gap;
- robustness only: `earnings_gap`, because its sign is awkward and salary-specific interpretation
  is fragile;
- robustness only: `price_level_gap`, because cost of living is highly correlated with GDP and
  earnings.

Do not describe GDP gap as a causal economic pull effect. It is included to avoid attributing
general prosperity differences to quality of life or institution quality.

## 5. Quality Of Life And Institution Quality

Quality of life is measured with two independent sources:

- **Erasmusu city ratings** (`rating_10`): the primary regression proxy, denser city coverage;
- **Reddit r/Erasmus sentiment/themes** (`qol_city`, `qol_country`): the course text-analysis
  contribution and qualitative evidence layer.

The Reddit and Erasmusu measures should be reported separately rather than merged into one
headline index. They capture different constructs: structured city ratings versus unstructured
discussion sentiment.

Institution quality is measured as:

```text
inst_quality = best QS overall score within ~35 km of the Erasmus destination city
```

It should be interpreted as **academic/institutional attractiveness**, not pure teaching quality.
Highly ranked universities may also be larger, more visible internationally, and connected to
denser Erasmus partnership networks.

`user_inst_quality` from StudyPortals is a robustness cross-check for beta3. For consistency, it
should mirror the preferred model and only swap the institution-quality measure:

```text
flow_count ~ rating_10
           + gdp_gap_usd_wb
           + log_distance
           + same_language
           + user_inst_quality
           + C(sending_code)
```

## 6. Causal-Adjacent Pull-Factor Design

The cross-sectional PPML model is descriptive because destination popularity, bilateral Erasmus
agreements, university capacity, and unobserved city attractiveness remain confounders.

The closest causal-adjacent design in the current project is the time-varying panel:

```text
flow_ijt ~ life_satisfaction_jt
         + C(sending_code)
         + C(receiving_code)
         + C(year)
```

This design is stronger because it asks whether **within-destination changes over time** in life
satisfaction are associated with Erasmus flows, while controlling for:

- permanent origin differences;
- permanent destination differences;
- common year shocks.

It still does not prove causality. A causal claim would require a natural experiment, instrument,
or policy shock that changes one pull factor without directly changing Erasmus flows through other
channels.

## 7. Specification Map

Use this smaller set in the report narrative:

```text
Preferred descriptive PPML:
  flow_count ~ rating_10 + gdp_gap_usd_wb + log_distance + same_language
             + inst_quality + C(sending_code)

Institution-quality cross-check:
  flow_count ~ rating_10 + gdp_gap_usd_wb + log_distance + same_language
             + user_inst_quality + C(sending_code)

Within-country QoL robustness:
  y ~ rating_10 + C(sending_code) + C(receiving_code)
  y ~ qol_city + C(sending_code) + C(receiving_code)

Causal-adjacent panel:
  flow_count ~ life_satisfaction + C(sending_code) + C(receiving_code) + C(year)
```

Treat these as appendix/diagnostic only:

- old salary/GDP/price full-controls models;
- log-OLS/WLS versions A-G;
- QS multi-year panel, because QS scores barely vary within city over time;
- education-spending panel, because it is a weak proxy for university quality;
- COVID sector DiD, because it answers a different research question.

## 8. Reporting Language

Recommended wording:

> Erasmus flows are descriptively larger toward destinations with stronger institutions, better
> perceived quality of life, and familiar language environments, conditional on broad destination
> prosperity and distance. These estimates are associations, not causal effects.

For the causal-adjacent result:

> The time-varying life-satisfaction panel provides stronger, but still non-causal, evidence
> because it relies on changes within destinations over time rather than only cross-sectional
> differences between destinations.

## References

- Tinbergen, J. (1962). *Shaping the World Economy.* Twentieth Century Fund.
- Anderson, J. E., & van Wincoop, E. (2003). Gravity with Gravitas. *American Economic Review*,
  93(1), 170-192.
- Santos Silva, J. M. C., & Tenreyro, S. (2006). The Log of Gravity. *Review of Economics and
  Statistics*, 88(4), 641-658.
- Rodríguez González, C., Bustillo Mesanza, R., & Mariel, P. (2011). The determinants of
  international student mobility flows: the Erasmus programme. *Higher Education*, 62(4), 413-430.
- Beine, M., Noël, R., & Ragot, L. (2014). Determinants of the international mobility of students.
  *Economics of Education Review*, 41, 40-54.
