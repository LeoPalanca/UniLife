# Economic Attractiveness and Erasmus Mobility

**A descriptive analysis of European student flows**  
Course: Text Analysis and Spatial Data for Economists SP 2026  
Student: Leonardo Palanca  
Status: report mockup based on the project as-is

## Page 1 - Research Question and Motivation

Erasmus mobility is both a spatial flow problem and a text-as-data problem. Students move from an
origin country to a destination country or city, and the attractiveness of a destination depends on
economic conditions, institutional quality, distance, language, and student perceptions of daily
life. This project asks:

> What explains the size of Erasmus Higher Education mobility flows from one country to another?

The starting point is a gravity-style view of student mobility. In the same way that trade,
migration, and commuting flows are usually larger between closer or more attractive places,
Erasmus flows can be described as a function of origin conditions, destination pull factors, and
bilateral frictions. The project focuses on three destination-pull variables: salary gap, perceived
quality of life, and institution quality. The executed analysis is descriptive and exploratory; it
does not claim causal effects.

The literature motivates this structure. Tinbergen's gravity model and the structural gravity
framework of Anderson and van Wincoop explain why bilateral flows should depend on both partner
characteristics and frictions. Student-mobility studies such as Rodriguez Gonzalez, Bustillo
Mesanza and Mariel (2011), and Beine, Noel and Ragot (2014), apply this logic to international
student flows, emphasizing distance, cost, networks, and university quality. The text layer follows
the "text as data" literature: student discussions are treated as a noisy measurement of perceived
quality of life, not as a representative survey.

The teacher's project specification requires a research question where text analysis and spatial
data are relevant, collection and execution of the text/spatial analysis, code and raw data, and a
short report describing how the results would answer the research question. This project addresses
that by combining official Erasmus mobility data, spatial aggregation and distance measures, and a
Reddit/OpenRouter/Pydantic extraction pipeline for student destination perceptions.

## Page 2 - Data

The core data source is the official Erasmus+ KA1 2022 mobility file:

```text
data/raw/Erasmus-KA1-Mobility-Data-2022.xlsx
```

The analysis filters the file to Higher Education learner study mobilities, keeps cross-border
flows, and aggregates the result to origin-destination pairs:

```text
sending_country, sending_code, receiving_country, receiving_code, flow_count
```

In the current database, the country-pair table contains 2,651 rows and 274,533 student flows. The
largest corridors include Italy to Spain, Spain to Italy, Germany to Spain, France to Spain, and
Germany to France. These flows provide the backbone of the spatial analysis.

The project also builds a richer set of supporting datasets:

- economic indicators: GDP per capita, net earnings, and price-level/cost indicators;
- distance and language-affinity controls;
- Higher Education grant-per-participant measures from the Erasmus statistical annex;
- city and university flow aggregations for map and dashboard views;
- institution quality from QS World University Rankings 2023, geocoded and snapped to Erasmus
  destination cities;
- StudyPortals student ratings as a user-based institution-quality cross-check;
- OWID life satisfaction and education-spending series for exploratory panel extensions.

The text layer uses Reddit `r/Erasmus` posts and comments. A structured extraction pipeline calls
OpenRouter/DeepSeek and parses responses with Pydantic. Each extracted destination mention contains
city, country, sentiment, sentiment score, themes, confidence, Reddit score, and permalink. The
current extracted dataset contains 900 destination mentions across 46 countries and 209 cities:
333 positive, 326 neutral, and 241 negative mentions. This is interpreted as a qualitative
perception signal, not a representative measure of all Erasmus students.

## Page 3 - Methods

The first part of the analysis is a spatial data pipeline. The Erasmus file is filtered to the
target population, reshaped and aggregated, then joined to country-level indicators. For each
origin-destination pair, the project computes economic gaps:

```text
gdp_gap = receiver_gdp_per_capita - sender_gdp_per_capita
earnings_gap = receiver_net_earnings - sender_net_earnings
price_level_gap = receiver_price_level - sender_price_level
```

The same flow data are also summarized as destination shares and flow-weighted destination
economics. For example, a sending country's flow-weighted destination GDP is:

```text
sum(flow_to_destination * destination_gdp) / total_outgoing_flow
```

This gives a descriptive answer to whether students from each country tend to move toward richer,
poorer, more expensive, or cheaper destinations.

The second part is the text analysis. The Reddit extraction pipeline asks the model to identify
destination mentions and classify each one by sentiment and themes such as cost, housing,
nightlife, academics, safety, and bureaucracy. The structured output design mirrors the course's
LLM information-extraction assignment: the output schema is explicit, the model response is parsed
into structured records, and sentiment is normalized before aggregation. In the dashboard and
database, Reddit evidence is aggregated by destination country and city. Positive and negative
themes are separated so that "top themes" can distinguish favorable discussion from complaints.

The third part is the step-3 gravity design. The report's core specification is:

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

Following the project instructions, this regression can be described as the design for answering
the research question. The current repository also estimates exploratory PPML/log-OLS versions.
Those estimates are useful as evidence, but they should be reported as associations, not causal
effects.

## Page 4 - Descriptive Results

The Erasmus flow structure is highly concentrated. The largest flows are between major Erasmus
sending and receiving countries, especially Spain, Italy, France, and Germany. Spain is central in
the network: Italy to Spain and Germany to Spain are among the largest corridors. This supports the
gravity intuition that destination popularity and institutional networks matter strongly.

Economic gradients are visible but not simple. Salary, GDP, and price-level gaps all proxy a
similar rich-destination dimension, which creates collinearity in the exploratory regression
outputs. For this reason, monetary variables are useful controls, but their individual coefficients
should not be overinterpreted. The project is strongest when it uses these variables to describe
destination profiles and flow-weighted averages rather than claiming a clean independent salary
effect.

The Reddit layer provides a qualitative view of destination perception. Spain, Italy, France,
Poland, Portugal, and Germany have the highest counts in the extracted Reddit mentions. The
dashboard separates positive and negative themes by destination, which is important because the
same destination can appear often for both attractive and problematic reasons. For example, themes
such as nightlife, academics, housing, bureaucracy, and cost can pull in different directions.
Because per-country Reddit counts are small, this layer is best read as evidence for perceived
quality of life rather than as a precise destination ranking.

The exploratory model outputs are directionally consistent with a destination-attractiveness
story. Institution quality has the strongest positive association in the current PPML output:
the QS-based city score is positive and significant, with an estimated effect of about +29 percent
per standard deviation. This variable should be read as academic or institutional attractiveness,
not pure teaching quality: highly ranked universities may also be larger, more internationally
visible, and embedded in denser Erasmus partnership networks. The quality-of-life proxy from
Erasmusu is also positive and significant, with an estimated effect of about +12 percent per
standard deviation after adding institution quality. Shared language-family affinity is positive
as well. These estimates are exploratory because destination popularity, institutional agreements,
university capacity, and unobserved city attractiveness can still confound the relationship.

The main descriptive interpretation is therefore cautious: Erasmus flows are larger toward
destinations that combine strong institutions, favorable perceived quality of life, and familiar
language environments, while purely monetary gaps are harder to separate from broader destination
wealth and popularity.

## Page 5 - Interpretation, Limitations, and Conclusion

The project answers the research question in two ways. First, the spatial flow analysis shows where
students move and how destination profiles differ by sending country. Second, the text layer adds a
student-perception variable that is not available in official Erasmus data. Together, these pieces
show how a gravity model of Erasmus mobility could combine official mobility flows, economic
indicators, spatial controls, institution quality, and student-generated text.

The clearest result is not a causal coefficient but a descriptive pattern: destination
attractiveness is multidimensional. High-flow destinations are not only geographically or
economically attractive; they also tend to have strong institutions and favorable perceived living
conditions. The quality-of-life result weakens when stricter fixed effects are used, which suggests
that much of the relationship lives across countries rather than within countries across cities.
This is plausible because Erasmus mobility is constrained by bilateral university agreements, not
only by free student choice.

Several limitations matter. Reddit users are not representative of all Erasmus students, and
destination discussions are sparse for many countries. The current repository contains structured
LLM extraction, but a final submission should add a small manual validation table of 40-50 mentions
or clearly state that such validation is missing. The institution-quality measure relies on
geocoding and nearest-city snapping, which can introduce assignment noise. It also cannot separate
academic quality from institutional scale: a city with a highly ranked university may also have
larger campuses, more exchange seats, and more bilateral Erasmus agreements. The exploratory
regressions therefore face omitted-variable concerns; without a causal research design, the
results should be read as associations.

The final submission should therefore state the contribution narrowly. The project builds a
reproducible descriptive pipeline for Erasmus Higher Education mobility, combines spatial flow
analysis with economic indicators, and adds a text-derived perception layer from Reddit. It shows
that institution quality, perceived quality of life, and language affinity are positively
associated with Erasmus destination flows, while monetary gaps are difficult to interpret
separately because they capture overlapping dimensions of destination wealth and cost.

## References

Anderson, J. E., and E. van Wincoop. 2003. "Gravity with Gravitas: A Solution to the Border
Puzzle." *American Economic Review* 93(1): 170-192.

Beine, M., R. Noel, and L. Ragot. 2014. "Determinants of the International Mobility of Students."
*Economics of Education Review* 41: 40-54.

Gentzkow, M., B. Kelly, and M. Taddy. 2019. "Text as Data." *Journal of Economic Literature*
57(3): 535-574.

Grimmer, J., and B. M. Stewart. 2013. "Text as Data: The Promise and Pitfalls of Automatic Content
Analysis Methods for Political Texts." *Political Analysis* 21(3): 267-297.

Rodriguez Gonzalez, C., R. Bustillo Mesanza, and P. Mariel. 2011. "The Determinants of
International Student Mobility Flows: An Empirical Study on the Erasmus Programme." *Higher
Education* 62(4): 413-430.

Santos Silva, J. M. C., and S. Tenreyro. 2006. "The Log of Gravity." *Review of Economics and
Statistics* 88(4): 641-658.

Tinbergen, J. 1962. *Shaping the World Economy*. New York: Twentieth Century Fund.

## Final Submission Notes

Before converting this mockup to PDF:

- trim to the required 5-page limit in the final layout;
- add one compact table or figure from the dashboard;
- either add a small Reddit manual validation table or keep the limitation explicit;
- make sure the notebook imports `erasmusgravity`, not the old `unilife` package name;
- package the final archive as `Palanca_Leonardo.zip` without `.env`, `.venv`, `.DS_Store`, or
  notebook checkpoints.
