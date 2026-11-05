# 06 — Local pilot before moving to a server

Status: **agreed** (2026-10-15; scope revised 2026-10-21). Run a small, complete version of the work on the local machine, measure what it costs, then move the same code to a cloud server.

**Revision 2026-10-21 (user):** develop and test locally on a **5 × 5 km pilot box at the Gaza–Israel border** with the **full time range** (all years, full season), instead of a single test day or the full domain. The full domain runs on the server with the same code.
- Pilot box: 31.570–31.615°N, 34.452–34.505°E, centred on the coastal border point (~31.594°N [VERIFY]). Map: `results/maps/pilot_box_map.png`. About 340 cells at 300 m (≈220 water) and ≈2,700 at HR (≈1,800 water). The 2026 patch was visible there (user).
- Why not one day: climatology, anomalies, significance, year comparison and change points all need the baseline years.
- Selection: `GREENPATCH_DOMAIN=pilot|full` or `--domain` on every script (default `pilot`; set `full` on the server). Raw satellite folders end in `/pilot` or `/full`; `data/interim/<domain>/` and `results/<domain>/` are separate; `results/tables/benchmarks.csv` is shared and has `domain` and `n_cell_days` columns, so cost per cell-day from the pilot scales to the full domain.
- Known limits (code test, not science): Method C has one 5 km alongshore bin and the 1–5 km band is truncated (water reaches only ~2–3 km offshore at the south edge, the coast is oblique); Method B objects are cut by the box edges.

## Why
- The cloud budgets (`AWS` and `Google Cloud` proposals) rested on two unmeasured numbers: ACOLITE time per scene (no longer relevant: ACOLITE dropped 2026-10-26) and ocean-model time per summer (assumed ~48 h). Measured numbers make the proposals credible.
- Open scientific settings (⚙ in `05_stage1_patch_identification.md`) are best settled on real data at small scale.
- Preliminary results strengthen the proposals.

## Local machine
Intel Core Ultra 7 155H (16 cores / 22 threads), 31 GB RAM, ~1.2 TB free disk, Windows 11 with WSL2 Ubuntu. The ocean model runs under WSL2 (Linux, like the cloud).

## Rules that make the code portable
1. **Linux from the start** for the model (WSL2 Ubuntu).
2. **All paths in `src/greenpatch/config.py`.** Moving to the cloud = changing paths to `s3://…` or `gs://…` (read through fsspec / xarray), no code changes.
3. **One command per unit of work** (one scene, one model season), safe to re-run (skips finished work). Locally a loop calls it; in the cloud each call is one batch job.
4. **Log every job:** wall time, peak memory, disk read/written, to `results/tables/benchmarks.csv`. These numbers feed the proposal budgets.
5. **Container last:** once the pilot works, package the code (and the model) in a Docker image (built in WSL2) for AWS Batch / Google Cloud Batch.

## Pilot scope
| Part | Local scope | Answers |
|---|---|---|
| CMEMS 300 m OLCI + HR | **Pilot box (5 × 5 km), all years** 2016–2026 (HR 2020–2026), July–October (MB, not GB) | Methods A–C end to end on real files; cost per cell-day. Full domain (~6–12 GB at 300 m) on the server |
| Lagrangian tracking | Back-tracking from the patch on CMEMS currents (OceanParcels) | Runs fully locally; first look at Nile vs Gaza origin |
| Ocean model | Coarse 2–3 km configuration, one-month run (CROCO under WSL2) | Model time per simulated day, to scale the cloud budget |

## Running on the external machine (2026-10-23)
Processing is tiled (`src/greenpatch/tiles.py`). Order of commands for the full domain (`--domain full`, or `GREENPATCH_DOMAIN=full`):
1. `03_download_cmems.py` (≈195 GB transfer; raw bands are kept, so disk use is larger than the 25–35 GB estimated with deletion).
2. `01_inventory.py --valid-fraction`.
3. `05_preprocess.py --workers N`, or on a batch system one job per tile: `05_preprocess.py --products <p> --tile <k>`, then `05_preprocess.py --products <p> --finalize`. Tile numbers are in `data/processed/<domain>/<product>/meta.json` (or `tiles.tile_list`).
4. `06_climatology_anomaly.py --workers N`, or per tile `--tile <k>` jobs followed by `--significance-only` (FDR, effect size, small objects over the whole domain) and `--audit-only`.
5. `07_figures_stage1.py` (to be adapted for the full domain, see `todo.md`).
Benchmarks per tile go to `results/tables/benchmarks.csv` with `n_cell_days`, for cost estimates.

## Steps
1. **CMEMS 300 m** (weeks 1–2): download script → inventory (`01_inventory.py`) → slim (`02_slim_storage.py`) → climatology, anomalies, methods A–C. Settle the ⚙ parameters.
3. **Modelling pilot** (weeks 3–4): OceanParcels tracking; CROCO coarse test run with timing.
4. **Update and submit proposals** with measured costs and preliminary results.

## Exit criteria (ready to move to a server)
- [ ] Methods A–C run end to end on the 300 m and HR products in the pilot box.
- [ ] `benchmarks.csv` has pilot rows with `n_cell_days`; full-domain cost estimated from them (and `--domain full --dry-run` sizes).
- [ ] Model time per simulated day measured.
- [ ] Every processing step is a re-runnable one-unit command with paths from config.
- [ ] Proposal budgets updated from `benchmarks.csv`.
