# Session handoff — Green Patch 2026

Last updated: 2026-11-06 (sessions 13 October – 6 November 2026; last: Nile forcing of the operational system recorded; before that scope settled, preparation for the remote machine, decisions round, GitHub).
Read this first in a new session, then the files listed in `CLAUDE.md`. Detailed decisions with dates and reasons are in `decisions_log.md`; open tasks in `todo.md`; server instructions in `06_local_pilot.md`. This file is the summary, not the record.

## Where the project stands
- **2026-11-06 — Nile in the operational system** (`07` section 2b, from QUIDs 006_013 issue 2.6 and 006_014 issue 3.3): a monthly climatological discharge (Said et al. 2011), the same every year, shared by physics and BGC. Nutrient loads = discharge × fixed reference concentrations (N, P, Si, ALK, DIC) for the land macro-region. Apparently one input point. Change log dated 25 Nov 2025, so in force in 2026. The Nile values, concentrations and grid cell are not in the QUIDs → added to the OGS questions (`todo.md`). (A transient GitHub "fatal error in commit_refs_rules" on push was solved by retrying.)
- **2026-11-05 — scope settled:** the paper's claim is "not forecastable with present operational tools"; the missing land input (fresh water + nutrients) is the leading hypothesis, tested in a separate continuation study (draft `08_next_study_draft.md`). Q3 reduced to simplified perfect-forcing runs with/without a land input, plus a nudging experiment (chl only / chl + nutrients above a threshold / chl + coastal source); forecast-mode run types (a)/(b) deferred. Q1 adds land-input indicators (CDOM, turbidity, SST, onset map). Satellite SSS not used; CDOM-salinity proxy left for the next study. QUIDs: satellite chl corrects only phytoplankton (not dissolved nutrients); the weekly analysis window starts on Monday (explains the saw-tooth jump). `00`, `01`, `03` and the manuscript Introduction/title not yet updated to this scope.
- **2026-11-05 (later) — preparing for the stronger machine** (`todo.md` reorganised by phase):
  - **Ceiling check** (`scripts/tools/check_chl_ceiling.py`): no saturation; a_ph443 rises with chl and the CDOM share falls, so CDOM inflation is unlikely. **But 300 m and HR chl disagree in Sep–Oct 2026** (300 m ≈ ×3.5 higher on the same days; they agree in 2020–25). The patch is robust, its magnitude product-dependent: user to decide how to report it.
  - **Onset map** (`significance.onset`, `onset_<p>_<v>.png`) and **co-location table** (`colocation_chl_patch.csv`) added; pilot onset 27 Aug – 5 Sep; pilot signature = phytoplankton, not a CDOM-rich plume.
  - **Settings review for the user:** `reports/settings_review_2026-11-05.md` (baked-in vs post-hoc settings; SST choice pending).
  - **Q3 simplified design** drafted in `03_models.md` (S0, S1, N1–N3).
- **2026-11-05 (end) — decisions from the question round** (all in `decisions_log.md`): magnitude reported as a range across 300 m and HR (Discussion paragraph added to the manuscript, tracked, 6 new references); SST = L3S `010_012_b`, two-sided test; HR buffer 3 px; a_dg443 max 2 m⁻¹; season max lag 60 d; 2026 data as available on run day; **Q3 = operational chain OGSTM-BFM offline + 3DVarBio** (ask OGS for forcings incl. vertical diffusivity and a BFM restart; fallback own nested NEMO v4.2); Q2 Level A descriptive only. **Settings not yet implemented** (todo Phase 1). Project now on GitHub (`yairsuari/greenpatch`, branch `main`); next sessions run from a second laptop via Remote-SSH on the machine (`09_remote_setup.md`).
- **Q2 first results (2026-10-30, `07` section 8):** model chl (reanalysis-interim, Jul–Sep) has 2026 as the highest of 11 years along the Israel/Gaza coast in all September bins, but only ×2 (satellite ×7–9) and at ~0.1 mg m⁻³ (satellite 12–25); no FDR-significant cell (no power: n_eff ≈ 1.4); weekly saw-tooth (Monday jumps, decay ×0.56–0.67 over 5 days in 2026); model salinity shows no freshening. Operational analysis offset vs reanalysis at the coast (salinity +0.2 psu); October 2026 is still appended (user decision), so October results carry that caveat. Manuscript: all tracked changes accepted 2026-10-30 at the user's request (backup `ms_draft_2026-10-30_1654_tracked.docx`); later edits are tracked again. Model data are processed with `--domain full` (only ~50 MB).
- **One paper, three questions (2026-10-26/30):** Q1 observed patch (satellite; the work so far), Q2 did the operational Med biogeochemical system represent the patch even in its best estimate and could it have forecast it (`07_q2_operational_model.md`), Q3 could it have been forecast and what would that require (own model reforecasts, `03_models.md`, not yet reviewed). OGS confirmed (2026-10-29) that issued forecasts are not archived, so Q2 is an upper-bound test on the analysis plus a saw-tooth test and input/physics diagnostics. From the product documentation: weekly assimilation of satellite chl (coast included); only a climatological Nile among land inputs in the SE Levantine (no Gaza, Israeli streams, wastewater); largest negative coastal chl bias of the Med in the southern/eastern Levantine. User-readable reasoning: `q2_way_forward.md` (project root).
- **Stage 1 runs end to end on real data in the 5 × 5 km pilot box** at the Gaza–Israel border (31.570–31.615°N, 34.452–34.505°E). The user calls this "the small domain"; in code it is `--domain pilot` (the default). Chain: download → inventory → preprocessing → climatology/anomalies → figures. 47 figures and one movie in `results/pilot/figures/stage1/{chlorophyll,cdom,turbidity,combined}/` (last generated 2026-10-26). No HR movie (user: HR p-values cannot be computed in 11 days). Draft manuscript figures `paper_<product>_<var>.png` (anomaly per bin with p < 0.05 contour) and `combined/autocorrelation.png`. The movie `chlorophyll/movie_olci300_chl_window11d.mp4` shows the 2026 chl anomaly and p-value in an 11-day window (day ±5) stepped daily, 1 Jul–13 Oct.
- **Data in hand (pilot):** 300 m chl 2016–2026, CDOM proxies 2016–2026, HR 2020–2026. The archive ends 14 Oct 2026 (300 m) and 20 Oct 2026 (HR). The pilot's 300 m reflectance bands were deleted on 21 Oct under the old rule. **Re-fetch:** `03_download_cmems.py --datasets rrs300` (raw data are now kept).
- **The code is ready for the full domain on an external machine.** Processing is tiled, parallel (`--workers`) and batch-friendly (`--tile k`). Figures scale to any domain. Not yet run on the full domain: about 195 GB of transfer and about 150–200 GB on disk.
- **Manuscript** `reports/ms_draft.docx`: Introduction (5 paragraphs) and Methods 2.1–2.7, written 2026-10-22 as tracked changes by Claude, with many `[VERIFY]` marks. No Results yet.
- **Q3 (own model, attribution)** is a draft in `03_models.md` (run types and reforecast design agreed in outline 2026-10-30; model choice not reviewed). Q2 is not implemented yet (next: download model datasets for an intermediate box).

## First pilot results (not yet a claim)
- **Since 2026-10-26 (later): FDR, effect size and minimum area are applied too** (`significance.py`). The "patch" = BH q ≤ 0.10 over the whole domain per map, ≥ ×1.5, objects ≥ 1 km². 300 m chl 2026: 21–31 Aug 0 of 145 (51 had p < 0.05; smallest p 0.015 cannot pass with 145 tests); 1–10 Sep 147/147, 11–20 Sep 146, 21–30 Sep 147, 1–10 Oct 145/145. HR chl: Sep 1,156 of 1,212, Oct 788 of 821 (7 small groups removed). Onset is therefore "between late August and early September".
- **Since 2026-10-26 all p-values are corrected for autocorrelation** (effective n from the empirical autocorrelation of baseline daily anomalies; see `decisions_log.md`); **no FDR yet**. 300 m chl 2026, 10-day bins, p < 0.05 pixels (of 147), uncorrected → corrected: 21–31 Aug 113 → 51; 1–10 Sep 147 → 145; 11–20 Sep 147 → 131; 21–30 Sep 147 → 141; 1–10 Oct 145 → 142. A 2026 bin ≈ 2 independent observations. The whole-season test drops a lot (300 m chl 147 → 12 pixels; HR turbidity 105 → 0) because a season of one year ≈ 5–8 independent observations and Jul–Aug were normal. Autocorrelation at 300 m: 0.63 (1 day), 0.27 (10 days); HR: no lag-1 pairs (Sentinel-2 revisit), noisy ACF.
- The numbers below are the original uncorrected results:
- **300 m chlorophyll, 2026 vs 2016–2025:** box median ×2.7 in 21–31 Aug and ×6.5–9.4 from 1 Sep to 10 Oct. p < 0.05 in nearly every pixel. Box-median chl 25 mg m⁻³ in 1–10 Sep (2016–2024: about 1–5). Early August was *below* normal (×0.3–0.6).
- **Whole season** (median of daily anomalies): chl elevated and significant in 147/147 pixels; CDOM (`adg443`) 14/147; HR turbidity 105/1212.
- **Phytoplankton absorption `aph443`** rises with chl (×3–7). **CDOM proxies are mostly not elevated** (`adg443` only in 1–10 Oct; `r412_443` 7 significant pixel-bins). **HR chl and turbidity** are ×1.7–4 in Sep–Oct. This points to algae rather than an organic-matter signal, but turbidity also rose.
- **Coverage** in 2026 is not lower than usual, so this is not a cloud artefact.
- **2025 was also high in September** (box-median chl 5–8 mg m⁻³); 2021 and 2023 had high September bins too. Possible upward trend. 2026 is still 2–5× above 2025. Not yet discussed with the user (`todo.md`).
- **Caveats:** values near the product ceiling (daily up to ~95 of max 100) need a check for sediment or CDOM inflation of band-ratio chl. The p-values have no autocorrelation or FDR correction. The 5 × 5 km box truncates Methods B and C.

## Key decisions (all in `decisions_log.md`)
| Topic | Decision |
|---|---|
| Language | Work and documents in English, even when the user writes in Hebrew (the user sometimes types English with a Hebrew keyboard layout; decode it) |
| Data | **Two Copernicus Marine products only (ACOLITE dropped 2026-10-26):** 300 m OLCI multi-year (`009_143`, from 2016-04-26) and ~100 m HR coastal mosaic (`009_205`, from 2020-01-01). Dataset IDs in `config.CMEMS`. Sentinel-2/Landsat + ACOLITE not used for statistics; role pending |
| Organic matter (CDOM) | Three proxies from the five 300 m reflectance bands: `adg443`, `aph443` (QAA v6), `r412_443` (lower = more CDOM; tests use that direction). Main proxy not chosen |
| Raw data (2026-10-23) | **Kept.** Reflectance bands are no longer deleted after CDOM (`--delete-bands` to delete). Satellite files may still be deleted after a verified slim copy, only on explicit flag |
| Domains | `pilot` = 5 × 5 km at the border (local; "small domain"); `full` = Rosetta to Rosh HaNikra, 31.0–33.15°N, 30.0–35.2°E (user 2026-10-26; dry run 139 GB: chl300 18, rrs300 31, HR 90) (external machine). Select with `--domain` or `GREENPATCH_DOMAIN`. Separate folders per domain |
| Season / baseline | 1 Jul–31 Oct; baseline 2016–2025 (300 m), 2020–2025 (HR), each year compared with a leave-one-year-out climatology. Formal significance rests on the 300 m product |
| Bins | 10-day calendar bins; monthly fallback applied automatically when more than 1/3 of sea pixel-bins fail sufficiency (HR → monthly) |
| Preprocessing | log10 for chl/absorption/turbidity/SPM; `QI_CHL` is the provider's anomaly score, diagnostic only; 3×3 outlier check = flag only (no smoothing; 5–10 % flagged, ⚙ to review); 1-pixel coastal buffer; native grids; GSHHG full-resolution coastline for distance n and alongshore s |
| Test | One-sided Mann–Whitney per pixel and bin (rank-based), and per pixel over the whole season. Kept although log-chl is near-normal when pooled; the parametric A2 stays in the plan. **Not yet corrected** for autocorrelation or FDR |
| Image use | Every daily field enters the statistics; masking per pixel only; audit `results/<domain>/tables/image_usage.csv` (pilot clean) |
| Tiling (2026-10-23) | ~30 km tiles (100 × 100 cells at 300 m, 300 × 300 at HR), 2-cell halo. Verified bit-identical to untiled; only outlier flags depend on tile size |
| Figures (2026-10-21/23) | Agreed set (overviews, per-bin pages, time series, chl vs CDOM, HR vs 300 m, distributions, coverage, QI vs z, season climatology, season anomaly). Panel letters on every multi-panel figure, metric scale bar on every map, p maps green < 0.05 / very light red ≥ 0.05, colour per variable (chl greens, CDOM yellow-brown, turbidity brown) |
| Figure folders, movie (2026-10-26) | Subfolders per variable group (chl + a_ph443 / CDOM / turbidity + SPM / combined); date range on every bin label. Daily-step movie for 300 m chl with an 11-day window (`config.WINDOW_HALF = 5`, `config.WINDOW_VARS`), clipped to the season and the last 2026 date |
| Autocorrelation (2026-10-26) | Effective n = n²/ΣΣ r(|tᵢ−tⱼ|) from the empirical ACF of baseline daily anomalies (≤ 30 days), in all tests; uncorrected p kept as `*_uncorr`. Confirmed by user 2026-10-26; null simulation: 4.3 % false alarms vs 16.3 % uncorrected |
| FDR, effect size, islands (2026-10-26) | BH q = 0.10 over the whole domain per map (product-wide step after the tiles; `06 --significance-only` in batch mode), ≥ ×1.5, objects < 1 km² removed (8-connected) → `patch`. Explainer https://claude.ai/artifact/TVAKtvg5UKBssZkB2fQAQL |
| ACOLITE (2026-10-26) | Dropped from research, paper and guidelines. HR product (provider-made from S2/Landsat) stays |
| Main CDOM proxy (2026-10-26) | a_dg443 |
| Baseline 2025 (2026-10-26) | Kept; the paper states that September 2025 was also high |
| Manuscript | `reports/ms_draft.docx`; every Claude edit as Word tracked changes by "Claude"; >25 % of a paragraph changed → whole paragraph tracked; backup in `reports/versions/` before editing; validate with the docx skill |

## How to run (small domain = pilot; add `--domain full` for the full domain)
```powershell
.venv\Scripts\python scripts\03_download_cmems.py              # skips existing files; --dry-run for sizes
.venv\Scripts\python scripts\01_inventory.py --valid-fraction
.venv\Scripts\python scripts\05_preprocess.py                  # --workers N; or --tile k ... then --finalize
.venv\Scripts\python scripts\06_climatology_anomaly.py         # --workers N; or --tile k ... then --audit-only
.venv\Scripts\python scripts\07_figures_stage1.py              # --all-vars; --max-pixels N
```
Pilot steps 2–5 take about 2 minutes. On the external machine, follow `06_local_pilot.md` ("Running on the external machine").

## What exists
| File | What it does | Status |
|---|---|---|
| `src/greenpatch/config.py` | Domains, season, products, downloads, preprocessing settings (⚙), tiles, baselines, paths | In use |
| `src/greenpatch/runtime.py` | `--domain` option (sets `GREENPATCH_DOMAIN` before config loads) | In use |
| `src/greenpatch/tiles.py` | Tile grid, tile file names, `meta.json`, lazy combined reading (`open_product`) | In use |
| `src/greenpatch/bench.py` | Time, memory, output size, domain, cell-days per job → `results/tables/benchmarks.csv` | In use. Two rows from 2026-10-21 (cdom300 aph443 84 s, r412_443 4942 s) are inflated (machine asleep) |
| `src/greenpatch/geo.py` | Coastline (Natural Earth for maps, GSHHG for analysis), distance to coast, alongshore coordinate, cell area | In use |
| `src/greenpatch/plotting.py` | Metric scale bar | In use |
| `scripts/00_domain_map.py` | Domain map and pilot-box map → `results/maps/` | Done; point locations approximate |
| `scripts/01_inventory.py` + `inventory.py` | Inventory, checksums, missing dates, coverage figure | Run on pilot |
| `scripts/02_slim_storage.py` + `slim.py` | Slim, verified copies; optional deletion with log | Synthetic test only; not needed for the pilot |
| `scripts/03_download_cmems.py` | Download chl300, rrs300 (→ CDOM; bands kept), hr; per year; skips finished files | Run on pilot; full-domain dry run done |
| `scripts/04_compute_cdom.py` + `cdom.py` | QAA v6 CDOM rasters from reflectance on disk | Run via 03 on pilot |
| `scripts/05_preprocess.py` + `preprocess.py` | Steps 3, 6, 7, 8 per tile → `data/processed/<domain>/<product>/` | Run on pilot |
| `scripts/06_climatology_anomaly.py` + `climatology.py` | Steps 9–10 per tile: climatology, anomalies, A1 p, whole-season stats, daily sliding-window stats (`window_stats`, for the movie), audit | Run on pilot. Note: `--products X` rewrites `image_usage.csv` with product X only; run `--audit-only` afterwards |
| `scripts/07_figures_stage1.py` | All stage 1 figures and the chl movie (`--movie-only`, `--fps`; ffmpeg from `imageio_ffmpeg`); scales to any domain (lazy reads, display coarsening, per-tile streaming, pixel sampling) | Run on pilot 2026-10-26; tested on 9/56-tile mosaics (before the movie) |
| `scripts/08_q2_operational_model.py` | Q2: overlap check, coastal-strip and pilot comparison tables, record-cell maps, time series, saw-tooth (model products via `03 --model`, `05`/`06 --domain full --products medbgc medphy`) | Run 2026-10-30; single-threaded dask (HDF5 segfault with threads) |
| `scripts/tools/fetch_coastline.py` | GSHHG full resolution → `background_data/coastline/gshhg_f_L1_east_med.geojson` | Done |
| `scripts/tools/mark_all_as_inserted.py` | Marks new .docx content as tracked insertions by "Claude" | Available |
| `reports/ms_draft.docx` | Introduction + Methods 2.1–2.7 (tracked). 2026-10-26: 2.6 autocorrelation (+ Zwiers and von Storch 1995 [VERIFY]); later the same day: ACOLITE removed (2.1, Table 1 row and caption, two Vanhellemont references), domain (2.2), main proxy (2.3), new 2.6 paragraph on FDR / effect size / minimum area | Backup before last edit: `reports/versions/ms_draft_2026-10-30_1037.docx`. 2026-10-30 (later): 2.7 rewritten for the implemented Q2 analysis (model products, salinity, power limitation, record cells, saw-tooth method), status note; backup `ms_draft_2026-10-30_1646.docx`. 2026-10-30: title, Introduction questions (Q1–Q3), paragraph 7 river-forcing [VERIFY] answered, new 2.7 (operational model output) and 2.8 (model experiments, placeholder), Software → 2.9, Discussion placeholder (unarchived forecasts), references Feudale et al. 2025, Gualtieri et al. 2025 (QUIDs), Teruzzi et al. 2021 |

## Next steps, in order
0. **Q2:** user asks OGS the three questions in `todo.md`; Claude adds the model datasets to the downloader and runs Level A on an intermediate box (needs the box choice).
1. **User:** review the pilot figures and the ⚙ settings: outlier flag rate, coastal buffer, plausible ranges, effect size ×1.5.
2. Re-fetch the pilot reflectance bands (`--datasets rrs300`).
3. Discuss the 2025 result (possible trend; baseline choice).
4. Method A: FDR (autocorrelation done 2026-10-26); then Methods B and C. These need the user's confirmation of Part 2 of `05`.
5. Check the very high 2026 chl values for sediment or CDOM interference (compare HR turbidity, a_ph443).
6. Choose a useful larger domain (the user wants to test the 5 × 5 km box first), then prepare the external machine and run the full domain.
7. Manuscript: resolve the `[VERIFY]` marks; write Results once the tests are corrected.

## Open questions for the user
1. **Terminology:** "daily field" (recommended) or "daily product" for one day's map?
2. ~~Role of Sentinel-2/Landsat~~ — dropped altogether (2026-10-26); removed from manuscript 2.1 and Table 1.
3. **Cloud proposals:** rewrite as modelling-only requests, or for the full-domain stage 1 run (~150–200 GB, ~10–15 h on 16 cores)?
4. ~~Domain edges~~ — Rosetta to Rosh HaNikra (2026-10-26).
5. **Missing-data section** in `05`?
6. **Event facts** for the introduction: sources for the salinity drop, the alongshore extent and the name "green patch" (currently press-based, `[VERIFY]`).

## Things to verify before publication
- QAA v6 constants in `cdom.py` (pure-water absorption at OLCI wavelengths, coefficients), written from memory.
- `[VERIFY]` marks in `reports/ms_draft.docx`: press facts on the event, reference details (volumes, pages, author lists), QAA v6 citation, CMEMS product references, thresholds.
- Gaza–Israel coastal border point (~31.594°N) used for the pilot box and the time-series points.
- Approximate coordinates in `background_data/infrastructure/key_locations.csv`.

## External documents
- AWS Cloud Credits for Research draft (US$6,000): https://claude.ai/code/artifact/73c6a96e-2cc1-46df-967a-07ae5c4d6528
- Google Cloud research credits draft (US$5,000): https://claude.ai/code/artifact/99722a4a-8bba-4644-8935-376836274c40
- Both predate the two-product decision and the measured costs; they need revision (question 3).

## Environment notes
- Machine: Intel Core Ultra 7 155H (16 cores), 31 GB RAM, ~1.2 TB free on C:, Windows 11 + WSL2. The full domain does not fit in RAM untiled; the tiled code needs < 1–2 GB per worker.
- Python venv `.venv` (Python 3.13, `--system-site-packages`); copernicusmarine 2.5.0, dask, netCDF4, scipy 1.15, cartopy, shapely, pyproj (`env/requirements.txt`). Copernicus Marine login done; credentials in `C:\Users\Yair\.copernicusmarine\`.
- Copernicus Marine: no published quota for the toolbox; full-domain dry run = 195 GB of transfer (chl300 26, rrs300 43, HR 125).
- Git repository initialised; **no commits yet**.
- From Git Bash, pass Windows-style paths to Python (`cygpath -m`).
- Windows Python: always use `encoding="utf-8"` for `read_text`/`write_text`. Bash heredocs mangle `\n` escapes inside Python string literals: put multi-line edit scripts in a file (scratchpad) or use the Edit tool.
- NetCDF: `_FillValue = -999` (NaN fill breaks quantisation); text variables cannot be compressed.
- Word: the docx skill's LibreOffice helper does not run on Windows (`AF_UNIX`); render with Word via PowerShell COM (`ExportAsFixedFormat`, item 7 = with markup), then `pdftoppm`. Validate with the skill's `validate.py --original … --author Claude` using `PYTHONIOENCODING=utf-8`.
- Literature search: the Consensus tool returns 3 results per query on the free tier.
