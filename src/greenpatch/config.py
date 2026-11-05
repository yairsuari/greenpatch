"""Project-wide settings. Values follow guidelines/04_conventions.md (provisional where marked).

Domain profile (decision 2026-10-21, guidelines/06_local_pilot.md): the environment variable GREENPATCH_DOMAIN
selects "pilot" (default; 5 x 5 km box at the Gaza-Israel border, for local development) or "full" (the whole
analysis domain, on the server). Scripts accept --domain, which sets the variable before this module is imported.
Satellite folders, data/interim and results are separated per domain; benchmarks.csv is shared.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Analysis domains: lat0, lat1, lon0, lon1
DOMAINS = {
    # Full domain (user 2026-10-26): Rosetta Nile mouth (~31.46 N, 30.37 E) to Rosh HaNikra (~33.09 N, 35.10 E)
    # [VERIFY coordinates]; small margin on each side. Was 31.0-34.5 N, 31.0-35.5 E (Nile delta to southern Lebanon).
    "full": dict(lat0=31.0, lat1=33.15, lon0=30.0, lon1=35.2),
    # Pilot: 5.0 x 5.0 km centred on the coastal Gaza-Israel border (~31.594 N [VERIFY]); east edge just past
    # the coast (Natural Earth 10 m coast: 34.472 E at 31.57 N, 34.502 E at 31.615 N)
    "pilot": dict(lat0=31.570, lat1=31.615, lon0=34.452, lon1=34.505),
}
DOMAIN_NAME = os.environ.get("GREENPATCH_DOMAIN", "pilot")
if DOMAIN_NAME not in DOMAINS:
    raise ValueError(f"GREENPATCH_DOMAIN={DOMAIN_NAME!r}; expected one of {list(DOMAINS)}")
DOMAIN = DOMAINS[DOMAIN_NAME]

DATA_RAW = ROOT / "data" / "raw"
SAT_RAW = DATA_RAW / "satellite"
DATA_INTERIM = ROOT / "data" / "interim" / DOMAIN_NAME
RESULTS = ROOT / "results" / DOMAIN_NAME
BENCHMARKS = ROOT / "results" / "tables" / "benchmarks.csv"   # shared by all domains (column "domain")


def sat_folder(*parts) -> Path:
    """Raw satellite folder for the active domain: data/raw/satellite/<parts>/<domain>."""
    return SAT_RAW.joinpath(*parts, DOMAIN_NAME)


def describe() -> str:
    d = DOMAIN
    return (f"domain '{DOMAIN_NAME}': {d['lat0']}-{d['lat1']} N, {d['lon0']}-{d['lon1']} E "
            f"(set GREENPATCH_DOMAIN or --domain to change)")

# Sentinel-2 / Landsat coverage: Israeli and Gaza coast only (decision 2026-10-15)
L1_EXTENT = dict(lat0=31.2, lat1=33.15, lon0=34.2, lon1=35.15)

# Season (provisional) and years: baseline 2016-2025 + event year 2026
SEASON = dict(start=(7, 1), end=(10, 31))   # (month, day), inclusive
YEARS = list(range(2016, 2027))
EVENT_YEAR = 2026

# Selected products (guidelines/02_data_sources.md) and where their raw files live.
#   kind "netcdf":  CMEMS NetCDF files; dates read from the time coordinate
#   kind "l1":      Level-1 scenes (SAFE folders / zips / Landsat folders or tars); dates from file names
#   daily:          True if the product nominally has one value per day (missing days are then real gaps)
PRODUCTS = {
    "olci300": dict(
        label="CMEMS multi-year 300 m OLCI (009_143)",
        kind="netcdf",
        folder=sat_folder("chl", "olci300"),
        variables=["CHL", "chl"],
        daily=True,
    ),
    "hr": dict(
        label="CMEMS HR coastal (009_205)",
        kind="netcdf",
        folder=sat_folder("chl", "hr"),
        variables=["CHL", "chl"],
        daily=False,   # built from Sentinel-2/Landsat, so not every day has data
    ),
    # CDOM proxies computed from the 300 m reflectance right after download (the bands are then deleted)
    "cdom300": dict(
        label="CDOM proxies from 300 m OLCI reflectance (QAA v6)",
        kind="netcdf",
        folder=DATA_INTERIM / "cdom300",
        variables=["adg443"],
        daily=True,
    ),
    # Not used for the statistics (decision 2026-10-20: statistics on the two CMEMS products only).
    # Kept so the inventory still recognises any Level-1 scenes; role (if any) pending.
    "s2_landsat": dict(
        label="Sentinel-2 / Landsat 8-9 Level-1 (not used for statistics)",
        kind="l1",
        folder=sat_folder("l1"),
        variables=[],
        daily=False,
    ),
}

# Q2 (guidelines/07_q2_operational_model.md): Copernicus Marine Med operational model output, 1/24 deg (~4.2 km), surface.
# Run with --domain full (the whole domain is only ~52 x 125 model cells; the 5 x 5 km pilot is about one cell).
# medbgc / medphy: multi-year reanalysis (+ interim, to 2026-09-30), then the operational analysis for October 2026
# (see MODEL_DOWNLOADS for the offset caveat). medbgc_an / medphy_an: the operational analysis alone (saw-tooth test,
# overlap check).
MODEL_RAW = DATA_RAW / "model"
PRODUCTS.update({
    "medbgc": dict(label="Med BGC model chl: reanalysis 006_008 (+ analysis 006_014 after its end)", kind="netcdf",
                   folder=MODEL_RAW / "medbgc" / DOMAIN_NAME, variables=["chl"], daily=True),
    "medphy": dict(label="Med physics model salinity: reanalysis 006_004 (+ analysis 006_013 after its end)", kind="netcdf",
                   folder=MODEL_RAW / "medphy" / DOMAIN_NAME, variables=["so"], daily=True),
    # operational analysis alone (2024-2026 seasons) for the saw-tooth test and the interim-analysis overlap check
    "medbgc_an": dict(label="Med BGC analysis-forecast 006_014 (analysis days only)", kind="netcdf",
                      folder=MODEL_RAW / "medbgc_an" / DOMAIN_NAME, variables=["chl"], daily=True),
    "medphy_an": dict(label="Med physics analysis-forecast 006_013 (analysis days only)", kind="netcdf",
                      folder=MODEL_RAW / "medphy_an" / DOMAIN_NAME, variables=["so"], daily=True),
})
SATELLITE_PRODUCTS = ["olci300", "hr", "cdom300"]
MODEL_PRODUCTS = ["medbgc", "medphy"]
MODEL_DEPTH = (0.0, 1.5)   # m: first model level only (~1.0 m)
ANALYSIS_LAG_DAYS = 2      # anfc days later than today - 2 are hindcast/forecast, not analysis (QUID 006_014 Fig. 1)

# Copernicus Marine downloads (scripts/03_download_cmems.py). Dataset IDs and coverage verified in the
# catalogue on 2026-10-15 (copernicusmarine 2.5.0):
#   300 m OLCI plankton: 2016-04-26 .. ongoing, 0.0027 deg, CHL + QI_CHL (no ADG443 at 300 m)
#   300 m OLCI reflectance: same period, 14 bands (RRS400 .. RRS865)
#   1 km multi-sensor optics: 1997 .. ongoing, ADG443 (CDOM + detritus absorption)
#   HR coastal mosaic: 2020-01-01 .. ongoing, 0.00093 deg (~100 m), CHL + SPM + TUR
#   default=True: part of the agreed download (2026-10-20: chl300, rrs300, hr); False: optional
CMEMS = {
    "chl300": dict(dataset_id="cmems_obs-oc_med_bgc-plankton_my_l3-olci-300m_P1D",
                   variables=["CHL", "QI_CHL"], folder=PRODUCTS["olci300"]["folder"],
                   first_year=2016, default=True),
    "hr": dict(dataset_id="cmems_obs_oc_med_bgc_tur-spm-chl_nrt_l3-hr-mosaic_P1D-m",
               variables=["CHL", "SPM", "TUR"], folder=PRODUCTS["hr"]["folder"],
               first_year=2020, default=True),
    "rrs300": dict(dataset_id="cmems_obs-oc_med_bgc-reflectance_my_l3-olci-300m_P1D",
                   variables=["RRS412_5", "RRS442_5", "RRS490", "RRS560", "RRS665"],
                   folder=sat_folder("rrs", "olci300"), first_year=2016, default=True),
    "adg1km": dict(dataset_id="cmems_obs-oc_med_bgc-optics_my_l3-multi-1km_P1D",
                   variables=["ADG443", "QI_ADG443"], folder=sat_folder("cdom", "adg1km"),
                   first_year=2016, default=False),
    # Q2 model output (verified in the catalogue 2026-10-30). "depth": surface level; "after": only days after this
    # date (the reanalysis-interim ends 2026-09-30); "analysis_only": drop days after today - ANALYSIS_LAG_DAYS.
    "bgc_my": dict(dataset_id="cmems_mod_med_bgc-plankton_my_4.2km_P1D-m", variables=["chl"],
                   folder=PRODUCTS["medbgc"]["folder"], first_year=2016, default=False, depth=True),
    "bgc_an": dict(dataset_id="cmems_mod_med_bgc-pft_anfc_4.2km_P1D-m", variables=["chl"],
                   folder=PRODUCTS["medbgc"]["folder"], first_year=2026, default=False, depth=True,
                   after="2026-09-30", analysis_only=True),
    "phy_my": dict(dataset_id="cmems_mod_med_phy-sal_my_4.2km_P1D-m", variables=["so"],
                   folder=PRODUCTS["medphy"]["folder"], first_year=2016, default=False, depth=True),
    "phy_an": dict(dataset_id="cmems_mod_med_phy-sal_anfc_4.2km_P1D-m", variables=["so"],
                   folder=PRODUCTS["medphy"]["folder"], first_year=2026, default=False, depth=True,
                   after="2026-09-30", analysis_only=True),
    "bgc_an_all": dict(dataset_id="cmems_mod_med_bgc-pft_anfc_4.2km_P1D-m", variables=["chl"],
                       folder=PRODUCTS["medbgc_an"]["folder"], first_year=2024, default=False, depth=True,
                       analysis_only=True),
    "phy_an_all": dict(dataset_id="cmems_mod_med_phy-sal_anfc_4.2km_P1D-m", variables=["so"],
                       folder=PRODUCTS["medphy_an"]["folder"], first_year=2025, default=False, depth=True,
                       analysis_only=True),
}
# bgc_an / phy_an: October 2026 from the operational analysis, appended to the reanalysis-interim (user 2026-10-30:
# "keep October in"). Caveat: on overlapping days the analysis is offset from the reanalysis at the coast (salinity
# +0.07..+0.25 psu, chl -0.06..+0.13 log10; results/full/tables/q2_overlap_reanalysis_vs_analysis.csv), so October
# anomalies include this offset.
MODEL_DOWNLOADS = ["bgc_my", "bgc_an", "phy_my", "phy_an", "bgc_an_all", "phy_an_all"]

# CDOM rasters (src/greenpatch/cdom.py): written here, source reflectance bands deleted after verification
CDOM_OUT = PRODUCTS["cdom300"]["folder"]
DELETION_LOG = DATA_INTERIM / "deletion_log.csv"

# ACOLITE Level-2 water outputs (step 2) are written here
ACOLITE_OUT = DATA_INTERIM / "acolite"
SLIM_OUT = DATA_INTERIM / "slim"

# Storage reduction (scripts/02_slim_storage.py). Proposed settings, see decisions_log.md.
#   keep:      regular expression of variables to keep (coordinates are always kept)
#   bbox:      crop box; None = keep the file's full extent
#   coast_km:  set pixels farther than this from the mainland coast to NaN and crop to them; None = no coastal crop
#   sig_digits: lossy quantisation (significant digits) for float variables; None = lossless only
SLIM = {
    "olci300": dict(folder=PRODUCTS["olci300"]["folder"], kind="netcdf",
                    keep=r"^(CHL|chl|ADG443|adg_?443.*|.*[Ff]lag.*|QI.*)$",
                    bbox=DOMAIN, coast_km=None, sig_digits=4),
    "hr":      dict(folder=PRODUCTS["hr"]["folder"], kind="netcdf",
                    keep=r"^(CHL|chl|TUR|tur|SPM|spm|.*[Ff]lag.*|QI.*)$",
                    bbox=DOMAIN, coast_km=None, sig_digits=4),
    "acolite": dict(folder=ACOLITE_OUT, kind="acolite",
                    keep=r"^(chl_.*|t_nechad.*|spm_nechad.*|Rrs_(4[4-9]\d|5[5-6]\d|6[5-6]\d|70\d|86\d)|l2_flags)$",
                    bbox=L1_EXTENT, coast_km=35, sig_digits=4),
}

# ---------------------------------------------------------------- Stage 1 preprocessing (05, Part 1; confirmed 2026-10-21)
# All values marked ⚙ in 05_stage1_patch_identification.md are provisional and tuned on the pilot.
DATA_PROCESSED = ROOT / "data" / "processed" / DOMAIN_NAME
COASTLINE = ROOT / "background_data" / "coastline" / "gshhg_f_L1_east_med.geojson"   # scripts/tools/fetch_coastline.py

# Alongshore coordinate s (km): along the smoothed mainland coast, s = 0 at the Damietta mouth, increasing northward
ALONGSHORE = dict(origin=(31.845, 31.525),       # lon, lat (key_locations.csv, approximate)
                  start=(30.0, 31.35), end=(35.15, 33.25),   # coast segment: west of Rosetta .. just north of Rosh HaNikra
                  smooth_km=2.0,                 # ⚙ simplification tolerance of the coastline
                  closing_km=3.0)                # ⚙ closes lagoon outlets / inlets narrower than ~2 x 3 km

# Per product: input variables, output names, transform, plausible range (Step 3), coastal buffer in pixels.
#   log=True -> analysis variable is log10(value). Range applied to the untransformed value.
#   signal: +1 if a higher value means more of the signal (chl, absorption, turbidity), -1 if lower means more
#           (r412_443: lower ratio = more CDOM). Sets the direction of the one-sided test (Method A1).
#   main: variable that defines the land mask (cells never valid in the whole record) and the image-usage audit
#   keep: extra variables copied unchanged (diagnostics; QI_CHL = provider anomaly score, never used to mask)
PREPROC = {
    "olci300": dict(main="chl", buffer_px=1, keep=["QI_CHL"], vars={
        "CHL": dict(out="chl", log=True, vmin=0.01, vmax=100.0)}),
    "hr": dict(main="chl", buffer_px=1, keep=[], vars={
        "CHL": dict(out="chl", log=True, vmin=0.01, vmax=100.0),
        "TUR": dict(out="tur", log=True, vmin=0.01, vmax=1000.0),
        "SPM": dict(out="spm", log=True, vmin=0.01, vmax=1000.0)}),
    "cdom300": dict(main="adg443", buffer_px=1, keep=[], vars={
        "adg443": dict(out="adg443", log=True, vmin=1e-4, vmax=10.0),
        "aph443": dict(out="aph443", log=True, vmin=1e-4, vmax=10.0),
        "r412_443": dict(out="r412_443", log=False, vmin=0.05, vmax=5.0, signal=-1)}),
    # Q2 model output: no coastal buffer and no GSHHG land test (a 4 km coastal cell may have its centre on land in
    # GSHHG; the model's own land mask is used); effect size per variable (salinity: absolute psu, user 2026-10-30 ⚙)
    "medbgc": dict(main="chl", buffer_px=0, gshhg_land=False, keep=[], vars={
        "chl": dict(out="chl", log=True, vmin=1e-3, vmax=100.0)}),
    "medphy": dict(main="so", buffer_px=0, gshhg_land=False, keep=[], vars={
        "so": dict(out="so", log=False, vmin=20.0, vmax=42.0, signal=-1, effect_min=0.3)}),
}
OUTLIER = dict(window=3, n_sd=3.0, min_neighbours=4, min_valid_day=10)   # ⚙ 3x3 local-median flag (flag only)

# Spatial tiles (src/greenpatch/tiles.py): ~30 km per tile for both products; halo = buffer_px + window // 2 cells
TILE = {"olci300": (100, 100), "cdom300": (100, 100), "hr": (300, 300), "medbgc": (200, 200), "medphy": (200, 200)}   # (rows, columns)
TILE_HALO = 2

# Baseline years per product (Step 9; 2026 never in the baseline) and data-sufficiency rule ⚙
BASELINE = {"olci300": list(range(2016, 2026)), "cdom300": list(range(2016, 2026)), "hr": list(range(2020, 2026)),
            "medbgc": list(range(2016, 2026)), "medphy": list(range(2016, 2026))}
SUFFICIENCY = {"olci300": dict(min_n=20, min_years=6), "cdom300": dict(min_n=20, min_years=6),
               "hr": dict(min_n=20, min_years=4), "medbgc": dict(min_n=20, min_years=6),
               "medphy": dict(min_n=20, min_years=6)}
# Calendar bins (Step 8): "10d" = days 1-10, 11-20, 21-end; "month" = 30-day fallback; "auto" = 10d unless more than
# BIN_FALLBACK_FRAC of the sea pixel-bins fail SUFFICIENCY with 10-day bins (rule ⚙ in 05, Step 8), then "month".
BIN = {"olci300": "auto", "cdom300": "auto", "hr": "auto", "medbgc": "10d", "medphy": "10d"}
BIN_FALLBACK_FRAC = 1 / 3
# Daily sliding window (user 2026-10-26, for the chlorophyll movie): one centre per day, the event year's values from
# centre - WINDOW_HALF to centre + WINDOW_HALF days against the baseline years' values on the same calendar days.
# The window is clipped to the season and to the last date of the event year, so both sides cover the same days.
WINDOW_HALF = 5
WINDOW_VARS = [("olci300", "chl")]   # HR not used: 11-day HR baseline N (median 11) < 20, no p-value (user 2026-10-26)
EFFECT_MIN = 0.17609   # ⚙ log10(1.5): "elevated" = at least 50 % above the baseline median (Method A step 5)
# Per-variable override: PREPROC[...]["vars"][...]["effect_min"] (same units as the analysis variable; medphy so: 0.3 psu)

# Points for time-series figures: desalination plants inside the domain (key_locations.csv) plus these.
# Border point ~31.594 N, 34.486 E [VERIFY]; offshore points along the normal to the coast (azimuth ~305 deg).
TS_POINTS = {"Border, 1 km offshore": (34.477, 31.599), "Border, 3 km offshore": (34.460, 31.610)}
