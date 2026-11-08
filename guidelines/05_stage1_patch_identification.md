# 05 — Stage 1: statistical identification of the patch in space and time

Status: **proposed** (2026-10-14); **Part 1 (preprocessing) confirmed by the user 2026-10-21**, ⚙ parameters still provisional. Parameters marked ⚙ are provisional and must be tuned on the data or agreed with the user. Record final choices in `decisions_log.md`.

Scope: every step after download, from raw files to the final patch maps, time series and year comparison.

**Statistics run on the two Copernicus Marine products only (user decision 2026-10-20):**
- **OLCI300** — CMEMS multi-year 300 m OLCI, `009_143`: chlorophyll (daily, 2016-04-26 onward) and five reflectance bands (412.5, 442.5, 490, 560, 665 nm) for the organic-matter proxy.
- **HR** — CMEMS coastal high-resolution mosaic, `009_205`: chlorophyll, turbidity and suspended matter at ~100 m (2020-01-01 onward).

Own processing of Sentinel-2 / Landsat with ACOLITE was dropped from the project on 2026-10-26 (user). Steps 2 and 5, which existed only for it, are removed; the step numbers are kept because code and documents refer to them.

### Image-use rule (user requirement 2026-10-20)
**Every satellite image in the analysis season is used in the statistics.** In practice:
- **No image is discarded** for low coverage, clouds or quality. Coverage thresholds below only *flag* images or values (and drive sensitivity tests); they never remove them.
- **Masking acts on pixels, not images:** a pixel is set to missing only where the retrieval itself is invalid (cloud, land, provider quality flag, implausible value). The valid pixels of a partly cloudy image always enter the statistics.
- **"Image" = one daily Level-3 field** of each product. The provider has already merged all overpasses of that day (Sentinel-3A and -3B for OLCI300; Sentinel-2 and Landsat tiles for the HR mosaic). Separate overpasses within one day are not available in these products.
- **Audit:** the pipeline writes `results/tables/image_usage.csv`: one row per product and date from the inventory, with the number of valid pixels and the 10-day bin(s) it entered. Any image that exists in the inventory but entered no statistic is reported as an error.
- Files are organised for processing convenience (one NetCDF per product and season, one layer per day); the organisation never affects which images are used.

Notation: pixel *p*, date *t*, year *y*, calendar window *w*. *x(p,t)* = log10(chlorophyll). Baseline years *B* = 2016–2025 (⚙). Event year 2026. Analysis season 1 July – 31 October (⚙).

---

## Part 1 — Common preprocessing (all methods)

### Step 1. Inventory and integrity
- Build a file inventory table (`data/interim/inventory_<product>.csv`) with date, time, sensor, tile, file size and checksum.
- List missing dates per product and season. This drives the later coverage checks.
- **Implemented:** `scripts/01_inventory.py` (library code in `src/greenpatch/inventory.py`). Run with `--valid-fraction` to add the valid-pixel fraction per date in the domain. Outputs: `data/interim/inventory_<product>.csv`, `data/interim/availability_<product>.csv`, `results/tables/inventory_summary.csv`, `results/tables/missing_dates.csv`, `results/figures/inventory_coverage.png`. Tested on synthetic data only (2026-10-14).

### Step 2. *(removed 2026-10-26: atmospheric correction was needed only for own Sentinel-2/Landsat processing; both products arrive as Level-3)*

### Step 3. Quality masking
- **Product flags:** apply the provider quality flags (CMEMS flags; clouds are already masked by the provider).
- **Sun glint:** discard pixels with residual glint above a threshold ⚙.
- **Land and adjacency:** exclude pixels on land and a buffer next to the coastline ⚙ (1 pixel for both products). Keep the buffer small; the patch is nearshore.
- **Plausible range:** keep 0.01–100 mg/m³ ⚙.
- **Speckle and outliers:** 3×3 median-based outlier filter (flag pixels > 3 robust SD from the local median).
- **Implemented 2026-10-21** (`src/greenpatch/preprocess.py`, `scripts/05_preprocess.py`). User decisions: the outlier check is a **flag only** (values never changed or removed; no smoothing); a sensitivity run may exclude flagged pixels. **`QI_CHL` is not a quality flag**: the file metadata define it as `(log(daily) − climatology median) / climatology SD`, i.e. an anomaly score, so it is never used for masking and is kept only as a diagnostic (`qi_vs_z.png`). Land = cells never valid in the record or on land in GSHHG, plus a 1-pixel buffer. Pilot: 5–10 % of values flagged, higher than expected from a 3-SD rule (⚙ revisit).

### Step 4. Gridding
- **Decision 2026-10-21 (user): both products stay on their native geographic grids**; no reprojection of HR to UTM. Cell areas (km²) and distances are computed from the coordinates (UTM 36N for distances). Grids are not square: 300 m ≈ 325 × 299 m, HR ≈ 125 × 102 m.

### Step 5. *(removed 2026-10-26: inter-sensor harmonisation; OLCI300 and HR are harmonised by the provider)*

### Step 6. Variables
- Main variable: *x* = log10(chl). Chlorophyll is close to log-normal, and log differences are ratios.
- Parallel variable (freshwater signal): a coloured-organic-matter proxy computed from the five OLCI300 reflectance bands (decision 2026-10-20; ADG443 does not exist at 300 m). Every method below is run on both.
  - **Computed immediately after each download, then the bands are deleted** (user instruction 2026-10-20). Implemented in `src/greenpatch/cdom.py`, run automatically by `scripts/03_download_cmems.py` (or `scripts/04_compute_cdom.py` for files on disk). Output: `data/interim/cdom300/cdom_cmems-olci_300m_<year>_<MMDD-MMDD>_qaa.nc`.
  - Three proxies are stored, so the algorithm choice stays open after the bands are gone: **adg443** (dissolved + detrital absorption at 442.5 nm, QAA v6), **aph443** (phytoplankton absorption at 442.5 nm, QAA v6; separates algae from CDOM), **r412_443** (Rrs(412.5)/Rrs(442.5); lower = more CDOM). Choose the main proxy ⚙ on pilot data.
  - [VERIFY] pure-water absorption constants and QAA v6 coefficients in `cdom.py` against the QAA v6 document before publication. Sanity test (2026-10-20): clear Levantine spectrum adg443 ≈ 0.009 m⁻¹, CDOM-rich plume spectrum ≈ 0.17 m⁻¹.
  - HR has no organic-matter variable; its turbidity and suspended matter are used as the nearshore freshwater/sediment signal instead.

### Step 7. Coastal coordinate system
- Coastline: high-resolution vector coastline (GSHHG full resolution or OpenStreetMap), stored in `background_data/coastline/`.
- **Implemented 2026-10-21** (`src/greenpatch/geo.py`): GSHHG v2.3.7 full resolution (`scripts/tools/fetch_coastline.py` → `gshhg_f_L1_east_med.geojson`). A 500 m closing bridges the Suez Canal. For *s* only, a 3 km closing ⚙ removes lagoon outlets (Manzala, Bardawil) and the line is simplified by 2 km ⚙. Check values: Port Said s ≈ 55 km, Wadi Gaza ≈ 296 km, Gaza border ≈ 315 km, Ashkelon ≈ 322 km, Tel Aviv ≈ 375 km, Haifa ≈ 462 km.
- **Distance to coast** *n(p)* in km for every pixel.
- **Alongshore coordinate** *s(p)* in km: distance along a smoothed coastline from a reference point at the Nile delta ⚙ (e.g. Damietta mouth), increasing northward.
- Locations of desalination intakes, sewage outfalls and river mouths, mapped onto (*s*, *n*), from `background_data/infrastructure/`.

### Step 8. Temporal binning (agreed with user 2026-10-14: 10-day bins, 30-day bins acceptable)
- **Standard time unit for statistics: 10-day bins**, fixed in the calendar (days 1–10, 11–20, 21–end of each month), the same in every year. The season July–October has 12 bins.
- **Fallback: 30-day bins** (calendar months), used where 10-day bins are too sparse, mainly HR in the baseline. The rule ⚙: switch a product to 30-day bins if more than a third of its coastal-strip pixel-bins fail the sufficiency rule in Step 9.
- Each bin stores both the composite (median of valid observations) and the individual observations, with their count. The composite is used for maps and for Methods B and C; the individual observations feed the per-pixel tests in Method A.
- Daily OLCI300 values are kept for case-study figures and for the onset/end refinement in Method C.
- **Implemented 2026-10-21:** the 30-day fallback rule is applied automatically per product (`config.BIN = "auto"`, threshold one third). Pilot result: 300 m chl and CDOM keep 10-day bins (0 % failing); **HR switches to monthly bins** (100 % of pixel-bins fail with 10-day bins; ~10 observations per pixel-bin). The choice is stored in each file (`bin_kind`, `bin_choice`).

### Step 9. Baseline climatology
For each pixel *p* and calendar bin *w* (10-day, or 30-day fallback), pool all valid baseline observations falling in that bin.
- Statistics: median *m*, robust standard deviation *σ* = 1.4826 × MAD, 90th and 95th percentiles, maximum, number of observations *N*, number of years with data.
- Data sufficiency rule ⚙: *N* ≥ 20 and ≥ 6 of the 10 baseline years; otherwise the pixel-window is flagged "insufficient": it is excluded from the per-pixel significance *test* (too few values for a valid test), but its observations still enter the maps, composites and Methods B and C. No image is lost by this rule.
- **HR baseline caveat:** HR starts in 2020, so its baseline is 2020–2025 (6 years). The sufficiency rule for HR becomes ≥ 4 of 6 years ⚙. With 6 years, the one-value-per-year test (Method A2) is weak (the best possible rank-based p is 1/7 ≈ 0.14, and the parametric version rests on 5 degrees of freedom). For HR, rely mainly on the observation-level test (A1) with 30-day bins, and use OLCI300 (10-year baseline) for the formal significance claim.
- 2026 is never part of the baseline.

### Step 10. Anomalies
For every 2026 (and every baseline-year, for comparison) observation:
- Log-ratio anomaly: *Δx* = *x* − *m* (Δx = 0.3 means twice the usual chlorophyll).
- Robust standardized anomaly: *z* = (*x* − *m*) / *σ*.
- Percentile rank of *x* within the baseline pool.
- Exceedance flags: above P90, above P95, above the baseline maximum.

Baseline years get "leave-one-year-out" anomalies, computed against a baseline excluding that year, so that every year is compared fairly with 2026.

**Steps 9–10 implemented 2026-10-21** (`src/greenpatch/climatology.py`, `scripts/06_climatology_anomaly.py`), with the image-usage audit (`results/<domain>/tables/image_usage.csv`). The per-pixel A1 p-value is computed for the p-value maps, but **without the autocorrelation correction or FDR** (Method A, not yet confirmed); it is labelled "uncorrected" everywhere. The test direction follows each variable's signal (`r412_443`: lower = more CDOM). Figures: `scripts/07_figures_stage1.py` → `results/<domain>/figures/stage1/` (figure set agreed with the user 2026-10-21).

---

## Part 2 — Three methods for identifying the patch

All three share Part 1. They answer different questions and are designed to be used together.

### Method A — Pixel-wise significance with field-significance control
**Question:** where, and in which weeks, was 2026 significantly higher than the baseline?

1. **Event windows:** the 10-day bins of Step 8 (30-day fallback for sparse products).
2. **Per-pixel test** — two variants; run both and report where they disagree:
   - **A1, observation-level, non-parametric:** compare the individual 2026 observations in the bin with all baseline observations of the same calendar bin. One-sided Mann-Whitney U test (H₁: 2026 > baseline).
   - **A2, bin-composite level, parametric:** treat each year's bin composite as one value; 10 baseline values versus the 2026 value. Test whether 2026 lies above the baseline prediction interval: *t* = (*x*₂₀₂₆ − mean) / (*s* √(1 + 1/*n*)), with *n* − 1 = 9 degrees of freedom. This assumes log-chlorophyll composites are roughly normal; check with a Shapiro-Wilk test or Q-Q plots on the baseline.
   - Why two variants: A2 is clean (years are independent), but a rank-only version of it cannot go below p = 1/11 ≈ 0.09 with 10 baseline years. The parametric form can reach p < 0.05 at the cost of the normality assumption. A1 has more data but needs the autocorrelation correction in step 3.
3. **Autocorrelation correction (A1):** observations inside a bin are not independent. ~~Estimate lag-1 autocorrelation *ρ* of daily anomalies and replace *n* by *n*(1 − *ρ*)/(1 + *ρ*).~~ **Implemented and confirmed by the user 2026-10-26 in its general form:** *n*_eff = *n*² / Σᵢ Σⱼ *r*(|*t*ᵢ − *t*ⱼ|) over pairs of observations of the same year (years independent), with *r*(*k*) the empirical autocorrelation of the baseline daily anomalies at lags 0–30 days per pixel (tile-pooled where < 20 pairs ⚙, interpolated where no pairs, floored at 0; 2026 excluded). Both *n*₁ and *n*₂ of the Mann-Whitney variance are replaced. Reason: the lag-1 AR(1) formula fails on the data. HR (Sentinel-2 based) has no lag-1 pairs at all; 300 m anomalies decay much more slowly than AR(1) (r = 0.63 at 1 day, 0.32 at 5, 0.27 at 10; AR(1) predicts 0.11 at 5) because each year keeps its own state through the season; cloud gaps make the gap-free formula wrong. Uncorrected p kept as `*_uncorr`. Code: `climatology.anomaly_acf`, `pair_sums`, `n_effective`.
4. **Multiple testing across pixels:** Benjamini-Hochberg false discovery rate with *α*_FDR = 0.10, which approximates a 0.05 global level under spatial correlation (Wilks 2016, *BAMS*). **Implemented 2026-10-26** over all tested sea pixels of the whole domain per map (year × bin; also the whole season and each movie window), product-wide after the tiles (`src/greenpatch/significance.py`, `<var>_significance.nc`: q-values, `sig`).
5. **Effect size:** also require median *Δx* ≥ log10(1.5) (≥ 50 % higher), so that tiny but significant differences do not count. **Kept by the user 2026-10-26; implemented** (`elevated`).
6. **Cleaning:** remove isolated significant objects smaller than a minimum area (1 km² ⚙, 8-connected). **Accepted by the user 2026-10-26; implemented** (`patch` = significant & elevated & cleaned).
7. **Spatial outputs:** significance map per window; maximum extent (union over windows); "core" (pixels significant in ≥ 3 windows ⚙); areas in km².
8. **Temporal outputs:** significant area *A*(*t*) per 10-day bin. Onset = first bin with *A* > *A*_min ⚙, kept only if ≥ 2 consecutive bins exceed it; end = last such bin; peak = maximum *A*. Temporal precision is therefore ±10 days; Method C refines onset and end with daily OLCI300 data.

Strengths: formal statistical answer to "significantly higher than previous years". Weaknesses: needs dense data, so it is strongest on OLCI300 and coarse in time on HR (monthly bins); sensitive to coverage gaps.

### Method B — Object-based patch detection and tracking
**Question:** what was the size, shape and life cycle of the patch, and how does it compare with each previous summer's patch?

**Scope confirmed by the user 2026-11-08 (reduced form):**
- Relative P90 threshold (leave-one-year-out) as the main mask, with P85 and P95 as sensitivity. The absolute 1 mg m⁻³ threshold goes in the supplement only.
- Steps 1–5 and 7–9 apply. Per-year metrics: maximum area, area-days, alongshore extent, offshore reach and duration.
- **Step 6 (tracking) is dropped.** Onset and end in step 7 are taken from the daily area series, not from a track.
- Not implemented yet.

1. **Exceedance mask per 10-day composite**: pixel is "patch" if *x* > baseline P90 for its pixel and bin (relative threshold) ⚙. Run the absolute alternative (*chl* > 1 mg/m³ ⚙) in parallel. Composites fill most cloud and swath gaps, so tracking becomes bin-to-bin.
2. **Coverage flag (no discarding):** composites where < 50 % ⚙ of the 0–10 km coastal strip is valid are *flagged* "low coverage"; they still enter all metrics. Invalid pixels are "unknown", never "not patch". Area metrics on flagged composites are reported as a range: observed area (lower bound) to observed + adjacent unknown area (upper bound). A sensitivity run without flagged composites shows their influence.
3. **Morphological cleaning:** opening then closing with a small structuring element; remove objects below a minimum area ⚙.
4. **Labelling:** connected components with 8-connectivity (scikit-image). Keep objects within 2 km ⚙ of the coast.
5. **Descriptors per object:** area; alongshore extent (*s*_min, *s*_max); maximum and mean offshore distance; centroid; mean *Δx*; integrated anomaly (Σ *Δx* × pixel area).
6. **Tracking:** link objects in consecutive bins when they overlap (intersection-over-union > 0.1 ⚙) or when the centroid moved less than *v*_max × Δ*t*. *v*_max ≈ 40 km/day ⚙ allows for the coastal current. Handle merges and splits; tolerate one bin ⚙ without valid data. With 10-day bins the patch may move far between bins, so overlap matters less than alongshore continuity; daily OLCI300 tracking is an optional refinement.
7. **Event definition:** onset = first date of the main track with area > *A*_min; end = last such date; also peak date, peak area, duration, area-days integral and northernmost extent.
8. **Year comparison:** run the identical procedure on each baseline year, with leave-one-year-out thresholds. Compare 2026 with the 10-year distribution of each metric, by rank and by robust z-score.
9. **Sensitivity:** repeat with P85, P90, P95 and with absolute thresholds 0.5, 1, 2 mg/m³ ⚙. Report how the metrics change.

Strengths: intuitive size and duration; follows the patch as it moves, which bears on the Nile-versus-Gaza question. Weaknesses: depends on the threshold; year-level comparison rests on only 10 baseline years.

### Method C — Alongshore Hovmöller diagrams and change-point detection
**Question:** when did the patch arrive at each part of the coast, how fast did it spread, and how does each year compare in one number?

**Scope confirmed by the user 2026-11-08 (reduced form):**
- Steps 1–3: the Hovmöller diagrams per year.
- Step 5: arrival at each desalination intake and the spreading speed (Theil-Sen). Both are read from the existing daily onset map (`significance.onset`).
- Step 6: the integrated index per year.
- **Step 4 (PELT/Pettitt change points) is dropped**, because the onset map already gives the onset of every pixel. Step 7 is optional.
- Headline year comparison: B area-days together with the C index.
- Not implemented yet.

1. **Bins:** alongshore bins of 5 km ⚙ × offshore bands 0–1 km (HR only), 1–5, 5–15 and 15–30 km ⚙.
2. **Bin series:** for each spatial bin, median *Δx* of valid pixels per 10-day bin (the statistical series) and per day for OLCI300 (the refinement series). Every value is kept, together with the valid fraction of its spatial bin; values from bins < 30 % ⚙ valid are *flagged*, not dropped, and a sensitivity run without them shows their influence.
3. **Hovmöller diagrams:** alongshore distance versus time (10-day bins; daily for OLCI300), one panel per year and band. Short gaps may be interpolated for display only; statistics use unfilled data.
4. **Onset and end per spatial bin:** change-point detection on the daily OLCI300 series, constrained to fall within the onset/end 10-day bins found by Method A. The 0–1 km band, covered only by HR, gets monthly precision.
   - Main: PELT algorithm (`ruptures` package) with a mean-shift cost and a BIC-type penalty ⚙.
   - Check: Pettitt test for a single change point, and a persistence rule (*Δx* > baseline P90 for ≥ 5 consecutive valid days ⚙).
5. **Propagation:** regress onset date against alongshore position (Theil-Sen, robust) to get speed (km/day) and direction. Read the arrival date at each desalination intake (Ashkelon, Ashdod, Palmachim, Sorek, Hadera).
6. **Integrated index per year:** *I*(*y*) = Σ over bins and days of max(*Δx*, 0) × bin length, in km·days, plus the number of exceedance bin-days. Compare 2026 with the baseline years.
7. **Bin-level test:** apply the Method A test to each bin, then Benjamini-Hochberg across bins. Aggregating to bins reduces noise and the number of tests.

Strengths: compact figures and indices for comparing years; arrival times at the plants; propagation direction relevant to source attribution. Weaknesses: collapses cross-shore structure into a few bands.

### Recommended use
- **A** supports the significance claim and the significance map.
- **B** gives the patch size, shape and life cycle.
- **C** gives timing, propagation and the year-by-year comparison.
- Where they disagree, report the disagreement; it usually points to coverage or threshold problems.

---

## Part 3 — Validation and uncertainty

1. **Product cross-check:** HR aggregated to 300 m versus OLCI300 on the same day. Metrics in log space: bias, RMSD, median absolute percentage difference.
2. **In-situ matchups:** IOLR monitoring data and desalination intake records (chlorophyll, turbidity). Satellite value = median of a 3 × 3 pixel box ⚙ around the station, within ± 1 day ⚙ for daily intake data. Also compare the intake time series with the pixel time series at the intake.
3. **Chlorophyll versus coloured organic matter:** run every method on both variables. Map where the anomaly is chlorophyll-only, organic-matter-only, or both. This bounds how much of the patch is real phytoplankton.
4. **Sensitivity:** thresholds, window lengths, baseline sub-periods (2016–2020 versus 2021–2025), data-sufficiency rules, coastal buffer width.
5. **Coverage bias:** compare the number of valid observations in 2026 with the baseline. A clearer summer gives more detections even with no real change; normalise metrics by coverage where needed.

---

## Part 4 — Outputs

| Output | Method | Location |
|---|---|---|
| Climatology and anomaly fields | Part 1 | `data/processed/` |
| Significance maps, extent and core maps | A | `results/maps/` |
| Significant area time series | A | `results/tables/`, `results/figures/` |
| Object tables and tracks per year | B | `results/tables/` |
| Patch life-cycle metrics per year | B | `results/tables/` |
| Hovmöller diagrams | C | `results/figures/` |
| Onset/arrival per bin and per desal plant | C | `results/tables/` |
| Integrated index per year | C | `results/tables/` |
| Validation statistics | Part 3 | `results/tables/` |

## Open decisions
- All ⚙ parameters, especially thresholds, windows, minimum areas and the reference point for the alongshore coordinate.
- ~~Availability of the organic-matter variable (ADG443) in the 300 m product.~~ Computed from the reflectance bands (QAA); main proxy a_dg443 (user 2026-10-26).
- Access to in-situ data for validation.

## Reference
- Wilks, D. S. (2016). "The stippling shows statistically significant grid points": How research results are routinely overstated and overinterpreted, and what to do about it. *Bulletin of the American Meteorological Society*, 97(12), 2263–2273.
