# 01 — Research plan

One paper, three questions (reframed 2026-10-26, wording of Q2/Q3 agreed 2026-10-30; see `00_project_overview.md` and `decisions_log.md`).
Q1 is the reference for Q2 and Q3: every model result is scored against the satellite patch.

## Q1 — Observed: did we see the patch, and what was its extent? (current focus)

### Sub-questions
1. Where was 2026 chlorophyll significantly higher than in previous years, and over what area?
2. When did the patch exist (onset, peak, end), and how did it propagate along the coast?
3. How does 2026 compare with each previous year in size, duration and intensity?
4. How much of the "chlorophyll" signal is actually coloured dissolved organic matter (CDOM) from freshwater?

### Analysis window and baseline
- Analysis window: about 1 July – 31 October each year.
- Baseline: 2016–2025 (Sentinel-3 OLCI era, 300 m); 2020–2025 for the HR product. 2025 stays in the baseline (it was also high; stated in the paper).
- Figures may show only 2020–2026.

### Methods
Full step-by-step procedure: **`05_stage1_patch_identification.md`**. Summary:
- **A. Per-pixel anomaly and significance** (implemented): leave-one-year-out climatology per 10-day bin (monthly fallback), one-sided Mann–Whitney with effective sample sizes from the empirical autocorrelation, Benjamini–Hochberg FDR (q = 0.10) over the whole domain per map, effect size ≥ ×1.5, objects < 1 km² removed → "patch". Also a whole-season test and an 11-day sliding window (movie).
- **B. Object-based patch detection and tracking** (to be written): connected objects, coast-connected, tracked by overlap; area, alongshore extent, offshore distance, lifespan; every year 2016–2026.
- **C. Alongshore Hovmöller and integrated indices** (to be written): coast-following coordinate from Rosetta to Rosh HaNikra; arrival date at each desalination plant; "anomaly × km × days" per year; change-point onset/end.
- Each method runs on chlorophyll and on CDOM (a_dg443, main proxy) side by side.

### Milestones
1. ~~Data access, download, climatology and anomaly fields on the pilot.~~ Done.
2. ~~Method A on the pilot (autocorrelation, FDR, patch).~~ Done 2026-10-26.
3. Full domain on the external machine.
4. Methods B and C.
5. Q1 synthesis: maps, time series, year comparison.

## Q2 — Operational system: did it represent the patch, and could it have?

Procedure: **`07_q2_operational_model.md`**. Summary:
- The issued forecasts are not archived (OGS, 2026-10-29), so forecast skill cannot be measured directly.
- **Level A — upper-bound test:** the model's chlorophyll (reanalysis 2016–2025 as baseline; reanalysis-interim/analysis for 2026) through the same pipeline as Q1. The analysis assimilates satellite chlorophyll, so if even the analysis shows no significant 2026 anomaly, the forecast almost certainly missed it.
- **Level B′ — saw-tooth test:** decay of the analysis chlorophyll in the patch between the weekly assimilations, as a proxy for what a forecast would lose.
- **Level C — inputs and physics:** what the model knows about land inputs (only a climatological Nile in the SE Levantine; no Gaza, Israeli streams or wastewater), its known coastal bias, and whether its physics showed the freshening.

### Milestones
1. Download model chlorophyll, nutrients and salinity for an intermediate box and then the full domain (the 5 × 5 km pilot is about one model cell).
2. Level A and the comparison with the Q1 patch.
3. Level B′ (after confirming the assimilation day with OGS).
4. Level C diagnostics.

## Q3 — Forecastability: could the patch have been forecast? (not yet reviewed)

Plan: **`03_models.md`**. Summary:
- First step: Lagrangian back/forward tracking on existing model currents (CMEMS MedSea, SELIPS) — cheap test of transport anomalies.
- Own regional model run as **reforecasts**: start dates every few days from ~10 Aug to early Sep 2026, initialised from the CMEMS physics and biogeochemistry analysis, 10-day leads, scored against the Q1 patch and persistence.
- Three run types: (a) operational-like (forecast atmosphere, climatological Nile, no Gaza/wastewater) — stand-in for the missing operational forecast; (b) forecast atmosphere with real 2026 inputs; (c) perfect forcing (reanalysis atmosphere, real inputs) — upper limit and mechanism. Run order c → a → b.
- Attribution (H1 vs H2) comes from the sensitivity runs of (c).

### Milestones
1. Model choice and setup (review of `03_models.md`).
2. Forcing: archived atmospheric forecasts for Aug 2026; Nile/Gaza/stream inputs for 2026.
3. Runs (c), then (a), (b); scoring.
