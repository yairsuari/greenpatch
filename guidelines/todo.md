# To do

Reorganised 2026-11-05 by phase, around the stronger machine expected in a few days. Completed items are at the end.

## Phase 1 — before the machine (settings that are baked into the full-domain run)
- [x] Check the very high 2026 values (2026-11-05, pilot, `scripts/tools/check_chl_ceiling.py`): no saturation (raw max 99.2, none at 100; baseline years also reach 91–99); a_ph443 rises with chl and the CDOM share falls (a_dg/a_ph 0.28 vs 1.25 baseline), so CDOM inflation is unlikely. **But the 300 m and HR products disagree in 2026:** same-day box medians agree in 2020–25 (r = 0.85, 300 m − HR = −0.08 log10) and not in Sep–Oct 2026 (r = 0.15, +0.55 log10, i.e. 300 m ≈ ×3.5 higher; HR 3–6 mg m⁻³ vs 300 m 9–60). Both rise from ~24–27 Aug. The patch is robust; its magnitude is product-dependent.
- [x] Magnitude (user 2026-11-05): range across products, 300 m formal; Discussion paragraph "Magnitude of the patch" added to the manuscript (tracked; backup `ms_draft_2026-11-05_1126.docx`), with 6 new references (Berthon and Zibordi 2004, Colella et al. 2025 QUID, Gilerson et al. 2010, Gons et al. 2005, Lavigne et al. 2021, Van der Zande et al. 2024 QUID). AD4 diagnostic in `scripts/tools/check_chl_ceiling.py` section 5. To do: Q2 comparison against both products; find the AD4 calibration range [VERIFY]. In-situ chl is now the most valuable data for Q1.
- [ ] Chl algorithms (web, 2026-11-05, catalogue records, not yet the QUIDs): 300 m OLCI = MedOC4 (Case 1) blended with AD4 (Case 2; Berthon and Zibordi 2004) by a Mahalanobis-distance weight against MedBiOp spectra; HR (Sentinel-2 MSI, 100 m, 20 km coastal strip) = "multi-algorithm approach" (O'Reilly et al.), details in QUID CMEMS-BGP_HR-QUID-009-201to212. Read both QUIDs for coastal validation and upper limits [VERIFY].
- [x] Onset map (2026-11-05): `significance.onset` (first window centre starting ≥ 3 consecutive patch days ⚙ `ONSET_PERSIST`; `onset`, `onset_win_start` in `<var>_significance.nc`), figure `onset_<product>_<var>.png`. Pilot: 27 Aug – 5 Sep, offshore pixels first.
- [x] Co-location table (2026-11-05): `results/<domain>/tables/colocation_chl_patch.csv` (a_dg443, a_ph443, Rrs412/443, HR turbidity inside vs outside the chl patch). Pilot Sep: a_ph443 ×3.5–5 and significant in 95–99 % of the patch; a_dg443 and turbidity mildly up but not significant; Rrs412/443 not CDOM-like. The pilot signature is phytoplankton, not a CDOM-rich plume.
- [ ] Implement the user's settings of 2026-11-05 (decisions_log): SST L3S `010_012_b` in `config`/downloader/PREPROC (no log; two-sided test → add a two-sided option to the anomaly step and `significance`); HR `buffer_px` 3; a_dg443 `vmax` 2; season-test MAX_LAG 60; then rerun the pilot 05/06/07 and compare with the previous pilot results.
- [ ] **User:** review `reports/settings_review_2026-11-05.md` (baked-in settings: HR coastal buffer, a_dg443 upper limit, MAX_LAG 60, HR ACF fit, October 2026 data end) and the pilot figures.
- [ ] Agree the remaining ⚙ parameters in `05_stage1_patch_identification.md`.
- [ ] HR autocorrelation function is noisy (≈ 5 pairs per pixel at most lags; e.g. 0 at lags 8–9, 0.63 at 18): smooth it or fit a parametric form.
- [ ] ACF stops at 30 days (r ≈ 0.09 there for 300 m chl); the whole-season test is slightly anti-conservative. Consider MAX_LAG = 60 for the season test.
- [x] Pilot 300 m reflectance bands re-downloaded (2026-11-05, 11 files in `data/raw/satellite/rrs/olci300/pilot/`, kept); the existing CDOM rasters were not recomputed and are unchanged. The 2026 band file now reaches the archive end (27 Oct), the CDOM raster still ends 13 Oct.
- [ ] Manuscript 2.3 still says the bands were deleted after the CDOM proxies were computed: fix (tracked) in the writing phase.
- [ ] Dormant ACOLITE / Level-1 code (`slim.py` ACOLITE_RE, `02_slim_storage.py` L1 handling, `config.L1_EXTENT`): remove, or keep? CLAUDE.md's deletion exception still names Sentinel-2/Landsat (user's file; not edited).
- [ ] Make the project portable (user 2026-11-05: work moves to a second laptop → VS Code Remote-SSH → machine): guide `09_remote_setup.md`. Initial commit + private GitHub repository — **user to confirm**.
- [ ] Machine details: settle after the first login (user 2026-11-05: "leave as is").
- [ ] Verify the QAA v6 constants in `src/greenpatch/cdom.py` against the QAA v6 document.
- [ ] Verify the coastal Gaza–Israel border coordinate (~31.594°N) used to place the pilot box.

## Phase 2 — on the machine: full-domain Q1
- [ ] Prepare the machine: copy the repository, create the venv, Copernicus login (`06_local_pilot.md`, "Running on the external machine").
- [ ] Download the full domain (dry run 2026-10-26: ~139 GB — chl300 18, rrs300 31, HR 90 — plus SST), inventory and image-usage audit.
- [ ] 05/06 per tile (`--workers` or batch jobs), product-wide FDR (`06 --significance-only`), figures, paper figure, movie, onset map, indicator co-location.
- [ ] Sensitivity run for the patch rules: effect size ×1.25 / ×2, minimum area 0.5 / 2 km² (supplement).
- [ ] Q2 re-scoring against the full-domain patch: hit rate, false-alarm ratio, CSI, onset/peak dates, alongshore extent (can run locally; model data are small).
- [ ] Q2 ⚙: minimum object area on the 4.2 km grid; patch fraction threshold for the satellite-model comparison.
- [ ] Methods B and C (needs the user's confirmation of Part 2 of `05`).

## Phase 3 — Q3 simplified model runs (design now, run on the machine)
- [x] Q3 simplified design drafted in `03_models.md` (2026-11-05): S0 control, S1 source (2–3 strengths), N1 chl-only nudging, N2 chl + nutrients above threshold, N3 chl + source; 1 Aug – 31 Oct 2026 hindcast.
- [x] Q3 model (user 2026-11-05): operational chain OGSTM-BFM offline + 3DVarBio (`03_models.md`).
- [ ] **User → OGS:** request the offline physics forcings (incl. vertical diffusivity `votkeavt`, wind, shortwave) and a full BFM restart for the domain, 1 Aug – 31 Oct 2026 (add to the OGS email with the Q2 questions).
- [ ] Q3: build OGSTM-BFM (ModelBuild) and 3DVarBio on the machine; prepare the regional NEMO v4.2 nest in 006_013 as fallback / buoyant-source route. Domain box ⚙, plausible source Q and C [VERIFY].
- [ ] Q3: model setup on the machine (grid, nesting in the operational fields, forcing, land-input scenarios).

## User tasks (can start now)
- [ ] **Ask OGS:** (i) was the setup described in the May 2025 QUIDs in operation in Aug–Oct 2026; (ii) are the weekly pre-assimilation misfits for 2026 archived (https://medeaf.inogs.it/nrt-validation); (iii) confirm that the Monday jump is the assimilation (QUID 006_014: the Tuesday run publishes analysis days −8 to −2, so the window starts on Monday); (iv) the analysis–reanalysis offset at the coast (salinity +0.2 psu); (v) how to cite their reply on the missing forecast archive.
- [ ] **Contact IOLR (monitoring data, SELIPS archive) and the Water Authority (desal intake records)** for in-situ chl, salinity and nutrients Aug–Oct 2026 — moved up from "Later" (2026-11-05): main weakness of Q1 and core of the next study.
- [ ] Sources for the event facts (salinity drop, alongshore extent, the name "green patch").
- [ ] Decide how to present Q2 Level A (formal test has no power on model fields; descriptive record cells / ranks proposed).
- [ ] Cloud-credit proposals: decide their purpose (perhaps Q3 only, if the machine comes through).
- [ ] (Optional) start archiving the daily operational forecast for our domain for future events?
- [ ] Review the next-study draft `08_next_study_draft.md` (scope and open questions).
- [ ] Discuss: September 2025 was also high in the pilot box (box-median chl 5–8 mg m⁻³ vs ~1–5 in 2016–2024; 2026: 12–25); 2021 and 2023 also had high September bins. Possible trend; 2025 in the baseline makes it more conservative.

## Writing (after results)
- [ ] Manuscript Introduction questions and title for the 2026-11-05 scope (tracked); guidelines `00`, `01`, `03` likewise.
- [ ] Manuscript Discussion: paragraph on the unarchived operational forecasts (limitation and recommendation).
- [ ] Results text: onset not significant at 10-day resolution (21–31 Aug elevated, 0 pixels after FDR) → "between late August and early September"; check with the daily movie windows.
- [ ] Results text: state that September 2025 was also high (2025 stays in the baseline).
- [ ] Resolve the [VERIFY] marks in `reports/ms_draft.docx` (press facts, salinity source, cross-shore extent, section numbers, reference details incl. Volpe et al., QAA v6 citation, CMEMS product references).
- [ ] Collect literature on Nile-origin summer blooms off Israel into `background_material/literature/`.
- [ ] Conclude section 2 of `02_data_sources.md` (sources, baseline, methods) with the user.
- [ ] Review section 3 of `02_data_sources.md` (oceanography and modelling).

## Later
- [ ] Decide whether to rename the folder (`Greenpathch2026` → `Greenpatch2026`).
- [ ] The `benchmarks.csv` rows for `climatology_anomaly` cdom300_aph443 (84 s) and cdom300_r412_443 (4,942 s) from 2026-10-21 are inflated (computer asleep); ignore for cost estimates.

## Done
- [x] Accounts and Copernicus Marine login; pilot downloaded and run end to end (2026-10-21); full-domain dry run (2026-10-26).
- [x] CMEMS product IDs and variable names verified (2026-10-15/21); HR ~100 m from 2020; 300 m multi-year 2016-04-26 → 2026-10; ADG443 not available at 300 m.
- [x] Organic-matter source: five 300 m reflectance bands; main proxy a_dg443 (2026-10-20/26).
- [x] ACOLITE / own Sentinel-2–Landsat processing dropped (2026-10-26).
- [x] Pilot domain profile, per-domain folders, benchmarks (2026-10-21); stale pre-pilot outputs removed.
- [x] Stage 1 steps 3–10, image-usage audit, figures (2026-10-21); figures scale to any domain (2026-10-23); subfolders, date labels, 300 m chl movie (2026-10-26); HR movie dropped.
- [x] Autocorrelation correction (empirical ACF, n_eff) in bin, season and window tests (2026-10-26); FDR (BH q = 0.10), effect ×1.5, objects ≥ 1 km² (2026-10-26); manuscript 2.6 updated. Explainer: https://claude.ai/artifact/TVAKtvg5UKBssZkB2fQAQL
- [x] Paper figure bins 21 Jul – 10 Oct, 2 × 4 (2026-10-26).
- [x] Full domain fixed: Rosetta to Rosh HaNikra (2026-10-26).
- [x] Q2: model datasets in `config` and the downloader; Level A on chl and salinity (per-variable effect size), saw-tooth test, full domain: `08_q2_operational_model.py`, results in `07` section 8 (2026-10-30). October kept in (user).
- [x] Scope 2026-11-05: claim "not forecastable with present tools"; Q3 simplified + nudging experiment; Q1 land-input indicators; CDOM → salinity proxy and its assimilation for the next study (draft `08_next_study_draft.md`).
