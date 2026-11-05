# 04 — Conventions

## Space and time
- **CRS:** WGS84 geographic (EPSG:4326) for storage. Area and distance calculations in UTM zone 36N (EPSG:32636).
- **Analysis domain (user 2026-10-26):** Rosetta Nile mouth to Rosh HaNikra: 31.0–33.15°N, 30.0–35.2°E (`config.DOMAINS['full']`; coordinates [VERIFY]). Was 31.0–34.5°N, 31.0–35.5°E. Pilot box unchanged.
- **Domain profiles** (`config.DOMAINS`, decision 2026-10-21): `full` (above; server) and `pilot` (31.570–31.615°N, 34.452–34.505°E, 5 × 5 km at the Gaza–Israel border; local development). Selected by `GREENPATCH_DOMAIN` or `--domain` (default `pilot`). Paths per domain: `data/raw/satellite/<…>/<domain>/`, `data/interim/<domain>/`, `results/<domain>/`; `results/tables/benchmarks.csv` and `results/maps/` are shared.
- **Time:** UTC everywhere. Dates as ISO 8601 (`YYYY-MM-DD`).
- **Analysis window:** 1 July – 31 October each year (provisional).
- **Baseline:** 2016–2025 main; 2003–2025 robustness (proposed).

## Units
- Chlorophyll: mg m⁻³ (analysed as log10).
- Salinity: PSU (practical salinity). Temperature: °C. Distance: km. Area: km².

## Files
- **Raw-data folders (proposed):** `data/raw/satellite/chl/olci300/` (CMEMS 300 m NetCDF), `data/raw/satellite/chl/hr/` (CMEMS HR NetCDF). Defined in `src/greenpatch/config.py`.
- Formats: NetCDF (CF conventions) for gridded data; CSV or Parquet for tables; GeoJSON for vector data.
- Raw file names keep the provider's naming. Derived files: `<variable>_<source>_<resolution>_<period>_<step>.nc`, e.g. `chl_cmems-olci_300m_2016-2026_anomaly.nc`.
- Scripts: numbered by pipeline order, e.g. `scripts/01_download_chl.py`.
- Figures: `results/figures/<method>_<variable>_<description>.png` (plus PDF/SVG for publication).

## Storage reduction (`scripts/02_slim_storage.py`, proposed)
- Slim copies go to `data/interim/slim/<product>/`: only the variables listed in `config.SLIM`, cropped to the analysis domain, compressed (zlib + shuffle) and quantised to 4 significant digits (max error ≈ 0.05 %, far below retrieval uncertainty). Missing values use fill value −999 (NaN fill breaks quantisation).
- Each slim copy is verified (variables, time steps, valid-pixel pattern, values within 0.1 %) before any deletion. Existing copies are re-verified before deleting their source.
- Originals are deleted only with `--delete-originals`; every deletion is logged with its checksum in `data/interim/deletion_log.csv` so the file can be re-downloaded.

## Code
- Python, managed in `.venv` (created with `--system-site-packages`).
- Reusable functions in `src/greenpatch/`; notebooks only for exploration.
- Credentials (CMEMS, Earthdata) never in code or git; use environment variables or the provider's credential files.
