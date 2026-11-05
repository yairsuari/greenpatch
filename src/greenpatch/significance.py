"""Stage 1 Method A steps 4-6 (guidelines/05_stage1_patch_identification.md), product-wide, after all tiles of
scripts/06: false discovery rate across the pixels of the whole domain, minimum effect size, and removal of small
isolated objects. Result: the "patch" mask per year and bin (and for the whole season and the daily movie window).

Run over the whole domain, never per tile: Benjamini-Hochberg ranks all p-values of a map together, and an object's
area must not be cut at a tile edge. The maps involved are 2-D, so this stays small even for the full domain.

  significant : q <= FDR_Q, with q the Benjamini-Hochberg adjusted p-value over all tested sea pixels of one map
  elevated    : anomaly >= the effect size in the direction of the signal (config.EFFECT_MIN = x1.5 above the baseline
                median for log variables; per-variable 'effect_min' in config.PREPROC, e.g. 0.3 psu for model salinity)
  patch       : significant & elevated, without 8-connected objects smaller than MIN_AREA_KM2
Decided with the user 2026-10-26 (FDR q = 0.10 per Wilks 2016; effect size x1.5 kept; small objects removed).
"""
from __future__ import annotations

import numpy as np
import xarray as xr
from scipy import ndimage

from . import config
from . import tiles as T
from .climatology import effect_min_of, signal_of
from .geo import cell_area_km2
from .preprocess import LAT, LON

FDR_Q = 0.10          # Method A step 4: alpha_FDR = 0.10, about a 0.05 global level under spatial correlation
MIN_AREA_KM2 = 1.0    # ⚙ Method A step 6: smallest object kept (about 11 pixels at 300 m, 100 at HR)
ONSET_PERSIST = 3     # ⚙ onset = first window centre that starts >= this many consecutive patch days (proposed 2026-11-05)


def onset(patch: np.ndarray, persist: int = ONSET_PERSIST) -> np.ndarray:
    """Index (along axis 0, time) of the first day that starts a run of >= persist consecutive patch days; -1 = none."""
    run = np.zeros(patch.shape[1:], int)
    first = np.full(patch.shape[1:], -1)
    for k in range(patch.shape[0]):
        run = np.where(patch[k] > 0, run + 1, 0)
        hit = (run == persist) & (first < 0)
        first[hit] = k - persist + 1
    return first


def bh(p: np.ndarray, q: float = FDR_Q) -> tuple[np.ndarray, np.ndarray, float]:
    """Benjamini-Hochberg over all finite values of p (any shape). Returns (q-values, significant, p threshold).

    The q-value of a pixel is the smallest FDR level at which it would be significant; significant = q <= `q`,
    which is the same as p <= the largest p_(k) with p_(k) <= k q / m (m = number of tested pixels).
    """
    flat = np.asarray(p, float).ravel()
    ok = np.isfinite(flat)
    qv = np.full(flat.shape, np.nan)
    m = int(ok.sum())
    if m == 0:
        return qv.reshape(np.shape(p)), np.zeros(np.shape(p), bool), 0.0
    order = np.argsort(flat[ok], kind="stable")
    ranked = flat[ok][order]
    adj = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    q_ok = np.empty(m)
    q_ok[order] = adj
    qv[ok] = q_ok
    sig = np.zeros(flat.shape, bool)
    sig[ok] = q_ok <= q
    thr = float(ranked[adj <= q].max()) if (adj <= q).any() else 0.0
    return qv.reshape(np.shape(p)), sig.reshape(np.shape(p)), thr


def remove_small(mask: np.ndarray, area_km2: np.ndarray, min_area: float = MIN_AREA_KM2) -> tuple[np.ndarray, int]:
    """Drop 8-connected objects of `mask` whose area is below min_area. Returns (cleaned mask, objects removed)."""
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), bool))
    if n == 0:
        return mask.astype(bool), 0
    areas = ndimage.sum(area_km2, lab, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = areas >= min_area
    return keep[lab], int((~keep[1:]).sum())


def classify(p, dx, sgn, sea, area, effect_min=config.EFFECT_MIN):
    """One map: (q, significant, elevated, patch, threshold, removed objects)."""
    p = np.where(sea, p, np.nan)
    qv, sig, thr = bh(p)
    with np.errstate(invalid="ignore"):
        elev = (sgn * dx >= effect_min) & sea
    patch, removed = remove_small(sig & elev, area)
    return qv, sig, elev, patch, thr, removed


def run(product: str, var: str) -> xr.Dataset:
    """Classify every map of one product and variable; writes <var>_significance.nc in the product folder."""
    ab = T.open_product(product, f"{var}_anom_bins")
    bins = T.open_product(product, "bins")
    ss = T.open_product(product, f"{var}_season")
    sea = ((bins["mask_land"] + bins["mask_buffer"]).values == 0)
    lat, lon = ab[LAT].values, ab[LON].values
    area = cell_area_km2(lon, lat)
    sgn, emin = signal_of(product, var), effect_min_of(product, var)
    logv = next(v["log"] for v in config.PREPROC[product]["vars"].values() if v["out"] == var)
    years, blist = ab["year"].values, ab["bin"].values
    shape = (len(years), len(blist), len(lat), len(lon))
    qa = np.full(shape, np.nan, "float32")
    sig, elev, patch = (np.zeros(shape, "int8") for _ in range(3))
    thr = np.zeros(shape[:2], "float32")
    removed = np.zeros(shape[:2], "int32")
    for i in range(len(years)):
        for j in range(len(blist)):
            e = ab.isel(year=i, bin=j)
            out = classify(e["p_a1"].values, e["dx"].values, sgn, sea, area, emin)
            qa[i, j], sig[i, j], elev[i, j], patch[i, j], thr[i, j], removed[i, j] = out
    dims = ("year", "bin", LAT, LON)
    ds = xr.Dataset(coords={"year": years, "bin": blist, LAT: lat, LON: lon})
    ds["q_a1"] = (dims, qa, dict(long_name="Benjamini-Hochberg q-value of p_a1 over all tested sea pixels of the map"))
    ds["sig"] = (dims, sig, dict(long_name=f"significant: q <= {FDR_Q}"))
    ds["elevated"] = (dims, elev, dict(long_name=(f"bin-median anomaly >= {emin:.4f} log10 (x{10 ** emin:.2f})" if logv else
                                                  f"bin-median anomaly >= {emin} (units of {var})") + " in the direction of the signal"))
    ds["patch"] = (dims, patch, dict(long_name=f"significant and elevated, objects < {MIN_AREA_KM2} km2 removed (8-connected)"))
    ds["p_threshold"] = (("year", "bin"), thr, dict(long_name="largest p-value declared significant (0 = none)"))
    ds["removed_objects"] = (("year", "bin"), removed, dict(long_name="small objects removed from the patch"))

    q2, s2, e2, p2, t2, r2 = classify(ss["p_season"].values, ss["dx_med"].values, sgn, sea, area, emin)
    ds["q_season"] = ((LAT, LON), q2.astype("float32"), dict(long_name="BH q-value of p_season"))
    ds["sig_season"] = ((LAT, LON), s2.astype("int8"), dict(long_name=f"whole season significant: q <= {FDR_Q}"))
    ds["patch_season"] = ((LAT, LON), p2.astype("int8"), dict(long_name="whole season: significant, elevated, cleaned"))
    ds.attrs.update(p_threshold_season=t2, removed_objects_season=r2)

    if (product, var) in config.WINDOW_VARS:
        wd = T.open_product(product, f"{var}_anom_window")
        nt = wd.sizes["time"]
        qw = np.full((nt, len(lat), len(lon)), np.nan, "float32")
        sw, pw = (np.zeros((nt, len(lat), len(lon)), "int8") for _ in range(2))
        for k in range(nt):
            w = wd.isel(time=k)
            qw[k], sw[k], _, pw[k], _, _ = classify(w["p"].values, w["dx"].values, sgn, sea, area, emin)
        ds = ds.assign_coords(time=wd["time"].values)
        ds["q_window"] = (("time", LAT, LON), qw, dict(long_name="BH q-value of the movie-window p, per day"))
        ds["sig_window"] = (("time", LAT, LON), sw, dict(long_name=f"window significant: q <= {FDR_Q}"))
        ds["patch_window"] = (("time", LAT, LON), pw, dict(long_name="window: significant, elevated, cleaned"))
        # onset map: first window centre starting a run of >= ONSET_PERSIST patch days, and that window's first day
        k0 = onset(pw)
        t, t0 = wd["time"].values, wd["win_start"].values
        nat = np.datetime64("NaT", "ns")
        ds["onset"] = ((LAT, LON), np.where(k0 >= 0, t[np.maximum(k0, 0)], nat),
                       dict(long_name=f"onset: first window centre starting >= {ONSET_PERSIST} consecutive patch days"))
        ds["onset_win_start"] = ((LAT, LON), np.where(k0 >= 0, t0[np.maximum(k0, 0)], nat),
                                 dict(long_name="first day of the onset window (earliest data behind the onset)"))
        ds.attrs.update(onset_persist_days=ONSET_PERSIST)

    ds["cell_area_km2"] = ((LAT, LON), area.astype("float32"))
    ds.attrs.update(product=product, variable=var, fdr_q=FDR_Q, min_area_km2=MIN_AREA_KM2,
                    effect_min=emin, effect_min_is_log10=int(logv), step="05 Method A steps 4-6 (product-wide)")
    return ds


def path(product: str, var: str):
    return T.product_dir(product) / f"{var}_significance.nc"
