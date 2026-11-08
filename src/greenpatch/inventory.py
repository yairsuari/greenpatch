"""Step 1 of guidelines/05_stage1_patch_identification.md: inventory and integrity.

For each product folder:
  * list every file, with size, modification time and SHA-256 checksum;
  * read acquisition dates and sensor (from the NetCDF time axis, or the date in the file name);
  * check integrity (opens, expected variable, overlaps the domain);
  * optionally compute the fraction of valid (non-NaN) pixels in the domain per date;
  * build an availability table (one row per product x date x sensor x tile)
    and list the missing dates per season.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ file-name patterns
DATE_RE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")

NC_SUFFIXES = {".nc", ".nc4", ".netcdf"}
SKIP_NAMES = {".gitkeep", "desktop.ini", "Thumbs.db"}


@dataclass
class FileRecord:
    product: str
    path: str
    kind: str                      # netcdf | other
    size_bytes: int
    modified_utc: str
    sha256: str = ""
    sensor: str = ""
    tile: str = ""
    first_date: str = ""
    last_date: str = ""
    n_dates: int = 0
    status: str = "ok"             # ok | warning | error
    message: str = ""
    dates: list = field(default_factory=list, repr=False)          # [(date, time_utc, valid_fraction)]


# ------------------------------------------------------------------ helpers
def _size(path: Path) -> int:
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return path.stat().st_size


def _mtime(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-256 of a file ("" for a folder)."""
    if path.is_dir():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def discover(folder: Path) -> list[Path]:
    """Files to inventory; sub-folders are searched."""
    items = []
    if not folder.exists():
        return items
    for p in sorted(folder.iterdir()):
        if p.name in SKIP_NAMES or p.name.startswith("."):
            continue
        if p.is_dir():
            items.extend(discover(p))
        else:
            items.append(p)
    return items


# ------------------------------------------------------------------ per-kind checks
def check_netcdf(rec: FileRecord, path: Path, variables: list[str], domain: dict, valid_fraction: bool):
    import xarray as xr
    try:
        ds = xr.open_dataset(path)
    except Exception as exc:  # noqa: BLE001
        rec.status = "error"
        rec.message = ("cannot open: not a valid NetCDF/HDF5 file (corrupt or incomplete download?)"
                       if "did not find a match" in str(exc) else f"cannot open: {type(exc).__name__}: {exc}"[:200])
        return
    with ds:
        notes = []
        var = next((v for v in variables if v in ds.data_vars), None)
        if var is None:
            rec.status = "error"
            notes.append(f"none of {variables} found; variables = {list(ds.data_vars)[:8]}")
        rec.sensor = str(ds.attrs.get("sensor", ds.attrs.get("platform", "")))[:60]

        tname = next((c for c in ("time", "TIME", "t") if c in ds.coords or c in ds.dims), None)
        if tname is not None and np.issubdtype(ds[tname].dtype, np.datetime64):
            times = pd.to_datetime(ds[tname].values)
        else:
            m = DATE_RE.search(path.name)
            times = pd.to_datetime([f"{m.group(1)}-{m.group(2)}-{m.group(3)}"]) if m else pd.DatetimeIndex([])
            info = "date from file name" if m else ""
            if not m:
                rec.status = "error"
                notes.append("no time axis and no date in file name")

        latn = next((c for c in ("lat", "latitude", "LAT") if c in ds.coords), None)
        lonn = next((c for c in ("lon", "longitude", "LON") if c in ds.coords), None)
        sub = None
        if latn and lonn:
            la, lo = ds[latn].values, ds[lonn].values
            overlap = (la.max() >= domain["lat0"] and la.min() <= domain["lat1"]
                       and lo.max() >= domain["lon0"] and lo.min() <= domain["lon1"])
            if not overlap:
                rec.status = "error"
                notes.append("does not overlap the analysis domain")
            elif var is not None:
                lat_ok = (ds[latn] >= domain["lat0"]) & (ds[latn] <= domain["lat1"])
                lon_ok = (ds[lonn] >= domain["lon0"]) & (ds[lonn] <= domain["lon1"])
                sub = ds[var].where(lat_ok & lon_ok, drop=True)
        else:
            if rec.status == "ok":
                rec.status = "warning"
            notes.append("no lat/lon coordinates found")

        fracs = [np.nan] * len(times)
        if valid_fraction and sub is not None and sub.size:
            if tname in sub.dims:
                fr = sub.notnull().mean(dim=[d for d in sub.dims if d != tname]).values
                fracs = [float(x) for x in np.atleast_1d(fr)]
            else:
                fracs = [float(sub.notnull().mean())]

        rec.dates = [(t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S"), f) for t, f in zip(times, fracs)]
        if rec.status == "ok" and notes:
            rec.status = "warning"
        if tname is None or not np.issubdtype(ds[tname].dtype, np.datetime64):
            notes.append(info) if info else None
        rec.message = "; ".join(n for n in notes if n)


def classify(path: Path) -> str:
    return "netcdf" if path.suffix.lower() in NC_SUFFIXES else "other"


# ------------------------------------------------------------------ main entry points
def inventory_product(name: str, spec: dict, domain: dict, *, checksums: bool = True,
                      valid_fraction: bool = False, cache: pd.DataFrame | None = None,
                      folder: Path | None = None, rel_to: Path | None = None) -> list[FileRecord]:
    folder = Path(folder or spec["folder"])
    cached = {}
    if cache is not None and len(cache):
        cached = {(r.path, r.size_bytes, r.modified_utc): r.sha256 for r in cache.itertuples()}
    records = []
    for path in discover(folder):
        kind = classify(path)
        shown = str(path.relative_to(rel_to)) if rel_to and path.is_relative_to(rel_to) else str(path)
        rec = FileRecord(name, shown.replace("\\", "/"), kind, _size(path), _mtime(path))
        if rec.size_bytes == 0:
            rec.status, rec.message = "error", "empty file"
        elif kind == "netcdf":
            check_netcdf(rec, path, spec["variables"], domain, valid_fraction)
        else:
            rec.status, rec.message = "warning", "unrecognised file type; not inventoried"
        if checksums and rec.size_bytes:
            key = (rec.path, rec.size_bytes, rec.modified_utc)
            rec.sha256 = cached.get(key) or sha256(path)
        if rec.dates:
            ds_ = sorted(d[0] for d in rec.dates)
            rec.first_date, rec.last_date, rec.n_dates = ds_[0], ds_[-1], len(set(ds_))
        records.append(rec)
    return records


def files_table(records: list[FileRecord]) -> pd.DataFrame:
    rows = [{k: v for k, v in asdict(r).items() if k != "dates"} for r in records]
    return pd.DataFrame(rows, columns=[f for f in FileRecord.__dataclass_fields__ if f != "dates"])


def availability_table(records: list[FileRecord]) -> pd.DataFrame:
    rows = [dict(product=r.product, date=d, time_utc=t, sensor=r.sensor, tile=r.tile,
                 valid_fraction=f, source=r.path)
            for r in records if r.status != "error" for d, t, f in r.dates]
    cols = ["product", "date", "time_utc", "sensor", "tile", "valid_fraction", "source"]
    av = pd.DataFrame(rows, columns=cols)
    if len(av):
        dup = av.duplicated(["product", "date", "time_utc", "sensor", "tile"], keep=False)
        av["duplicate"] = dup
    else:
        av["duplicate"] = pd.Series(dtype=bool)
    return av


def season_dates(year: int, season: dict) -> pd.DatetimeIndex:
    (m0, d0), (m1, d1) = season["start"], season["end"]
    return pd.date_range(dt.date(year, m0, d0), dt.date(year, m1, d1), freq="D")


def coverage(av: pd.DataFrame, products: dict, years: list[int], season: dict):
    """Per product and year: days with data, coverage, longest gap. Also the list of missing dates."""
    summary, missing = [], []
    for name, spec in products.items():
        have = set(av.loc[av["product"] == name, "date"]) if len(av) else set()
        for y in years:
            days = season_dates(y, season)
            flags = np.array([d.strftime("%Y-%m-%d") in have for d in days])
            gap, longest = 0, 0
            for f in flags:
                gap = 0 if f else gap + 1
                longest = max(longest, gap)
            n_scenes = int(((av["product"] == name) & av["date"].str.startswith(str(y))).sum()) if len(av) else 0
            summary.append(dict(product=name, year=y, season_days=len(days), days_with_data=int(flags.sum()),
                                coverage_pct=round(100 * flags.mean(), 1),
                                longest_gap_days=longest if flags.any() else np.nan,
                                n_scenes_or_steps=n_scenes))
            for d, f in zip(days, flags):
                if not f:
                    missing.append(dict(product=name, year=y, date=d.strftime("%Y-%m-%d"),
                                        nominally_daily=spec["daily"]))
    return pd.DataFrame(summary), pd.DataFrame(missing, columns=["product", "year", "date", "nominally_daily"])
