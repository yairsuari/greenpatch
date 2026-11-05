"""Storage reduction: write slim copies of NetCDF files and (optionally) delete originals.

A slim copy keeps only the listed variables, is cropped to a box and optionally to a coastal strip,
and is compressed (zlib + shuffle, optional lossy quantisation to N significant digits).
Every slim copy is verified against its source before the source may be deleted.
Deletions are appended to a log with the original's checksum so the file can be re-downloaded.
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
from pathlib import Path

import numpy as np
import xarray as xr

from .geo import coastal_mask
from .inventory import LS_RE, S2_RE, sha256

ACOLITE_RE = [
    re.compile(r"^(S2[ABCD])_MSI_(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})(?:_(T\d{2}[A-Z]{3}))?_L2W"),
    re.compile(r"^(L[89])_OLI_(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})(?:_(\d{6}))?_L2W"),
]


# ------------------------------------------------------------------ helpers
def _coords(ds):
    lat = next((c for c in ("lat", "latitude", "LAT") if c in ds.variables), None)
    lon = next((c for c in ("lon", "longitude", "LON") if c in ds.variables), None)
    return lat, lon


def _size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def _crop(ds, bbox, coast_km):
    """Crop to bbox (and coastal strip). Works for 1-D (regular grid) and 2-D (swath/projected) lat/lon."""
    latn, lonn = _coords(ds)
    if latn is None:
        return ds, None
    lat, lon = ds[latn], ds[lonn]
    if lat.ndim == 1 and lon.ndim == 1:
        if bbox:
            ds = ds.sel({latn: slice(*sorted((bbox["lat0"], bbox["lat1"]), reverse=bool(lat[0] > lat[-1]))),
                         lonn: slice(bbox["lon0"], bbox["lon1"])})
        if coast_km is None:
            return ds, None
        m = coastal_mask(ds[lonn].values, ds[latn].values, coast_km)
        rows, cols = np.where(m.any(axis=1))[0], np.where(m.any(axis=0))[0]
        ds = ds.isel({latn: slice(rows.min(), rows.max() + 1), lonn: slice(cols.min(), cols.max() + 1)})
        m = m[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
        return ds, xr.DataArray(m, dims=(latn, lonn))
    # 2-D coordinates
    keep = np.ones(lat.shape, bool)
    if bbox:
        keep &= ((lat >= bbox["lat0"]) & (lat <= bbox["lat1"]) & (lon >= bbox["lon0"]) & (lon <= bbox["lon1"])).values
    if coast_km is not None:
        keep &= coastal_mask(lon.values, lat.values, coast_km)
    if not keep.any():
        raise ValueError("no pixels left after cropping")
    ydim, xdim = lat.dims
    rows, cols = np.where(keep.any(axis=1))[0], np.where(keep.any(axis=0))[0]
    sl = {ydim: slice(rows.min(), rows.max() + 1), xdim: slice(cols.min(), cols.max() + 1)}
    return ds.isel(sl), xr.DataArray(keep[sl[ydim], sl[xdim]], dims=(ydim, xdim))


def slim_dataset(src: Path, keep: str, bbox=None, coast_km=None, sig_digits=4):
    """Return (slim dataset, encoding, mask) without writing."""
    ds = xr.open_dataset(src)
    pat = re.compile(keep)
    latn, lonn = _coords(ds)
    data_vars = [v for v in ds.data_vars if pat.match(v) and v not in (latn, lonn)]
    if not data_vars:
        ds.close()
        raise ValueError(f"no variable matches {keep!r}; found {list(ds.data_vars)[:10]}")
    sub = ds[data_vars]
    sub, mask = _crop(sub, bbox, coast_km)
    if mask is not None:
        for v in data_vars:
            if set(mask.dims) <= set(sub[v].dims) and np.issubdtype(sub[v].dtype, np.floating):
                sub[v] = sub[v].where(mask)
    enc = {}
    for v in sub.data_vars:
        e = dict(zlib=True, complevel=4, shuffle=True)
        if np.issubdtype(sub[v].dtype, np.floating):
            sub[v] = sub[v].astype("float32")
            # numeric fill value: with NaN as fill, netCDF quantisation corrupts missing pixels
            e["_FillValue"] = np.float32(-999.0)
            sub[v].attrs.pop("_FillValue", None)
            sub[v].encoding.pop("_FillValue", None)
            if sig_digits:
                e.update(significant_digits=int(sig_digits), quantize_mode="GranularBitRound")
        if "time" in sub[v].dims and sub[v].ndim == 3:
            e["chunksizes"] = (1,) + tuple(sub[v].shape[1:])
        enc[v] = e
    sub.attrs.update(ds.attrs)
    sub.attrs["greenpatch_slim"] = (f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ} from {src.name}; "
                                    f"keep={keep}; bbox={bbox}; coast_km={coast_km}; sig_digits={sig_digits}")
    return ds, sub, enc, mask


def verify(src_ds, expected, dst: Path, tol=1e-3):
    """Check the written slim file.

    1. Against the source: every kept variable exists there, and the time steps are identical.
    2. Against the expected in-memory slim data (cropped and masked source values): same shape,
       same valid-pixel pattern, values within a relative tolerance (quantisation error).
    """
    with xr.open_dataset(dst) as out:
        if set(out.data_vars) != set(expected.data_vars):
            return False, f"variables differ: {sorted(out.data_vars)}"
        if "time" in src_ds.dims:
            if "time" not in out.dims or not np.array_equal(out["time"].values, src_ds["time"].values):
                return False, "time steps differ from source"
        for v in out.data_vars:
            if v not in src_ds.data_vars:
                return False, f"{v}: not in source"
            av = np.asarray(expected[v].values, float)
            bv = np.asarray(out[v].values, float)
            if av.shape != bv.shape:
                return False, f"{v}: shape {bv.shape} vs source {av.shape}"
            fin = np.isfinite(av)
            if not np.array_equal(fin, np.isfinite(bv)):
                return False, f"{v}: valid-pixel pattern differs"
            if fin.any():
                rel = np.abs(bv[fin] - av[fin]) / np.maximum(np.abs(av[fin]), 1e-12)
                if rel.max() > tol:
                    return False, f"{v}: max relative difference {rel.max():.2e} > {tol}"
    return True, "ok"


def log_deletion(log: Path, path: Path, size: int, checksum: str, reason: str):
    new = not log.exists()
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["deleted_utc", "path", "size_bytes", "sha256", "reason"])
        w.writerow([f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}", str(path), size, checksum, reason])


def delete_path(p: Path):
    shutil.rmtree(p) if p.is_dir() else p.unlink()


# ------------------------------------------------------------------ ACOLITE <-> Level-1 matching
def acolite_key(name: str):
    """(platform, date, tile-or-pathrow or None) from an ACOLITE output name."""
    for rx in ACOLITE_RE:
        m = rx.match(name)
        if m:
            g = m.groups()
            return g[0], f"{g[1]}-{g[2]}-{g[3]}", g[7]
    return None


def l1_key(name: str):
    m = S2_RE.match(name)
    if m:
        sat, _, d8, _, tile = m.groups()
        return sat, f"{d8[:4]}-{d8[4:6]}-{d8[6:]}", tile
    m = LS_RE.match(name)
    if m:
        sat, _, pathrow, d8, _, _ = m.groups()
        return "L" + sat[-1], f"{d8[:4]}-{d8[4:6]}-{d8[6:]}", pathrow
    return None


def matching_l1(akey, l1_items):
    """Level-1 scenes matching an ACOLITE output. Without a tile in the ACOLITE name, match only if unique."""
    plat, date, tile = akey
    cands = [p for p, k in l1_items if k and k[0] == plat and k[1] == date and (tile is None or k[2] == tile)]
    return cands if (tile is not None or len(cands) == 1) else []
