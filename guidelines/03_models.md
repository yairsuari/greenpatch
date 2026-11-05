# 03 — Models (Q2 and Q3)

Q2 uses the operational system's existing output; Q3 needs our own model. Research questions: `00_project_overview.md`.

## Q2 — Operational system (verified 2026-10-26/30)
Full procedure and facts from the product documentation: **`07_q2_operational_model.md`**.

| Product | Use | Coverage |
|---|---|---|
| `MEDSEA_ANALYSISFORECAST_BGC_006_014` (MedBFM4.3: OGSTM-BFM + 3DVarBio, OGS) | 2026 model chl, nutrients (analysis; the issued forecasts are not archived) | 2024-07-23 → rolling |
| `MEDSEA_MULTIYEAR_BGC_006_008` (MedBFM3.2) | Model baseline 2016–2025; 2026 to 30 Sep (interim) | 1999 → 2026-09-30 |
| `MEDSEA_ANALYSISFORECAST_PHY_006_013` (NEMO + OceanVar) | Salinity, temperature, currents, mixed layer in 2026 | 2024-08-27 → rolling |
| `MEDSEA_MULTIYEAR_PHY_006_004` | Physics baseline | reanalysis + interim |

Key facts for the paper: weekly assimilation of satellite chlorophyll (coast included); in the SE Levantine the only land input is a climatological Nile; largest negative coastal chlorophyll bias of the Mediterranean in the southern/eastern Levantine.

## Q3 — Own model: what would the model need to reproduce the patch? (DRAFT, not yet reviewed)

### Other existing outputs (cross-checks, currents for Lagrangian tracking)
| Model | Resolution | Notes |
|---|---|---|
| SELIPS (IOLR, POM-based SE Levantine forecast) | ~1 km | Highest resolution off Israel; archive via IOLR |
| CYCOFOS (Cyprus) | ~2 km | Independent regional forecast |
| HYCOM / Mercator global | 1/12° | Boundary conditions and cross-check only |

### Lagrangian analysis (first step)
OceanParcels or OpenDrift on CMEMS/SELIPS currents. Back-track from the patch; forward-track from Nile mouths and Gaza outfalls; 2026 versus 2016–2025. Tests transport anomalies without building a model.

### Model
- **Proposed:** CROCO (or ROMS), ~0.5–1 km, Rosetta to Rosh HaNikra (31.0–33.15°N, 30.0–35.2°E) with a margin, nested in the CMEMS Med physics and biogeochemistry. Biogeochemistry: ⚙ (PISCES, Fennel NPZD, or BFM for consistency with the operational system). Passive dye tracers for Nile and Gaza water.
- **Alternatives:** SCHISM or FVCOM (unstructured, resolve outfalls and intakes); MITgcm or NEMO-AGRIF (heavier).

### Simplified design for this paper (user 2026-11-05; DRAFT by Claude, to review)
The paper's claim is "not forecastable with present operational tools"; the missing land input is the leading
hypothesis (`decisions_log.md` 2026-11-05). Q3 is therefore reduced to runs that test what the model needs to hold the
patch; the forecast-mode runs (a)/(b) below are deferred. Wording consequence: Q3 can answer "given the input, does
the model produce the patch, and how soon after the input starts", not a full lead-time skill.

**Model (user 2026-11-05): the operational chain, OGSTM-BFM offline (+ 3DVarBio for the nudging runs).** The
operational system is NEMO v4.2 + WW3 + OceanVar physics at 1/24° (141 levels; Richardson-number vertical mixing,
Pacanowski and Philander 1981; ECMWF hourly forcing; QUID 006_013), with the biogeochemistry run **offline** by
OGSTM-BFM on the saved physics (QUID 006_014). Code: OGSTM (https://github.com/inogs/ogstm, GPL-3), 3DVarBio
(inogs/3DVarBio), build tooling (inogs/ModelBuild); BFM from the BFM community (user's PhD model). Running "the same
system plus a source" is the cleanest Q3. ROMS + Fennel (earlier proposal) dropped.

**Physics forcing.** OGSTM reads daily U, V, W, **vertical eddy diffusivity (`votkeavt`)**, T, S, sea level, wind
stress or speed and surface shortwave flux (`src/IO/forcing_phys.f90`). The public 006_013 has U, V, W, T, S and sea
level, but not the diffusivity or the surface fluxes. Two routes:
1. **Preferred: ask OGS** for their offline forcings and a full BFM restart (all state variables; the public 006_014
   lacks internal quotas, bacteria, DOM/POM, zooplankton groups) for the domain, 1 Aug – 31 Oct 2026: exactly the
   operational physics, no drift, no NEMO set-up.
2. **Own regional NEMO v4.2**, nested in 006_013 (daily boundaries; weak nudging to the analysis ⚙ against drift,
   since our run has no OceanVar), same vertical mixing scheme, ERA5 (or ECMWF if accessible [VERIFY]) atmosphere, no
   WW3; it writes the OGSTM forcings including the diffusivity. Also the fallback if OGS cannot share, and the route to
   a finer coastal grid later (follow-up study).

**Why offline.** OGSTM steps at `rdt = 1800` s (variable, CFL-limited; namelist.init) against minutes for NEMO at
1/24°, and one physics run is reused by all biogeochemical runs. Caveats: daily-mean forcing smooths sub-daily
mixing (as in the operational system), and **a source added in OGSTM carries nutrients and dye but no buoyancy** (the
physics never sees the fresh water). If plume stratification matters, S1/N3 need physics from our NEMO with the fresh
water added (one NEMO run per source strength).

**Domain and grid ⚙.** Operational grid (1/24°, ~4.2 km); a box around the Gaza–Israel coast with the Nile through the
boundary, or the full domain (31.0–33.15°N, 30.0–35.2°E). A source is diluted into 4.2 km cells, as in the operational
system; a finer nest belongs to the follow-up study.

**Common set-up.** One continuous hindcast 1 Aug – 31 Oct 2026 (onset ~27 Aug). Initial state from the OGS restart (or
the 006_014 analysis with derived quotas); Nile as in the operational system (monthly climatology) unless stated.
Passive dye tracer on every added source. **Validation first:** S0 and N1 must reproduce the operational analysis,
including the weekly jump and decay (`07` section 8), before S1–N3 count.

| Run | Land input | Assimilation (weekly, like the operational system) | Question |
|---|---|---|---|
| **S0 control** | none beyond the operational Nile | none | Does the model alone produce the patch? (expected: no, as the operational analysis) |
| **S1 source** | added coastal source(s): fresh water Q and nitrate/phosphate C at candidate points (Gaza first), 2–3 strengths ⚙ [VERIFY plausible Q and C] | none | Is a land input of plausible size enough to produce a patch like the observed one (extent, onset, magnitude)? |
| **N1 chl only** | as S0 | weekly 3DVarBio with satellite chl, as operational (corrects phytoplankton only) | Reproduces the operational saw-tooth? (target: decay ×0.56–0.67 over 5 days) |
| **N2 chl + nutrients** (user's idea) | as S0 | as N1, plus a nitrate increment where observed chl > climatology × threshold ⚙ (×1.5, the effect size); increment from the phytoplankton increment by N:chl ⚙ | Does a one-off nutrient correction hold the patch, or does it still decay? |
| **N3 chl + source** | as S1 (best strength) | as N1 | Does the system hold the patch once the source exists? |

Scoring for all runs: against the Q1 satellite patch on the model grid (hit rate, false-alarm ratio, critical success
index), onset date, alongshore extent, and the decay after each weekly correction (N runs). Seven runs if S1 has three
strengths. Run order: S0 → N1 (checks the set-up against the operational behaviour) → S1 → N2 → N3.

### Reforecast design (agreed in outline 2026-10-30; run types a/b deferred 2026-11-05)
- **Start dates:** every few days (⚙ 3–4 days) from ~10 Aug to early Sep 2026, covering the onset (Q1: between late August and early September).
- **Initial conditions:** CMEMS physics (006_013) and biogeochemistry (006_014) analysis on the start date — the same starting point the operational forecast had.
- **Length:** 10 days (as the operational forecast).
- **Scoring:** against the Q1 satellite patch (aggregated to the model grid) and against persistence: hit rate, false-alarm ratio, critical success index, onset date; by lead time.

| Run | Atmosphere | Rivers / land inputs | Answers |
|---|---|---|---|
| **(a) Operational-like** | Forecasts available at the time [VERIFY: archive, e.g. ECMWF/GFS] | As the operational system: monthly climatological Nile only; no Gaza, Israeli streams, wastewater | Stand-in for the missing operational forecast |
| **(b) Better inputs** | As (a) | Real 2026 discharges, as far as knowable at the time | Would better inputs have made it forecastable? |
| **(c) Perfect forcing** | Reanalysis (ERA5) | Real 2026 discharges | Upper limit of predictability; mechanism |

Run order: c → a → b.

### Attribution (sensitivity runs on (c); largely replaced by S0/S1 above and the next study, `08_next_study_draft.md`)
| Run | Rivers/sources | Atmosphere | Purpose |
|---|---|---|---|
| CTRL-2026 | 2026 | 2026 | Reference (= run c) |
| CLIMRIV-2026 | climatological | 2026 | Remove discharge anomaly (tests H1) |
| NOGAZA-2026 | 2026 without Gaza | 2026 | Gaza contribution |
| CLIMATM-2026 | 2026 | climatological | Remove atmospheric anomaly (tests H2) |
| CTRL-YYYY | each year | each year | Inter-annual comparison |
