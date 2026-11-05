# 08 — Next study (draft): where did the water come from, and what did it carry?

Status: **first draft, 2026-11-05, not reviewed by the user.** Not part of the current paper.
Everything here is open for discussion; ⚙ marks choices still to be made, `[VERIFY]` marks facts to check.

## 1. Why a second study
The current paper (Q1–Q3, `00_project_overview.md`) shows that the patch was there (Q1), that the operational
Mediterranean system did not represent it even in its analysis and could not have forecast it with its present inputs
(Q2), and, with simplified runs, what the model needs to reproduce it (Q3). Its leading hypothesis is a **land input
not represented in the model: fresh water carrying nutrients**, which the model lacks (its only land input in the
south-eastern Levantine is a climatological Nile; no Gaza, Israeli streams or wastewater; QUID 006_014).

Evidence that points this way (from the current paper; to be firmed up there):
- the analysis gets only ~×2 where the satellite shows ×6–9 (`07` section 8);
- the saw-tooth test: each weekly assimilation adds phytoplankton (not dissolved nutrients), and the model loses most of
  it within ~5 days (×0.56–0.67 in 2026), so something outside the model sustained the patch;
- the model shows no freshening, while a salinity drop was reported during the event [VERIFY: source, `handoff.md` open
  question 6].

The current paper stops at "a land input is the leading hypothesis". The next study tests it and quantifies it.

## 2. Questions (draft)
- **N1 — Where?** Where along the coast did the input enter (one point, several, or a diffuse source), and when did it
  start?
- **N2 — How much and what?** How much fresh water entered, and with what nutrient load and concentration?
- **N3 — Which source?** Which of the candidate sources (section 3) is consistent with N1 and N2?
- **N4 — Could a forecasting system catch it?** Would assimilation that reacts to coastal blooms (nutrients or an
  estimated source, and a satellite salinity proxy) have kept the patch in the model? This continues the nudging
  experiment of the current paper's Q3.

## 3. Candidate sources (to be completed; all `[VERIFY]`)
| Source | Fresh water? | Nutrients? | Steady or episodic? | Notes |
|---|---|---|---|---|
| Nile (Damietta, Rosetta), carried east and north by the coastal current | yes | yes | regulated, seasonal | In the model only as climatology; actual 2026 releases unknown |
| Gaza: Wadi Gaza and coastal wastewater outfalls | yes | high | could change abruptly (treatment-plant failure, power cuts, war damage) | Near the pilot box; volumes and 2026 status unknown |
| Israeli streams (e.g. Lachish, Soreq, Yarkon, Alexander, Hadera, Kishon) | yes (summer flow mostly effluent) | yes | mostly steady in summer | Monitoring data probably available |
| Wastewater/effluent outfalls on the Israeli coast | yes | yes | steady, with incidents | Outfall locations in `background_data/infrastructure/` [VERIFY] |
| Submarine groundwater discharge | yes | yes (nitrate) | mostly steady | Hard to explain a one-off event |
| Desalination brine outfalls | **no** (saltier) | possibly (antiscalants, coagulants) [VERIFY] | steady | Inconsistent with freshening; still to be ruled out |
| Atmospheric deposition (dust) | no | yes | episodic | Inconsistent with freshening; check dust events Aug 2026 |

A source must explain the onset location and time, the alongshore extent, the freshening (if confirmed) and a
nutrient supply large enough to sustain the observed chlorophyll.

## 4. Approach (draft)
### 4.1 Where (N1)
1. **Onset map from satellite** (from the current paper's Q1 land-input indicators): first day each pixel becomes
   significant, from the 11-day daily windows; CDOM (a_dg443), turbidity and SST anomalies at onset.
2. **Back-tracking:** Lagrangian particles released in the early patch and tracked backward with the operational
   currents (MEDSEA_ANALYSISFORECAST_PHY_006_013, 4.2 km) and, nearer the coast, with our own model's currents.
   Tool ⚙ (e.g. OceanParcels).
3. **Source inversion (Green's functions):** release a passive tracer from each candidate source (section 3) in the
   model, forward in time; find the non-negative combination of sources and release times that best matches the
   observed patch (non-negative least squares on the satellite anomaly or patch mask). This gives source weights with
   an uncertainty, and is cheap once the tracer runs exist. Resolution of the model near the coast is the limit ⚙.

### 4.2 How much (N2)
1. **Fresh water volume** from the salinity deficit, if salinity data exist (in situ or a proxy, 4.3):
   V_fw = ∫ (S₀ − S) / S₀ dV, with S₀ the ambient salinity.
2. **Nutrient supply needed** to hold the observed chlorophyll against losses:
   supply ≈ k · Chl · (C:Chl) · (N:C) · h · A,
   with k the loss rate, h the mixed-layer depth, A the patch area. Illustration only (not a result): Chl = 15 mg m⁻³,
   C:Chl = 50, Redfield N:C = 16/106 gives ≈ 9 mmol N m⁻³ in phytoplankton; with k ≈ 0.1 d⁻¹ (the model's decay in the
   saw-tooth test, ×0.6 in 5 days) about 1 mmol N m⁻³ d⁻¹ must be supplied. C:Chl, k and h are uncertain by factors of
   2–3 ⚙.
3. **Source concentration** = nutrient supply / fresh water flux. Compare with typical concentrations of the candidate
   sources (raw sewage, treated effluent, river water) [VERIFY: literature values]. This is the most direct test of
   N3.

### 4.3 Salinity from ocean colour
- Satellite salinity (SMOS, SMAP; ~40–50 km, land-contaminated near the coast) cannot resolve the coastal strip
  (decision 2026-11-05).
- In plumes of fresh water, CDOM often falls linearly with salinity (conservative mixing). Calibrate a_dg443 (300 m)
  against in-situ salinity where both exist; test whether the relation holds for each candidate source (river water,
  effluent and Nile water may have different end-members).
- Needs in-situ salinity during plumes: IOLR monitoring, desalination intake records, cruises [VERIFY: availability].

### 4.4 Assimilation that reacts to coastal blooms (N4)
Builds on the Q3 nudging experiment of the current paper (chl only / chl + nutrients above a threshold / chl + coastal
source).
1. **Threshold-triggered multivariate update:** when observed chl exceeds the climatology by a threshold ⚙, the
   increment also corrects dissolved nutrients, not only phytoplankton (the operational 3DVarBio corrects only the
   phytoplankton groups; QUID 006_008 §II.3).
2. **Source estimation:** add the unknown coastal fluxes (fresh water and nutrients at candidate points) to the
   estimated variables (augmented state, ensemble method ⚙), so the system corrects the cause, not only the state.
3. **Proxy salinity assimilation:** assimilate the CDOM-derived salinity (4.3) when the chl threshold is crossed.
4. Twin experiments first (known synthetic source, does the method recover it?), then the 2026 event, scored against
   the Q1 patch and against persistence.

## 5. Data needed
- From the current paper: full-domain Q1 patch, onset map, CDOM/turbidity/SST co-location, Q3 model setup and runs.
- Copernicus Marine: operational and reanalysis physics and biogeochemistry (already in the pipeline).
- In situ (to be found): coastal salinity and nutrients Aug–Oct 2026 (IOLR national monitoring; desalination plant
  intakes; Water Authority) [VERIFY].
- Discharges: Israeli streams and outfalls (gauges, permits), Gaza wastewater (UN/WHO/World Bank reports; 2026 status),
  Nile releases (likely not available) [VERIFY].
- Dust events Aug 2026 (CAMS or MERRA-2 aerosol) ⚙.

## 6. Dependencies and risks
- Depends on the current paper's full-domain Q1 and on a Q3 model that resolves the coast well enough.
- **Main risk:** little in-situ data, so salinity and nutrient concentrations may stay unconstrained; the study then
  rests on the inversion and the budget, with wide uncertainty.
- Gaza data may be incomplete or politically sensitive; the paper should state sources neutrally.
- Model resolution: 4.2 km operational currents cannot resolve outfall plumes; our own model's resolution ⚙.

## 7. Open questions for the user
1. Is the scope right (N1–N4), or should N4 (assimilation) be a third paper?
2. Which candidate sources do you already have data or contacts for?
3. Is there an observed salinity record for the event (who measured it, where)?
4. Model for the tracer and source runs: the same as Q3 of the current paper, or a higher-resolution coastal nest ⚙?
