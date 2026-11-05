"""Stage 1 preprocessing (guidelines/05_stage1_patch_identification.md, Part 1, steps 3, 6, 7, 8).

Per product (settings in config.PREPROC), per spatial tile (src/greenpatch/tiles.py):
  step 3  pixel masking: plausible range, land (cells never valid in the record, or on land in GSHHG) plus a
          coastal buffer of `buffer_px` pixels; 3x3 local-median outlier FLAG (values are never changed or removed)
  step 6  analysis variables: log10 where config says so (chl, absorption, turbidity, SPM); ratios stay linear
  step 7  coastal coordinates per cell: distance to coast n (km), alongshore s (km), cell area (km²)
  step 8  calendar bins (10-day, or monthly fallback decided over the whole product) and per-year bin composites

Image-use rule: every daily field is kept. Masking acts only on pixels; no day is dropped.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
import xarray as xr
from scipy import ndimage

from . import config, geo
from .tiles import LAT, LON, grid, source_files


# ---------------------------------------------------------------- calendar bins (step 8)
def bin_labels(times, kind: str = "10d") -> np.ndarray:
    """Calendar bin label per date: '07-1', '07-2', '07-3' (days 1-10, 11-20, 21-end) or '07' for monthly bins."""
    t = pd.DatetimeIndex(times)
    if kind == "month":
        return np.array([f"{m:02d}" for m in t.month])
    dek = np.where(t.day <= 10, 1, np.where(t.day <= 20, 2, 3))
    return np.array([f"{m:02d}-{d}" for m, d in zip(t.month, dek)])


def season_bins(kind: str = "10d") -> list[str]:
    days = pd.date_range("2001-%02d-%02d" % config.SEASON["start"], "2001-%02d-%02d" % config.SEASON["end"])
    return list(dict.fromkeys(bin_labels(days, kind)))


# ---------------------------------------------------------------- loading
def load_region(name: str, i0: int, i1: int, j0: int, j1: int) -> xr.Dataset:
    """All season files of one product, cut to rows i0:i1 and columns j0:j1 of its grid, along time."""
    files = source_files(name)
    spec = config.PREPROC[name]
    wanted = list(spec["vars"]) + spec["keep"]
    parts = []
    for f in files:
        with xr.open_dataset(f) as ds:
            sub = ds[[v for v in wanted if v in ds]].isel({LAT: slice(i0, i1), LON: slice(j0, j1)})
            if "depth" in sub.dims:   # model output: one surface level (config.MODEL_DEPTH)
                sub = sub.isel(depth=0, drop=True)
            parts.append(sub.load())
    ds = xr.concat(parts, dim="time").sortby("time")
    ds = ds.sel(time=~ds.get_index("time").duplicated())
    ds.attrs["source_files"] = ";".join(f.name for f in files)
    return ds


# ---------------------------------------------------------------- outlier flag (step 3)
def _nanmedian_window(a: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Local nanmedian and number of valid neighbours (excluding the centre) in a w x w window, per 2-D field."""
    r = w // 2
    pad = np.pad(a, ((0, 0), (r, r), (r, r)), constant_values=np.nan)
    win = np.lib.stride_tricks.sliding_window_view(pad, (w, w), axis=(1, 2))      # (t, y, x, w, w)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(win, axis=(-2, -1))
    n = np.isfinite(win).sum(axis=(-2, -1)) - np.isfinite(a)
    return med, n


def outlier_flag(x: np.ndarray, window: int, n_sd: float, min_neighbours: int, min_valid_day: int):
    """Flag pixels whose value departs from the local median by more than n_sd robust SD of that day's residuals
    (within the tile). x: (time, y, x) analysis values (NaN = invalid). Returns (flag bool array, local median).
    Flag only: the caller never changes or removes the flagged values (user decision 2026-10-21).
    """
    med, n = _nanmedian_window(x, window)
    res = x - med
    flag = np.zeros(x.shape, bool)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for t in range(x.shape[0]):
            ok = np.isfinite(res[t]) & (n[t] >= min_neighbours)
            if ok.sum() < min_valid_day:
                continue
            r = res[t][ok]
            sd = 1.4826 * np.median(np.abs(r - np.median(r)))
            if sd > 0:
                flag[t] = ok & (np.abs(res[t]) > n_sd * sd)
    return flag, med


# ---------------------------------------------------------------- one tile (steps 3, 6, 7)
def preprocess_tile(name: str, tile: dict, halo: int = config.TILE_HALO) -> xr.Dataset:
    """Daily analysis fields of one tile (core cells only). Bin labels are attached later (finalize step)."""
    spec = config.PREPROC[name]
    lat_all, lon_all = grid(name)
    hi0, hi1 = max(tile["i0"] - halo, 0), min(tile["i1"] + halo, len(lat_all))
    hj0, hj1 = max(tile["j0"] - halo, 0), min(tile["j1"] + halo, len(lon_all))
    raw = load_region(name, hi0, hi1, hj0, hj1)
    lat, lon = raw[LAT].values, raw[LON].values
    core = (slice(tile["i0"] - hi0, tile["i1"] - hi0), slice(tile["j0"] - hj0, tile["j1"] - hj0))
    times = raw.get_index("time")

    # step 7 + land: on the halo region (the buffer needs land next to the core)
    n_km = geo.distance_to_coast_km(lon, lat)
    main_in = next(k for k, v in spec["vars"].items() if v["out"] == spec["main"])
    never = ~np.isfinite(raw[main_in].values).any(axis=0)
    land = never | (n_km < 0) if spec.get("gshhg_land", True) else never
    buffer = (ndimage.binary_dilation(land, np.ones((3, 3), bool), iterations=spec["buffer_px"]) & ~land
              if spec["buffer_px"] else np.zeros_like(land))
    excluded = land | buffer

    clat, clon = lat[core[0]], lon[core[1]]
    out = xr.Dataset(coords={"time": times, LAT: clat, LON: clon})
    out["n_km"] = ((LAT, LON), n_km[core].astype("float32"), dict(long_name="distance to mainland coast (GSHHG full)", units="km"))
    out["s_km"] = ((LAT, LON), geo.alongshore_km(clon, clat).astype("float32"),
                   dict(long_name="alongshore distance from the Damietta mouth (smoothed coast)", units="km"))
    out["area_km2"] = ((LAT, LON), geo.cell_area_km2(lon, lat)[core].astype("float32"), dict(units="km2"))
    out["mask_land"] = ((LAT, LON), land[core].astype("int8"),
                        dict(long_name="land or never valid in the record (provider mask) or on land in GSHHG"))
    out["mask_buffer"] = ((LAT, LON), buffer[core].astype("int8"),
                          dict(long_name=f"coastal buffer of {spec['buffer_px']} pixel(s) next to land"))
    exc_c = excluded[core]

    # steps 3 + 6 per variable (outlier test on the halo region, statistics on the core)
    stats = {}
    for vin, v in spec["vars"].items():
        if vin not in raw:
            raise KeyError(f"{name}: variable {vin} not in files (have {list(raw.data_vars)})")
        a = raw[vin].values.astype("float64")
        finite = np.isfinite(a)
        in_range = finite & (a >= v["vmin"]) & (a <= v["vmax"])
        keep = in_range & ~excluded[None]
        with np.errstate(divide="ignore", invalid="ignore"):
            x = np.where(keep, np.log10(a) if v["log"] else a, np.nan)
        flag, _ = outlier_flag(x, **config.OUTLIER)
        sl = (slice(None),) + core
        x, flag, finite, in_range, keep = x[sl], flag[sl], finite[sl], in_range[sl], keep[sl]
        o = v["out"]
        units = raw[vin].attrs.get("units", "")
        out[o] = (("time", LAT, LON), x.astype("float32"),
                  dict(long_name=("log10 of " if v["log"] else "") + raw[vin].attrs.get("long_name", vin),
                       units=f"log10({units})" if v["log"] else units, source_variable=vin,
                       plausible_range=f"{v['vmin']}..{v['vmax']} {units}"))
        out[f"flag_{o}"] = (("time", LAT, LON), flag.astype("int8"),
                            dict(long_name=f"3x3 local-median outlier flag for {o} (flag only, value kept)",
                                 settings=str(config.OUTLIER)))
        stats[o] = dict(raw_valid=int((finite & ~exc_c[None]).sum()),
                        out_of_range=int((finite & ~in_range & ~exc_c[None]).sum()),
                        in_land_or_buffer=int((finite & exc_c[None]).sum()), kept=int(keep.sum()), flagged=int(flag.sum()))
    for k in spec["keep"]:
        if k in raw:
            out[k] = raw[k].isel({LAT: core[0], LON: core[1]}).astype("float32").where(~xr.DataArray(exc_c, dims=(LAT, LON)))
            out[k].attrs.update(raw[k].attrs, note="diagnostic only, never used to mask")

    out["year"] = ("time", times.year.values.astype("int16"))
    fails, total = bin_rule_counts(out[spec["main"]].values, out["year"].values, times, sea=~exc_c, name=name)
    out.attrs.update(product=name, domain=config.DOMAIN_NAME, tile=json.dumps(tile), source_files=raw.attrs["source_files"],
                     step="05 Part 1 steps 3, 6, 7", mask_stats=json.dumps(stats), bin10_fails=fails, bin10_total=total)
    return out


def bin_rule_counts(x, years, times, sea, name) -> tuple[int, int]:
    """Sea pixel-bins (10-day bins) failing the sufficiency rule, and their total (Step 8 rule, summed over tiles)."""
    bv = bin_labels(times, "10d")
    base, suff = config.BASELINE[name], config.SUFFICIENCY[name]
    fails, total = 0, 0
    for b in season_bins("10d"):
        sel = (bv == b) & np.isin(years, base)
        valid = np.isfinite(x[sel])
        n = valid.sum(0)
        ny = sum(valid[years[sel] == y].any(0) for y in base) if sel.any() else np.zeros(n.shape)
        ok = (n >= suff["min_n"]) & (ny >= suff["min_years"])
        fails += int((~ok & sea).sum())
        total += int(sea.sum())
    return fails, total


def choose_bin_kind(name: str, fails: int, total: int) -> tuple[str, str]:
    """Step 8 rule over the whole product: 10-day bins unless more than BIN_FALLBACK_FRAC of the sea pixel-bins fail."""
    frac = fails / max(total, 1)
    setting = config.BIN[name]
    kind = ("month" if frac > config.BIN_FALLBACK_FRAC else "10d") if setting == "auto" else setting
    return kind, (f"setting {setting}; with 10-day bins {frac:.0%} of sea pixel-bins fail the sufficiency rule "
                  f"(fallback above {config.BIN_FALLBACK_FRAC:.0%})")


# ---------------------------------------------------------------- step 8 composites (per tile, after the bin choice)
def composites(daily: xr.Dataset, name: str) -> xr.Dataset:
    """Per year and calendar bin: median of valid daily values, number of valid values, number flagged."""
    years = sorted(set(daily["year"].values.tolist()))
    bins = season_bins(daily.attrs["bin_kind"])
    lat, lon = daily[LAT].values, daily[LON].values
    out = xr.Dataset(coords={"year": years, "bin": bins, LAT: lat, LON: lon})
    for c in ("n_km", "s_km", "area_km2", "mask_land", "mask_buffer"):
        out[c] = daily[c]
    yv, bv = daily["year"].values, daily["bin"].values
    for o in [v["out"] for v in config.PREPROC[name]["vars"].values()]:
        x, f = daily[o].values, daily[f"flag_{o}"].values.astype(bool)
        med = np.full((len(years), len(bins), len(lat), len(lon)), np.nan, "float32")
        cnt = np.zeros(med.shape, "int16")
        nfl = np.zeros(med.shape, "int16")
        for i, y in enumerate(years):
            for j, b in enumerate(bins):
                sel = (yv == y) & (bv == b)
                if not sel.any():
                    continue
                xs = x[sel]
                cnt[i, j] = np.isfinite(xs).sum(0)
                nfl[i, j] = (f[sel] & np.isfinite(xs)).sum(0)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    med[i, j] = np.nanmedian(xs, axis=0)
        out[f"med_{o}"] = (("year", "bin", LAT, LON), med, dict(long_name=f"bin median of {o}", units=daily[o].attrs["units"]))
        out[f"n_{o}"] = (("year", "bin", LAT, LON), cnt, dict(long_name=f"valid daily values of {o} in the bin"))
        out[f"nflag_{o}"] = (("year", "bin", LAT, LON), nfl, dict(long_name=f"flagged (3x3 outlier) values of {o} in the bin"))
    out.attrs.update({k: v for k, v in daily.attrs.items() if k in ("product", "domain", "tile", "bin_kind")},
                     step="05 Part 1 step 8 (bin composites)")
    return out


def encoding(ds: xr.Dataset) -> dict:
    enc = {}
    for v in ds.data_vars:
        if ds[v].dtype.kind not in "fiub":
            continue   # text variables (bin labels) cannot be compressed
        e = dict(zlib=True, complevel=4, shuffle=True)
        if ds[v].dtype.kind == "f":
            e["_FillValue"] = -999.0   # NaN fill breaks quantisation (handoff notes)
        enc[v] = e
    return enc


def save(ds: xr.Dataset, path):
    """Write atomically (tmp file, then rename), without the per-time bin labels (they are derived from meta.json)."""
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = ds.drop_vars([v for v in ("bin",) if v in ds.data_vars])
    tmp = path.with_suffix(".tmp.nc")
    ds.to_netcdf(tmp, encoding=encoding(ds))
    tmp.replace(path)
