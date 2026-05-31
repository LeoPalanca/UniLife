---
title: "Economic Attractiveness and Erasmus Mobility"
subtitle: "A descriptive analysis of European student flows"
author: "Leonardo Palanca"
date: "Text Analysis and Spatial Data for Economists --- SP 2026"
geometry: "margin=2cm"
fontsize: 11pt
---

## 1. Research Question and Motivation

Erasmus mobility is jointly a spatial-flow problem and a text-as-data problem.
Students move from an origin country to a destination country or city, and the
attractiveness of a destination depends on economic conditions, institutional
quality, distance, language, and student perceptions of daily life. This project
asks:

> **What explains the size of Erasmus Higher Education mobility flows from one
> country to another, and how does the role of destination quality of life
> change over time?**

The starting point is a gravity-style view of student mobility. As with trade,
migration, and commuting flows, Erasmus flows can be described as a function of
origin conditions, destination pull factors, and bilateral frictions. The
project focuses on three destination-pull variables: a broad prosperity control
(GDP-per-capita gap), perceived quality of life, and institution quality, with
distance and language affinity as frictions. The executed analysis is
descriptive and exploratory; it does not claim causal effects.

The literature motivates this structure. Tinbergen's gravity model and the
structural gravity framework of Anderson and van Wincoop explain why bilateral
flows depend on both partner characteristics and frictions. Student-mobility
studies such as Rodríguez González, Bustillo Mesanza, and Mariel (2011) and
Beine, Noël, and Ragot (2014) apply this logic to international student flows,
emphasising distance, cost, networks, and university quality. The text layer
follows the "text as data" literature (Gentzkow, Kelly, and Taddy 2019; Grimmer
and Stewart 2013): student discussions are treated as a noisy measurement of
perceived quality of life, not as a representative survey. The PPML estimator
follows Santos Silva and Tenreyro (2006) for count-flow gravity models with
heteroskedasticity and zero flows.

This project addresses the course's project specification --- a research
question where text and spatial data are relevant, executed analysis with code
and raw data, and a description of how the results answer the question --- by
combining official Erasmus mobility data, spatial aggregation and distance
measures, an institution-quality layer from world university rankings, and a
Reddit/OpenRouter/Pydantic extraction pipeline for student destination
perceptions.

## 2. Data

The core data source is the official Erasmus+ statistical annex covering all
mobility years 2014--2023:

```text
data/raw/annual-report-2024-statistical-annex.xlsx  (sheet: HE-Learn Mobility)
```

The pipeline filters the file to Higher Education learner study mobilities,
keeps cross-border flows, and aggregates the result to origin-destination pairs
(`sending_country`, `sending_code`, `receiving_country`, `receiving_code`,
`flow_count`). The country-pair table contains 2,651 rows and 274,533 student
flows. The largest corridors include Italy → Spain, Spain → Italy, Germany →
Spain, France → Spain, and Germany → France. These flows are the backbone of
the spatial analysis. A multi-year city-level panel (2014--2023) is also built
for the temporal extension.

Supporting datasets:

- **Economic indicators**: World Bank GDP per capita, Eurostat net earnings,
  and Eurostat price-level indicators.
- **Spatial controls**: great-circle distance and shared-language-family
  affinity between origin and destination capitals.
- **Institution quality**: QS World University Rankings 2023 (and 2014, 2017,
  2018 retrieved via the Wayback Machine for the panel), geocoded with
  Nominatim and snapped to the nearest Erasmus destination city.
- **Cross-checks**: StudyPortals student ratings as a user-based
  institution-quality cross-check.
- **Temporal indicators**: OWID life satisfaction (Cantril ladder) and
  education-spending series; Eurostat Labour Cost Index (`lc_lci_r2_a`) and
  Labour Force Survey employment (`lfsa_egan2`) for the COVID-2020 sector
  shock.

The text layer uses Reddit `r/Erasmus` posts and comments. A structured
extraction pipeline calls OpenRouter/DeepSeek and parses responses with a
Pydantic schema; each extracted destination mention carries city, country,
sentiment, sentiment score, themes (cost, housing, nightlife, academics,
safety, bureaucracy, etc.), confidence, Reddit score, and permalink. The
current extracted dataset contains **980 destination mentions across 56
countries and 211 cities: 360 positive, 363 neutral, and 257 negative
mentions**. A 51-row stratified manual-validation sample
(`data/processed/reddit_manual_validation.xlsx`, 17 per sentiment class) is
provided alongside the submission so the LLM-vs-human agreement rate can be
reported. The Reddit signal is interpreted as a qualitative perception proxy,
not a representative measure of all Erasmus students.

## 3. Methods

**Spatial flow pipeline.** The Erasmus annex is filtered to the target
population, reshaped and aggregated, then joined to country-level indicators.
For each origin-destination pair the project computes monetary gaps
`gdp_gap = receiver_gdp_pc − sender_gdp_pc`,
`earnings_gap = receiver_net_earnings − sender_net_earnings`, and
`price_level_gap = receiver_price_level − sender_price_level`. Flow-weighted
destination summaries (e.g. `sum(flow × dest_gdp) / total_outflow`) describe
whether a sending country tilts toward richer or poorer destinations.

**Text pipeline.** The Reddit extraction asks the model to identify destination
mentions and classify each by sentiment and themes, with the schema mirroring
the course's LLM information-extraction assignment: explicit JSON output, a
Pydantic schema, and sentiment normalisation before aggregation. The Reddit
signal is then cross-checked against an independent two-proxy quality-of-life
construction: average per-city Erasmusu student ratings provide a parallel
text-derived destination signal (Spearman ρ ≈ 0.21 with the Reddit sentiment
score), and both proxies enter the gravity model so the estimates do not lean
on a single noisy text source.

**Gravity design (step 3).** The headline descriptive specification is a PPML
gravity model of bilateral flows:

```text
E[flow_ij] = exp(
    beta1 · gdp_gap_ij               # broad prosperity control
  + beta2 · quality_of_life_j        # Erasmusu rating (+ Reddit cross-check)
  + beta3 · institution_quality_j    # QS 2023 score, geocoded → city
  + gamma1 · log_distance_ij
  + gamma2 · same_language_ij
  + sending_country fixed effects
)
```

estimated with city-clustered robust standard errors. Salary gap and
price-level gap are kept as robustness controls rather than headline terms,
because they overlap strongly with the GDP gap (VIF ≈ 5--7 with each other) and
make the monetary block hard to interpret separately. Following Santos Silva
and Tenreyro (2006), PPML is preferred to log-OLS because it handles zero flows
and the multiplicative-error structure consistently.

**Temporal extension.** A city-year panel (2014--2023) is used to add (i) a
time-varying $\beta_2$ via OWID life satisfaction --- the Cantril ladder enters at the
country-year level so identification is within-destination over time, with
origin, destination, and year fixed effects; (ii) a time-varying $\beta_3$ via
multi-year QS rankings (2014, 2017, 2018, 2023); and (iii) a 2020 COVID
difference-in-differences at the field × NACE-sector cell level, estimated
twice --- once with Eurostat LCI wage growth (`covid_hit_pp`) and once with LFS
employment growth (`covid_emp_hit_pp`) as the treatment-intensity measure.

Estimates are reported as exploratory associations, not causal effects.

## 4. Descriptive Results

The Erasmus flow structure is highly concentrated. Spain is central in the
network --- Italy → Spain and Germany → Spain are among the largest corridors
--- which supports the gravity intuition that destination popularity and
institutional networks matter strongly.

The cross-sectional PPML output is directionally consistent with a
destination-attractiveness story. Three findings stand out:

1. **Institution quality dominates.** The QS-based city score is positive and
   highly significant ($\beta_3$ = 0.012, p < 0.001), implying about **+28% per SD**.
   This should be read as academic + institutional attractiveness rather than
   pure teaching quality: top-ranked universities are also larger, more
   internationally visible, and embedded in denser Erasmus partnership
   networks.
2. **Quality of life adds independent signal.** The Erasmusu rating is positive
   and significant ($\beta_2$ = 0.159, p < 0.001) once institution quality is
   controlled for, equivalent to **+11% per SD**. The Reddit sentiment proxy is
   correlated with this measure (ρ ≈ 0.21), so the text layer enters as a
   robustness cross-check rather than the headline.
3. **Monetary gaps are weak headlines.** The GDP-per-capita gap is not
   significant in the headline cross-section ($\beta_1$ = $-3\times10^{-6}$, p ≈ 0.25). Salary
   and price-level gaps are correlated with GDP gap (VIF ≈ 5--7) and remain in
   the robustness column. Shared language-family affinity is positive and
   significant (β = 0.18, p ≈ 0.002).

The Reddit layer adds a qualitative view of destination perception. Spain,
Italy, France, Poland, Portugal, and Germany dominate the extracted mention
counts. Themes such as nightlife, academics, housing, bureaucracy, and cost
pull in different directions for the same destination, so the layer is best
read as evidence about *perceived* quality of life rather than as a precise
ranking.

The **temporal extension** sharpens the QoL story. With panel year fixed
effects, the OWID Cantril-ladder happiness score enters positively and
significantly within destinations over time (β = 0.23, p ≈ 0.035; ≈ +19% per
SD across 36 destinations, 2014--2023). This is the closest causal-adjacent
evidence in the project because it identifies the QoL channel from within-
destination changes, not just cross-country differences. By contrast, the
time-varying QS score is null (p ≈ 0.57), consistent with rank stickiness ---
once a city has a top university it tends to keep it.

The **COVID-2020 sector DiD** is informative for what it does *not* find. With
the Eurostat LCI wage-growth hit as treatment intensity, the estimate is small
and weakly negative (p ≈ 0.10); with the cleaner LFS employment-growth hit it
collapses to zero (p ≈ 0.95). The honest reading is that COVID's mobility
shock was **lockdown-wide, not field-selective**: Erasmus flows in 2020 fell
across the board, not preferentially in the sectors that took the bigger wage
or employment hit. The wage-based version partly picked up lockdown intensity
because LCI is contaminated by 2020 wage-subsidy schemes (Dutch NOW, German
Kurzarbeit), which the LFS replication confirms.

## 5. Interpretation, Limitations, and Conclusion

The project answers the research question on two fronts. First, the spatial
flow analysis shows where students move and how destination profiles differ by
sending country. Second, the text layer adds a student-perception variable not
available in official Erasmus data. Together they show how a gravity model of
Erasmus mobility can combine mobility flows, economic indicators, spatial
controls, institution quality, and student-generated text.

The clearest result is not a causal coefficient but a descriptive pattern:
destination attractiveness is multidimensional. High-flow destinations combine
strong institutions, favourable perceived living conditions, and familiar
language environments. Monetary gaps are difficult to separate because they
capture overlapping rich-destination dimensions. The quality-of-life signal
weakens under stricter fixed effects, suggesting much of it lives across
countries rather than within countries across cities --- plausible because
Erasmus mobility is constrained by bilateral university agreements, not only
by free student choice. The OWID time-varying panel is the strongest piece of
quasi-experimental evidence because it identifies QoL within destination over
time.

**Limitations.** Reddit users are not representative of all Erasmus students,
and per-country mention counts are small. The manual-validation xlsx provides
the required hand-labelled cross-check on a stratified sample of 51 mentions,
but the Reddit layer should still be read as a perception proxy. The
institution-quality measure relies on Nominatim geocoding plus nearest-city
snapping, which introduces assignment noise, and it cannot separate academic
quality from institutional scale: a city with a top-ranked university tends to
have larger campuses, more exchange seats, and more bilateral agreements.
Without a causal research design, all regression estimates are exploratory
associations.

**Contribution.** The project builds a reproducible descriptive pipeline for
Erasmus Higher Education mobility, combines spatial flow analysis with
economic indicators and an institution-quality layer, and adds a text-derived
perception layer from Reddit. It documents that institution quality, perceived
quality of life, and language affinity are positively associated with Erasmus
destination flows conditional on broad prosperity and distance, that the
quality-of-life association is robust within destinations over time, and that
the COVID-2020 mobility shock was lockdown-wide rather than field-selective.

## References

Anderson, J. E., and E. van Wincoop. 2003. "Gravity with Gravitas: A Solution
to the Border Puzzle." *American Economic Review* 93(1): 170--192.

Beine, M., R. Noël, and L. Ragot. 2014. "Determinants of the International
Mobility of Students." *Economics of Education Review* 41: 40--54.

Gentzkow, M., B. Kelly, and M. Taddy. 2019. "Text as Data." *Journal of
Economic Literature* 57(3): 535--574.

Grimmer, J., and B. M. Stewart. 2013. "Text as Data: The Promise and Pitfalls
of Automatic Content Analysis Methods for Political Texts." *Political
Analysis* 21(3): 267--297.

Rodríguez González, C., R. Bustillo Mesanza, and P. Mariel. 2011. "The
Determinants of International Student Mobility Flows: An Empirical Study on
the Erasmus Programme." *Higher Education* 62(4): 413--430.

Santos Silva, J. M. C., and S. Tenreyro. 2006. "The Log of Gravity." *Review
of Economics and Statistics* 88(4): 641--658.

Tinbergen, J. 1962. *Shaping the World Economy*. New York: Twentieth Century
Fund.
