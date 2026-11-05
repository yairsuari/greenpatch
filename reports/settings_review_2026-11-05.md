# Settings to review before the full-domain run (2026-11-05)

For the user. Each ⚙ setting of the satellite pipeline, its current value, what it did on the pilot (5 × 5 km box),
and whether it can be changed cheaply after the big run. **Baked in** = inside steps 05/06, so changing it later
means rerunning the whole domain; **post-hoc** = applied after the tiles (`06 --significance-only`, figures), cheap.
Numbers from `results/pilot/tables/preprocess_summary.csv` and the pilot outputs.

## A. Baked in — please decide before the run

| # | Setting | Current | Pilot effect | Recommendation |
|---|---|---|---|---|
| 1 | Coastal buffer (`config.PREPROC buffer_px`) | 1 pixel: 300 m (OLCI), ~100 m (HR) | 27 of 174 sea cells at 300 m (16 %), 72 of 1,310 at HR (5 %); 8,222 valid 300 m chl values dropped in land or buffer cells (89,713 kept) | Keep 1 pixel at 300 m. At HR, 100 m may be too little against land adjacency (often a few hundred m) [VERIFY]; consider 3 pixels (~300 m) so both products start at the same distance from the coast. |
| 2 | Plausible ranges (`vmin`, `vmax`) | chl 0.01–100; turbidity, SPM 0.01–1000; a_dg443, a_ph443 1e-4–10 m⁻¹; Rrs412/443 0.05–5 | Removed: chl 2 values; a_dg443 894 (1.2 %); a_ph443 45; Rrs412/443 632 (0.8 %) | Chl fine (no saturation at 100; see the ceiling check). **a_dg443 upper limit 10 m⁻¹ is too loose:** 1–3 Oct 2026 box medians of 5–9 m⁻¹ are QAA failures, not water. Suggest ⚙ 2 m⁻¹ [VERIFY against coastal literature values]. |
| 3 | Data sufficiency (`SUFFICIENCY`) and bins (`BIN = auto`) | ≥ 20 baseline values in ≥ 6 years (HR ≥ 4); 10-day bins, monthly if > 1/3 of pixel-bins fail | 300 m stays at 10-day bins; HR falls back to monthly | Keep. On the full domain HR will very likely be monthly too. |
| 4 | Autocorrelation max lag (`MAX_LAG`) | 30 days | Median ACF of 300 m chl at lag 30 = 0.09 (not yet zero) | 60 days for the whole-season test (slightly anti-conservative now); bins and windows are unaffected (shorter than 30 days). |
| 5 | HR autocorrelation | empirical, pooled per tile below 20 pairs | Noisy: ~5 pairs per lag per pixel (0 at lags 8–9, 0.63 at 18) | Fit a simple exponential decay to the first lags instead of the raw ACF ⚙. Affects only HR p-values. |
| 6 | Daily window half-width (`WINDOW_HALF`) | ± 5 days (11-day window) | Used by the movie and the new onset map | Keep. |
| 7 | 2026 data end | Pilot: 13 Oct (300 m), 19 Oct (HR) | The archive now reaches 27 Oct 2026 (300 m) | The full-domain download will take everything up to the run date. Accept that October 2026 is then longer than in the pilot? |
| 8 | **SST** (new indicator) | not yet chosen | — | See section C. |

## B. Post-hoc — can change after the run

| # | Setting | Current | Note |
|---|---|---|---|
| 9 | Outlier flag (3×3 local median, `OUTLIER`) | flags 4–9 % of values (chl 300 m 7.7 %, HR chl 4.6 %, CDOM 7.9–8.6 %) | Flag only, never used to mask; a diagnostic. Can stay as is. |
| 10 | Effect size (`EFFECT_MIN`) | ×1.5 | Sensitivity run planned (×1.25, ×2). |
| 11 | Minimum object area (`MIN_AREA_KM2`) | 1 km² | Sensitivity run planned (0.5, 2 km²). On the pilot no object was removed. |
| 12 | FDR level | q = 0.10 (Benjamini-Hochberg over the whole domain per map) | Agreed 2026-10-26. |
| 13 | Onset persistence (`ONSET_PERSIST`, new) | 3 consecutive patch days | Pilot onset 27 Aug – 5 Sep; offshore pixels first, nearshore last (could be fewer nearshore observations: check on the full domain). |

## C. Open choices from this session

- **SST dataset.** Candidates (catalogue checked 2026-11-05, all 2008 → present):
  - L3S NRT `SST_MED_SST_L3S_NRT_OBSERVATIONS_010_012_b` (~1 km, observations only, quality levels): real values with
    gaps, which our pipeline already handles; **recommended** for the statistics.
  - L4 NRT UHR `SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_c_V2` (~1 km, gap-free, interpolated): smoother; the
    interpolation adds artificial autocorrelation and can smear a narrow coastal plume. Good for maps.
  - L4 REP `010_021` (~5 km): too coarse; ends 2026-10-06.
  Both NRT products are night-time (foundation) SST, so warm daytime surface layers of a plume are partly removed.
- **SST test direction.** A plume can be warmer or cooler than the sea, and upwelling is cooler. The pipeline tests
  one direction. Options: two-sided for SST, or descriptive only (anomaly maps inside/outside the patch, no test).
  Recommendation: descriptive only, since SST is an indicator here, not a claim.
- **Magnitude of the patch** (ceiling check): 300 m and HR chl agree in 2020–25 but in Sep–Oct 2026 the 300 m product
  is ×3.5 higher than HR on the same days. How to report the magnitude (range across products?) and which one to
  compare with the model in Q2.
