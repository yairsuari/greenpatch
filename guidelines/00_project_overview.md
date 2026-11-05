# 00 — Project overview

## Background
Between August and September 2026 an anomalous environmental event occurred along the Israeli Mediterranean coast:
- chlorophyll concentrations were unusually high;
- sea-surface salinity dropped significantly.

Potential impacts include changes in marine populations and, above all, operational impacts on seawater desalination plants (Sorek, Hadera, Ashkelon, Palmachim, Ashdod) and through them on the Israeli water sector.

The source is not fully clear. Contrary to some press coverage, Nile-origin microalgae intrude along the Israeli coast every summer. **The core question is why the phenomenon was amplified in 2026.**

Press:
- ynet: https://www.ynet.co.il/environment-science/article/h18uzn00dzg
- Calcalist: https://www.calcalist.co.il/local_news/article/byrmxi0fgg

## Research questions (one paper; reframed 2026-10-26/30)
1. **Q1 — Observed.** Did satellites see the patch, and what was its extent in space and time? Define the area and time window in which 2026 chlorophyll was statistically significantly higher than in previous years (onset, peak, end, propagation), and compare 2026 with previous years. Detail is limited by the satellites' spatial resolution. Procedure: `05_stage1_patch_identification.md` (done for the 5 × 5 km pilot).
2. **Q2 — Operational system.** Did the operational Mediterranean biogeochemical system (Copernicus Marine Med-BGC, MedBFM run by OGS) represent the patch at all, even in its best estimate (the analysis, with satellite chlorophyll assimilated), and does it contain the processes and inputs needed to forecast it? The original question, "did it forecast the patch?", cannot be answered directly: OGS confirmed (2026-10-29) that the forecasts as issued are not stored. Procedure: `07_q2_operational_model.md`.
3. **Q3 — Forecastability.** Could the patch have been forecast, how many days ahead, and what would that have required? Own regional model run as reforecasts (operational-like, better inputs, perfect forcing). The attribution question is part of Q3:
   - **H1 — enhanced discharge:** increased flow of fresh, nutrient-rich water from the Gaza Strip and/or the Nile.
   - **H2 — oceanographic conditions:** circulation, winds, eddies or stratification unique to 2026.
   Plan: `03_models.md` (not yet reviewed).

In-situ validation data: little is expected (user 2026-10-26).

## Key outputs
- Q1: map(s) of the significant 2026 anomaly and its area; onset, peak, end and propagation; 2026 versus previous years (size, duration, intensity).
- Q2: model chlorophyll anomaly tested with the same statistics as Q1 (an upper-bound test, because satellite chlorophyll is assimilated); decay of the patch between weekly assimilations (saw-tooth test); inventory of the model's land inputs and known coastal bias; statement that issued forecasts are not archived (limitation and recommendation).
- Q3: forecast skill against the Q1 patch and persistence by lead time; what limits predictability (weather forecast, land inputs, model); evidence for or against H1 and H2.
