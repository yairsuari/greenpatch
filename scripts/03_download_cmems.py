"""Download Copernicus Marine satellite products for the analysis domain and season (step 1 of the local pilot).

One file per dataset and year, July-October only, cropped to the analysis domain and compressed:
    <folder from config.CMEMS>/<key>_<year>_<MMDD>-<MMDD>.nc   (folders end in /pilot or /full)
Reflectance files (rrs300) are turned into CDOM rasters immediately after download
(data/interim/<domain>/cdom300/cdom_cmems-olci_300m_<year>_<MMDD-MMDD>_qaa.nc) and the five bands are deleted
only with --delete-bands, after the raster is verified (logged in data/interim/<domain>/deletion_log.csv).
Default since 2026-10-23 (user): raw data are kept.
Re-running skips files that already exist (one unit of work = one dataset-year, safe to repeat).
Each download is logged in results/tables/benchmarks.csv (time, memory, size).

Before the first run, log in once (stores your credentials locally; Claude never sees the password):
    .venv/Scripts/copernicusmarine login

Usage (from the project root)
    .venv/Scripts/python scripts/03_download_cmems.py --dry-run          # what would be downloaded, with sizes
    .venv/Scripts/python scripts/03_download_cmems.py --domain full --dry-run   # full-domain sizes
    .venv/Scripts/python scripts/03_download_cmems.py                    # default datasets: chl300, hr
    .venv/Scripts/python scripts/03_download_cmems.py --datasets chl300 --years 2026
    .venv/Scripts/python scripts/03_download_cmems.py --datasets rrs300 adg1km   # optional datasets
    .venv/Scripts/python scripts/03_download_cmems.py --domain full --model      # Q2 model output (config.MODEL_DOWNLOADS)
Model datasets (Q2): surface level only (config.MODEL_DEPTH); "after" keeps only days after the reanalysis ends;
"analysis_only" drops days later than today - config.ANALYSIS_LAG_DAYS (those are hindcast or forecast, not analysis).
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import copernicusmarine as cm  # noqa: E402

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
from greenpatch import config  # noqa: E402
from greenpatch import cdom  # noqa: E402
from greenpatch.bench import Benchmark  # noqa: E402


def season_bounds(year):
    (m0, d0), (m1, d1) = config.SEASON["start"], config.SEASON["end"]
    return f"{year}-{m0:02d}-{d0:02d}T00:00:00", f"{year}-{m1:02d}-{d1:02d}T23:59:59", f"{m0:02d}{d0:02d}-{m1:02d}{d1:02d}"


def clip_dates(spec, start, end):
    """Apply the model-dataset date rules ("after", "analysis_only") to one season; None if nothing is left."""
    s0, s1 = dt.datetime.fromisoformat(start), dt.datetime.fromisoformat(end)
    if spec.get("after"):
        s0 = max(s0, dt.datetime.fromisoformat(spec["after"]) + dt.timedelta(days=1))
    if spec.get("analysis_only"):
        s1 = min(s1, dt.datetime.combine(dt.date.today() - dt.timedelta(days=config.ANALYSIS_LAG_DAYS), dt.time(23, 59, 59)))
    if s0 > s1:
        return None
    return s0.isoformat(), s1.isoformat(), f"{s0:%m%d}-{s1:%m%d}"


def cell_days(path):
    """Grid cells x days in a downloaded file (for scaling benchmarks to the full domain)."""
    import xarray as xr
    if not Path(path).exists():
        return None
    with xr.open_dataset(path) as ds:
        n = 1
        for dim, size in ds.sizes.items():
            if dim.lower() in ("time", "lat", "lon", "latitude", "longitude"):
                n *= size
    return n


def cdom_path(year, tag):
    return Path(config.CDOM_OUT) / f"cdom_cmems-olci_300m_{year}_{tag}_qaa.nc"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets", nargs="+", choices=list(config.CMEMS),
                    default=[k for k, v in config.CMEMS.items() if v["default"]])
    ap.add_argument("--years", nargs="+", type=int, default=config.YEARS)
    ap.add_argument("--dry-run", action="store_true", help="report sizes without downloading")
    ap.add_argument("--model", action="store_true", help="the Q2 model datasets (config.MODEL_DOWNLOADS)")
    ap.add_argument("--delete-bands", action="store_true",
                    help="delete the 300 m reflectance bands after the CDOM raster is verified (default: keep raw data)")
    add_domain_arg(ap)
    a = ap.parse_args()
    d = config.DOMAIN
    if a.model:
        a.datasets = config.MODEL_DOWNLOADS
    print(config.describe())

    # Check stored credentials first; otherwise the toolbox asks for a username interactively.
    if not cm.login(check_credentials_valid=True):
        print("No valid Copernicus Marine credentials found.\n"
              "Register (free): https://data.marine.copernicus.eu/register\n"
              "Then run once:   .venv/Scripts/copernicusmarine login")
        sys.exit(1)

    total_mb = 0.0
    for key in a.datasets:
        spec = config.CMEMS[key]
        folder = Path(spec["folder"])
        folder.mkdir(parents=True, exist_ok=True)
        for year in sorted(a.years):
            if year < spec["first_year"]:
                print(f"[{key} {year}] skipped: dataset starts in {spec['first_year']}")
                continue
            start, end, tag = season_bounds(year)
            clipped = clip_dates(spec, start, end)
            if clipped is None:
                print(f"[{key} {year}] skipped: no days left after the date rules")
                continue
            start, end, tag = clipped
            name = f"{key}_{year}_{tag}.nc"
            dst = folder / name
            # rrs300: with --delete-bands the CDOM raster stands in for the bands; otherwise the raw bands must exist too
            done = (cdom_path(year, tag) if a.delete_bands else dst) if key == "rrs300" else dst
            if done.exists() and not a.dry_run:
                print(f"[{key} {year}] exists, skipped: {done.name}")
                continue
            kwargs = dict(dataset_id=spec["dataset_id"], variables=spec["variables"],
                          minimum_longitude=d["lon0"], maximum_longitude=d["lon1"],
                          minimum_latitude=d["lat0"], maximum_latitude=d["lat1"],
                          start_datetime=start, end_datetime=end,
                          output_directory=str(folder), output_filename=name,
                          netcdf_compression_level=4, skip_existing=True, disable_progress_bar=True)
            if spec.get("depth"):
                kwargs.update(minimum_depth=config.MODEL_DEPTH[0], maximum_depth=config.MODEL_DEPTH[1])
            try:
                if a.dry_run:
                    resp = cm.subset(dry_run=True, **kwargs)
                    mb = float(getattr(resp, "file_size", 0) or 0)
                    total_mb += mb
                    print(f"[{key} {year}] would download ~{mb:,.0f} MB (uncompressed estimate) -> {name}")
                else:
                    with Benchmark("download_cmems", f"{key}_{year}", out_path=dst, note=spec["dataset_id"]) as b:
                        cm.subset(**kwargs)
                        b.n_cell_days = cell_days(dst)
                    mb = dst.stat().st_size / 1e6 if dst.exists() else 0
                    total_mb += mb
                    print(f"[{key} {year}] downloaded {mb:,.0f} MB -> {name}")
                    if key == "rrs300" and dst.exists():
                        res = cdom.run(dst, config.CDOM_OUT, delete=a.delete_bands)
                        print(f"[{key} {year}] CDOM: {res['message']} -> {res['dst'].name}; "
                              f"bands {'deleted' if res['deleted'] else 'KEPT'}")
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).splitlines()[0][:200]
                print(f"[{key} {year}] FAILED: {type(exc).__name__}: {msg}")
                if "credential" in msg.lower() or "login" in msg.lower() or "authenticat" in msg.lower():
                    print("  -> run once: .venv/Scripts/copernicusmarine login")
                    return
    print(f"\nTotal: {total_mb / 1e3:,.2f} GB {'(estimate)' if a.dry_run else 'downloaded'}")
    if not a.dry_run:
        print("Next: .venv/Scripts/python scripts/01_inventory.py --valid-fraction")


if __name__ == "__main__":
    main()
