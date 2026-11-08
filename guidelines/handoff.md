# Session handoff — Green Patch 2026

Last updated: 2026-11-08. This is the **final handout from the first laptop** (sessions 13 Oct – 8 Nov 2026). From now on
work continues on the **new machine**, reached from a second laptop through VS Code Remote-SSH (`09_remote_setup.md`).
Read this first in a new session, then the files listed in `CLAUDE.md`. Decisions with dates and reasons are in
`decisions_log.md`; open tasks, ordered by phase, in `todo.md`. This file is the summary, not the record.

## 0. First session on the new machine: do this in order
1. **Storage first.** The user's home disk on the machine is very limited.
   - Find a large project or scratch disk (≥ 300 GB) and check whether it is purged or backed up.
   - Keep the git clone in home. Symlink `data/` and `model/runs/` to the big disk, and put the pip and tmp caches there too, **before any download** (`09_remote_setup.md`, step 4).
   - All code paths go through `config.ROOT / "data"`, so no code change is needed. If symlinks are not allowed, add a `GREENPATCH_DATA` variable to `config.py`.
2. **Environment.**
   - `git clone https://github.com/yairsuari/greenpatch.git greenpatch2026`
   - venv with `--system-site-packages`. Check what is importable before installing anything from `env/requirements.txt`.
   - `copernicusmarine login`, tmux, and modules if it is a cluster (`09` steps 4–5).
   - Linux paths: `.venv/bin/python`, not `.venv\Scripts\python`.
3. **Implement the settings of 2026-11-05** (user 2026-11-08: on the machine, for the full domain directly).
   - SST L3S `SST_MED_SST_L3S_NRT_OBSERVATIONS_010_012_b`: add it to `config.CMEMS`, the downloader and `PREPROC` (no log). Add a **two-sided** test option to the anomaly step and to `significance`.
   - HR coastal buffer: 3 px.
   - a_dg443 plausible maximum: 2 m⁻¹.
   - Whole-season autocorrelation max lag: 60 days.
   - Check the code on the pilot box first (re-download takes minutes; `--domain pilot`), then the full domain.
4. **Download everything on the machine** (user: nothing is copied from the laptop).
   - Full-domain satellite data: dry run ~139 GB (chl300 18, rrs300 31, HR 90).
   - SST.
   - Q2 model output: `config.MODEL_DOWNLOADS`, ~50 MB.
   - Then the inventory (`01`).
5. **Full-domain Q1**: steps 05 and 06 per tile (`--workers` or batch jobs), then `06 --significance-only` (product-wide FDR), then the figures, movie, onset map and co-location table. Then the sensitivity runs (effect ×1.25 and ×2; minimum area 0.5 and 2 km²).
6. **Methods B and C**, reduced form (user 2026-11-08; section 3 below). New script, then a year-comparison table.
7. **Q2 re-scoring** against the full-domain patch. Level A is **descriptive only**: ranks, record cells, and ratios against both satellite products. Adapt `08_q2_operational_model.py` and manuscript 2.7 (tracked).
8. **Q3**: build OGSTM-BFM (ModelBuild) and 3DVarBio. Keep the regional NEMO v4.2 nest as the fallback (`03_models.md`).

## 1. The paper (scope settled 2026-11-05)
**One paper, three questions:**
- **Q1 — the observed patch:** satellite data; the current focus.
- **Q2 — the operational Copernicus Med biogeochemical system** (`07_q2_operational_model.md`):
  - Issued forecasts are not archived (OGS, 2026-10-29), so Q2 is an upper-bound test on the analysis.
  - Plus the saw-tooth test, and the inputs and physics.
- **Q3 — simplified model runs with the operational chain** (`03_models.md`).

**Claim:** the patch was there, and it was **not forecastable with present operational tools**.

**Leading hypothesis:** a missing land input of fresh water and nutrients. Locating it is a **separate continuation
study** (`08_next_study_draft.md`).

## 2. Results so far
**Q1, pilot 5 × 5 km box at the Gaza–Israel border:**
- 300 m chl in 2026 is significant after the autocorrelation correction, FDR (q = 0.10), effect size ×1.5 and the 1 km² minimum area, in 145–147 of 147 pixels from 1 Sep to 10 Oct.
  - The 21–31 Aug bin is elevated but not significant, so onset is "late August – early September".
  - The daily onset map gives 27 Aug – 5 Sep, with offshore pixels first.
- Box-median chl is about 25 mg m⁻³ in early September (2016–2024: about 1–5).
- **Magnitude depends on the product:**
  - 300 m ≈ ×3.5 above HR on the same days in Sep–Oct 2026. The two agree in 2020–25.
  - Likely cause: the Case-2 AD4 branch of the 300 m algorithm; 2026 Rrs490/560 = 0.49 vs 1.08 in the baseline.
  - No saturation.
  - Reported as a range; the 300 m product carries the formal test. The Discussion paragraph is in the manuscript.
- Co-location: a_ph443 ×3.5–5 and significant in 95–99 % of the patch. a_dg443 and turbidity are not significant. The signature is **phytoplankton, not a CDOM-rich plume**.
- September 2025 (and 2021, 2023) was also high, possibly a trend. 2025 stays in the baseline, and the paper says so.

**Q2, full domain, operational model (2026-10-30):**
- Model chl ranks 2026 highest of 11 years along the Israel/Gaza coast in all September bins.
- But the 2026 excess is only ×2 (satellite ×7–9), at ~0.1 mg m⁻³.
- No power for a formal test (n_eff ≈ 1–1.4).
- Weekly saw-tooth: Monday jumps, then decay ×0.56–0.67 over 5 days.
- No model freshening.

**Nile in the operational system** (`07` section 2b):
- Monthly **climatology** (Said et al. 2011), identical every year, shared by the physics and the biogeochemistry.
- Nutrient load = discharge × fixed reference concentrations per land macro-region.
- Apparently one input point.
- No Gaza, Israeli streams, wastewater or lagoon outflows.
- Satellite chl assimilation corrects phytoplankton only (not nutrients).

## 3. Decisions to keep in mind (full list: `decisions_log.md`)
| Topic | Decision |
|---|---|
| Language | English in code and documents, even when the user writes in Hebrew (the user sometimes types English with a Hebrew keyboard layout: decode it) |
| Data | Copernicus Marine only: 300 m OLCI multi-year `009_143` (2016–), HR coastal `009_205` (~100 m, 2020–), 300 m reflectance → CDOM proxies (QAA v6; main proxy a_dg443), SST L3S `010_012_b` (to add). ACOLITE/Sentinel-2–Landsat own processing dropped; its code removed 2026-11-08 |
| Domains | `pilot` (5 × 5 km, default) and `full` = Rosetta to Rosh HaNikra, 31.0–33.15°N, 30.0–35.2°E; `--domain` or `GREENPATCH_DOMAIN`; separate folders per domain |
| Season / baseline | 1 Jul–31 Oct; baseline 2016–2025 (HR 2020–2025), leave-one-year-out; formal claim on the 300 m product; 2026 data = whatever exists on the run day |
| Method A | 10-day bins (HR → monthly fallback); one-sided Mann–Whitney per pixel and bin (SST two-sided); n_eff from the empirical ACF (max lag 30, whole-season 60); BH FDR q = 0.10 over the whole domain per map; effect ≥ ×1.5; objects ≥ 1 km² → `patch`; onset = first window centre starting ≥ 3 consecutive patch days |
| Method B (2026-11-08) | Mask = pixel > own baseline P90 (P85/P95 sensitivity; absolute 1 mg m⁻³ in the supplement); per-year object metrics (maximum area, area-days, alongshore extent, offshore reach, duration); 2026 ranked against 2016–2025. **No tracking** |
| Method C (2026-11-08) | Hovmöller per year; arrival at each desalination intake and spreading speed (Theil-Sen) from the onset map; integrated index per year (km·days). **No change points** |
| Year comparison | Headline = B area-days **and** C index together; state that 2021/2023/2025 were also high |
| Magnitude | Range across 300 m and HR; 300 m treated as an upper estimate |
| Preprocessing | log10 for chl/absorption/turbidity/SPM; outlier check flags only; coastal buffer 1 px (300 m) / 3 px (HR, to implement); native grids; GSHHG coastline |
| Q2 | Level A descriptive only; saw-tooth test; October 2026 kept (analysis appended, with an offset caveat) |
| Q3 | OGSTM-BFM offline + 3DVarBio, forced by OGS's offline physics (ask) or by our own nested NEMO v4.2; runs S0, S1 (2–3 source strengths), N1 (chl), N2 (chl + nutrients above threshold), N3 (chl + source); 1 Aug – 31 Oct 2026; S0/N1 must reproduce the saw-tooth first. Forecast-mode runs (a)/(b) deferred |
| Not done | Forecast archiving (user: blooms only in summer; revisit before ~June 2027 if wanted); satellite salinity; CDOM–salinity proxy (next study) |
| Raw data | Never edited. Satellite files may be deleted only after a verified slim copy (`02_slim_storage.py --delete-originals`, checksum log) |
| Manuscript | `reports/ms_draft.docx`; every Claude edit is a Word tracked change by "Claude"; > 25 % of a paragraph changed → whole paragraph tracked; backup in `reports/versions/` first; validate with the docx skill |
| Git | Private repository `yairsuari/greenpatch`, branch `main`. The machine's clone + GitHub are the only working copy; `data/`, `model/runs/`, `.venv/` are not tracked |

## 4. Waiting on the user
- **Email OGS** (`todo.md`, User tasks):
  - (i) was the 2025 QUID setup in operation in Aug–Oct 2026;
  - (ii) are the pre-assimilation misfits for 2026 archived;
  - (iii) confirm the Monday jump;
  - (iv) the analysis–reanalysis coastal offset;
  - (v) how to cite their reply on the missing forecast archive;
  - (vi) the Nile forcing: monthly discharge, grid cell(s), N/P/Si/ALK/DIC concentrations;
  - plus, for Q3: the offline physics forcings (including `votkeavt`, wind, shortwave) and a full BFM restart, 1 Aug – 31 Oct 2026.
- **Email IOLR and the Water Authority:** in-situ chl, salinity and nutrients for Aug–Oct 2026. This is the main weakness of Q1 and the core of the next study.
- Sources for the event facts: the salinity drop, the alongshore extent, the name "green patch".
- Review `08_next_study_draft.md`.
- Open questions:
  - "daily field" vs "daily product" as the term;
  - the purpose of the cloud-credit proposals (drafts: AWS https://claude.ai/code/artifact/73c6a96e-2cc1-46df-967a-07ae5c4d6528, Google https://claude.ai/code/artifact/99722a4a-8bba-4644-8935-376836274c40; both outdated);
  - a missing-data section in `05`.

## 5. Writing (after the full-domain results)
**Manuscript state:**
- Introduction and Methods 2.1–2.9 exist.
- All tracked changes up to 2026-10-30 were accepted at the user's request.
- Later edits are tracked: the 2026-11-05 Discussion paragraph "Magnitude of the patch", with 6 references.
- Last backup: `reports/versions/ms_draft_2026-11-05_1126.docx`.
- No Results yet.

**To do:**
- Introduction questions and title for the 2026-11-05 scope.
- Guidelines `00`, `01`, `03` likewise.
- Section 2.3: the bands are now kept.
- Section 2.7: Q2 descriptive.
- A Discussion paragraph on the unarchived forecasts.
- Results text: onset "late August – early September"; September 2025 also high.
- Resolve the `[VERIFY]` marks.
- Find the AD4 calibration range.

## 6. How to run (pilot by default; add `--domain full`)
```bash
.venv/bin/python scripts/03_download_cmems.py            # --dry-run for sizes; --datasets ...; --model for Q2
.venv/bin/python scripts/01_inventory.py --valid-fraction
.venv/bin/python scripts/05_preprocess.py                # --workers N, or --tile k ... then --finalize
.venv/bin/python scripts/06_climatology_anomaly.py       # --workers N, or --tile k ...; then --significance-only (FDR), --audit-only
.venv/bin/python scripts/07_figures_stage1.py            # --all-vars; --movie-only
.venv/bin/python scripts/08_q2_operational_model.py      # Q2, --domain full; single-threaded dask (HDF5 segfault with threads)
```
Full-domain order and batch jobs: `06_local_pilot.md`, "Running on the external machine". Pilot steps 05–07 take
minutes.

## 7. Code map
| File | Role |
|---|---|
| `src/greenpatch/config.py` | Domains, season, products, downloads (`CMEMS`, `MODEL_DOWNLOADS`), preprocessing (`PREPROC`, ⚙), tiles, paths |
| `runtime.py`, `tiles.py`, `bench.py` | `--domain`; tile grid and lazy reading; benchmarks → `results/tables/benchmarks.csv` |
| `geo.py`, `plotting.py` | Coastline, distance to coast, alongshore coordinate s, cell area; scale bar |
| `inventory.py` (+ `scripts/01_inventory.py`) | Inventory, checksums, coverage (NetCDF only since 2026-11-08) |
| `slim.py` (+ `scripts/02_slim_storage.py`) | Slim verified copies; optional deletion with checksum log |
| `cdom.py` (+ `scripts/04_compute_cdom.py`) | QAA v6 CDOM proxies (constants to verify) |
| `preprocess.py`, `climatology.py`, `significance.py` | Steps 3–10; ACF/n_eff; FDR, effect, cleaning, `patch`, `onset` |
| `scripts/03_download_cmems.py` | Satellite and model downloads; skips finished files |
| `scripts/07_figures_stage1.py` | All Q1 figures, movie, onset map, co-location table |
| `scripts/08_q2_operational_model.py` | Q2 tables, record cells, saw-tooth |
| `scripts/tools/check_chl_ceiling.py` | Magnitude / ceiling diagnostics (300 m vs HR, AD4) |
| `reports/settings_review_2026-11-05.md` | Baked-in vs post-hoc settings (answered) |

## 8. Things to verify before publication
- QAA v6 constants in `cdom.py` (written from memory).
- Coordinates: the Gaza–Israel border point (~31.594°N), `background_data/infrastructure/key_locations.csv` (approximate; also needed for the intake arrival dates in Method C), domain edges.
- `[VERIFY]` marks in the manuscript and guidelines (references, product IDs, event facts).

## 9. Environment notes
- **New machine:** details are unknown until the first login (OS, scheduler, disks). Record them here.
- **First laptop** (no longer the working copy):
  - Intel Core Ultra 7 155H (16 cores), 31 GB RAM, Windows 11.
  - Its `data/` holds the pilot data (not in git).
- `copernicusmarine` 2.5.0. No published quota; the full-domain transfer is ~195 GB.
- The tiled code needs < 1–2 GB RAM per worker.
- NetCDF: `_FillValue = -999` (a NaN fill breaks quantisation).
- On Windows only:
  - use `encoding="utf-8"` for text I/O;
  - render Word through PowerShell COM;
  - the docx skill's LibreOffice helper fails (`AF_UNIX`).
- On Linux, LibreOffice should work for rendering the manuscript [VERIFY on the day].
- Validate the manuscript with the docx skill's `validate.py --original … --author Claude` (`PYTHONIOENCODING=utf-8`).
- Bash heredocs mangle `\n` inside Python string literals. Put edit scripts in files.
