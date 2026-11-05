"""Stage 1 steps 9-10 (guidelines/05_stage1_patch_identification.md): baseline climatology and anomalies,
plus the per-pixel test used for the p-value maps (Method A1, with the autocorrelation correction of Method A step 3:
effective sample sizes from the empirical autocorrelation of the baseline daily anomalies; no FDR yet).

Reference ("ref") per year: baseline years are compared with a leave-one-year-out climatology ("excl_<year>");
all other years (2026) with the full baseline ("all").
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

from . import config
from .preprocess import LAT, LON, season_bins

MIN_TARGET_OBS = 3   # ⚙ minimum observations of the tested year in a pixel-bin for the A1 test


def refs_for(baseline: list[int]) -> list[str]:
    return ["all"] + [f"excl_{y}" for y in baseline]


def ref_of(year: int, baseline: list[int]) -> str:
    return f"excl_{year}" if year in baseline else "all"


def _pool_mask(years: np.ndarray, ref: str, baseline: list[int]) -> np.ndarray:
    m = np.isin(years, baseline)
    if ref != "all":
        m &= years != int(ref.split("_")[1])
    return m


def climatology(daily: xr.Dataset, var: str, product: str) -> xr.Dataset:
    """Per ref, bin and pixel: median, robust SD (1.4826 MAD), P90, P95, max, N, years with data, sufficiency."""
    base, suff = config.BASELINE[product], config.SUFFICIENCY[product]
    refs, bins = refs_for(base), season_bins(daily.attrs["bin_kind"])
    x, yv, bv = daily[var].values, daily["year"].values, daily["bin"].values
    shape = (len(refs), len(bins), daily.sizes[LAT], daily.sizes[LON])
    out = {k: np.full(shape, np.nan, "float32") for k in ("med", "sd", "p90", "p95", "max")}
    n = np.zeros(shape, "int16")
    nyears = np.zeros(shape, "int8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for j, b in enumerate(bins):
            inbin = bv == b
            for i, r in enumerate(refs):
                sel = inbin & _pool_mask(yv, r, base)
                if not sel.any():
                    continue
                pool = x[sel]
                med = np.nanmedian(pool, 0)
                out["med"][i, j] = med
                out["sd"][i, j] = 1.4826 * np.nanmedian(np.abs(pool - med), 0)
                out["p90"][i, j], out["p95"][i, j] = np.nanpercentile(pool, [90, 95], axis=0)
                out["max"][i, j] = np.nanmax(pool, 0)
                n[i, j] = np.isfinite(pool).sum(0)
                nyears[i, j] = sum(np.isfinite(x[inbin & (yv == y)]).any(0) for y in set(yv[sel].tolist()))
    ds = xr.Dataset(coords={"ref": refs, "bin": bins, LAT: daily[LAT], LON: daily[LON]})
    units = daily[var].attrs.get("units", "")
    for k, a in out.items():
        ds[k] = (("ref", "bin", LAT, LON), a, dict(units=units))
    ds["sd"].attrs["long_name"] = "robust SD = 1.4826 x MAD"
    ds["n"] = (("ref", "bin", LAT, LON), n, dict(long_name="valid baseline observations in the pool"))
    ds["nyears"] = (("ref", "bin", LAT, LON), nyears, dict(long_name="baseline years with data"))
    # rule for the "all" reference; leave-one-out references have one year fewer available
    min_years = np.array([suff["min_years"] if r == "all" else suff["min_years"] - 1 for r in refs])[:, None, None, None]
    ds["sufficient"] = (("ref", "bin", LAT, LON), ((n >= suff["min_n"]) & (nyears >= min_years)).astype("int8"),
                        dict(long_name=f"data sufficiency: N >= {suff['min_n']} and >= {suff['min_years']} baseline years "
                                       "(one fewer for leave-one-year-out references)"))
    ds.attrs.update(variable=var, product=product, baseline=f"{base[0]}-{base[-1]}", bin_kind=daily.attrs["bin_kind"])
    return ds


def anomalies_daily(daily: xr.Dataset, var: str, clim: xr.Dataset, product: str) -> xr.Dataset:
    """Per observation: dx = x - median, z = dx / robust SD, percentile rank in the pool, exceedance flags."""
    base = config.BASELINE[product]
    x, yv, bv = daily[var].values, daily["year"].values, daily["bin"].values
    dx = np.full(x.shape, np.nan, "float32")
    z, pct = dx.copy(), dx.copy()
    exc = {k: np.zeros(x.shape, "int8") for k in ("p90", "p95", "max")}
    bins = list(clim["bin"].values)
    with np.errstate(invalid="ignore", divide="ignore"):
        for y in sorted(set(yv.tolist())):
            r = ref_of(y, base)
            ri = list(clim["ref"].values).index(r)
            pmask = _pool_mask(yv, r, base)
            for b in set(bv[yv == y].tolist()):
                t = (yv == y) & (bv == b)
                j = bins.index(b)
                c = clim.isel(ref=ri, bin=j)
                xs = x[t]
                dx[t] = xs - c["med"].values
                z[t] = dx[t] / c["sd"].values
                for k in exc:
                    exc[k][t] = (xs > c[k].values).astype("int8")
                pool = x[pmask & (bv == b)]                                   # (np, y, x)
                if len(pool):
                    less = (pool[None] < xs[:, None]).sum(1)
                    eq = (pool[None] == xs[:, None]).sum(1)
                    npool = np.isfinite(pool).sum(0)
                    pct[t] = np.where(np.isfinite(xs), 100 * (less + 0.5 * eq) / np.maximum(npool, 1), np.nan)
    ds = xr.Dataset(coords={"time": daily["time"], LAT: daily[LAT], LON: daily[LON]})
    ds["dx"] = (("time", LAT, LON), dx, dict(long_name=f"anomaly of {var} (x - baseline median)", units=daily[var].attrs.get("units", "")))
    ds["z"] = (("time", LAT, LON), z, dict(long_name="robust standardized anomaly (dx / robust SD)"))
    ds["pct"] = (("time", LAT, LON), pct, dict(long_name="percentile rank in the baseline pool", units="%"))
    for k, a in exc.items():
        ds[f"exc_{k}"] = (("time", LAT, LON), np.where(np.isfinite(x), a, -1).astype("int8"),
                          dict(long_name=f"above baseline {k} (1), not above (0), no data (-1)"))
    ds["ref"] = ("time", np.array([ref_of(y, base) for y in yv]))
    ds["year"], ds["bin"] = daily["year"], daily["bin"]
    ds.attrs.update(variable=var, product=product)
    return ds


def effect_min_of(product: str, var: str) -> float:
    """Minimum effect size for "elevated" (Method A step 5): per-variable 'effect_min', else config.EFFECT_MIN."""
    return next(v.get("effect_min", config.EFFECT_MIN) for v in config.PREPROC[product]["vars"].values() if v["out"] == var)


def signal_of(product: str, var: str) -> int:
    """+1 if higher values mean more signal, -1 if lower values do (config.PREPROC 'signal')."""
    return next(v.get("signal", 1) for v in config.PREPROC[product]["vars"].values() if v["out"] == var)


# ---------------------------------------------------------------- Method A step 3: autocorrelation (effective n)
# Decided 2026-10-26: the AR(1) formula n (1 - rho1) / (1 + rho1) of 05 does not fit the data (HR has no lag-1 pairs,
# Sentinel-2 revisit; 300 m anomalies decay much more slowly than AR(1)). Its general form is used instead:
# n_eff = n^2 / sum_i sum_j r(|t_i - t_j|) over pairs in the same year, with r the empirical autocorrelation function.
MAX_LAG = 30         # ⚙ longest lag (days) of the autocorrelation function (longest bin: a 31-day month)
MIN_ACF_PAIRS = 20   # ⚙ minimum pairs at a lag to use a pixel's own estimate (else the tile-pooled one)


def _corr(a, b, axis=0):
    """Pearson correlation of paired arrays with NaN where a pair is missing (per pixel, or pooled if axis=None)."""
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        da, db = a - np.nanmean(a, 0), b - np.nanmean(b, 0)   # centred per pixel in both cases
        return np.nansum(da * db, axis) / np.sqrt(np.nansum(da ** 2, axis) * np.nansum(db ** 2, axis))


def anomaly_acf(ad: xr.Dataset, product: str, max_lag: int = MAX_LAG) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Empirical autocorrelation r(k), k = 0..max_lag days, of the daily anomalies (dx) of the BASELINE years, per
    pixel, from pairs of valid days exactly k days apart in the same year. 2026 is excluded: its persistence is the
    signal being tested. Lags with < MIN_ACF_PAIRS pairs at a pixel take the tile-pooled estimate; lags with no pairs
    in the tile (e.g. lag 1 for the Sentinel-2-based HR product) are interpolated between lags; r is floored at 0.

    Returns (r_used (lag, y, x), r_raw (NaN where the pixel had too few pairs), n_pairs (lag, y, x)).
    """
    base = config.BASELINE[product]
    t = ad["time"].values
    yv = ad["year"].values
    dx = np.where(np.isin(yv, base)[:, None, None], ad["dx"].values, np.nan)
    shape = (max_lag + 1,) + dx.shape[1:]
    raw, npairs = np.full(shape, np.nan, "float32"), np.zeros(shape, "int32")
    raw[0], pooled = 1.0, np.full(max_lag + 1, np.nan)
    pooled[0] = 1.0
    for k in range(1, max_lag + 1):
        same = ((t[k:] - t[:-k]) == np.timedelta64(k, "D")) & (yv[k:] == yv[:-k])
        a, b = dx[:-k][same], dx[k:][same]
        ok = np.isfinite(a) & np.isfinite(b)
        a, b = np.where(ok, a, np.nan), np.where(ok, b, np.nan)
        npairs[k] = ok.sum(0)
        if ok.sum() >= MIN_ACF_PAIRS:
            pooled[k] = _corr(a, b, axis=None)
        raw[k] = np.where(npairs[k] >= MIN_ACF_PAIRS, _corr(a, b), np.nan)
    have = np.isfinite(pooled)
    lags = np.arange(max_lag + 1)
    pooled = np.interp(lags, lags[have], pooled[have])   # no pairs at all at a lag: interpolate (edges: nearest)
    used = np.where(np.isfinite(raw), raw, pooled[:, None, None])
    return np.clip(used, 0.0, 1.0).astype("float32"), raw, npairs


def pair_sums(x: np.ndarray, times: np.ndarray, sel: np.ndarray, years: np.ndarray, acf: np.ndarray) -> dict:
    """{year: (n, S)} for the valid observations of x[sel], per year: n = count and S = sum_i sum_j r(|t_i - t_j|)
    over pairs of the same year (S = n if r = 0 beyond lag 0). Different years are independent, so n and S of several
    years add up; n_eff = n^2 / S (n_effective)."""
    out, kmax = {}, acf.shape[0] - 1
    for y in np.unique(years[sel]):
        idx = np.flatnonzero(sel & (years == y))
        v, t = np.isfinite(x[idx]), times[idx]
        n = v.sum(0).astype("float64")
        s = n.copy()
        for d in range(1, len(idx)):
            lag = ((t[d:] - t[:-d]) / np.timedelta64(1, "D")).astype(int)
            keep = lag <= kmax
            if not keep.any():
                break   # times are sorted, so larger offsets only give larger lags
            both = v[:-d][keep] & v[d:][keep]
            s += 2.0 * (acf[lag[keep]] * both).sum(0)
        out[int(y)] = (n, s)
    return out


def n_effective(parts) -> np.ndarray:
    """n_eff = n^2 / S from (n, S) of independent years (pair_sums values)."""
    parts = list(parts)
    if not parts:
        return np.array(0.0)
    n = sum(p[0] for p in parts)
    s = sum(p[1] for p in parts)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, n ** 2 / s, 0.0)


def mannwhitney_greater(target: np.ndarray, pool: np.ndarray, n1_eff=None, n2_eff=None, both: bool = False):
    """One-sided Mann-Whitney U (H1: target > pool) per pixel, normal approximation with continuity correction.

    target (n1, ...), pool (n2, ...), NaN = missing. n1_eff / n2_eff (per pixel; default n1 / n2): effective sample
    sizes for autocorrelation (Method A step 3); the variance of U / (n1 n2) under H0 is taken with them, so with
    n_eff = n this is the ordinary test. Returns p (NaN where either side is empty), or (p, p_uncorrected) if both.
    No tie correction (values are continuous).
    """
    n1 = np.isfinite(target).sum(0)
    n2 = np.isfinite(pool).sum(0)
    # U from mid-ranks of the combined sample (memory ~ (n1 + n2) x pixels; identical to counting pairs)
    ranks = stats.rankdata(np.concatenate([target, pool], axis=0), axis=0, nan_policy="omit")
    u = np.nansum(ranks[: len(target)], axis=0) - n1 * (n1 + 1) / 2.0

    def p_for(n1e, n2e):
        n1e, n2e = np.maximum(n1e, 1.0), np.maximum(n2e, 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            auc = (u - 0.5) / (n1 * n2)                              # with continuity correction
            zz = (auc - 0.5) / np.sqrt((n1e + n2e + 1) / (12.0 * n1e * n2e))
        return np.where((n1 > 0) & (n2 > 0), stats.norm.sf(zz), np.nan)

    p = p_for(n1 if n1_eff is None else n1_eff, n2 if n2_eff is None else n2_eff)
    return (p, p_for(n1, n2)) if both else p


def anomalies_bins(daily: xr.Dataset, bins_ds: xr.Dataset, var: str, clim: xr.Dataset, product: str,
                   acf: np.ndarray | None = None) -> xr.Dataset:
    """Per year, bin and pixel: composite anomaly (dx, z), A1 p-value (autocorrelation-corrected with the effective
    sample sizes from `acf` (anomaly_acf), and uncorrected), effective sample sizes, counts, sufficiency.
    acf None = no correction (r = 0 beyond lag 0)."""
    base = config.BASELINE[product]
    years, bins = list(bins_ds["year"].values), list(bins_ds["bin"].values)
    x, yv, bv = daily[var].values, daily["year"].values, daily["bin"].values
    shape = (len(years), len(bins), daily.sizes[LAT], daily.sizes[LON])
    dxb = np.full(shape, np.nan, "float32")
    zb, p, pu, ne1, ne2 = dxb.copy(), dxb.copy(), dxb.copy(), dxb.copy(), dxb.copy()
    times = daily["time"].values
    acf = acf if acf is not None else np.ones((1,) + x.shape[1:], "float32")
    parts = {b: pair_sums(x, times, bv == b, yv, acf) for b in bins}   # per bin: {year: (n, S)}
    suff = np.zeros(shape, "int8")
    refs = list(clim["ref"].values)
    for i, y in enumerate(years):
        r = ref_of(int(y), base)
        ri = refs.index(r)
        pmask = _pool_mask(yv, r, base)
        for j, b in enumerate(bins):
            c = clim.isel(ref=ri, bin=j)
            with np.errstate(invalid="ignore", divide="ignore"):
                dxb[i, j] = bins_ds[f"med_{var}"].values[i, j] - c["med"].values
                zb[i, j] = dxb[i, j] / c["sd"].values
            suff[i, j] = c["sufficient"].values
            t = (yv == y) & (bv == b)
            if t.any():
                sgn = signal_of(product, var)   # test "more signal": higher values, or lower for signal = -1
                ne1[i, j] = n_effective([parts[b][int(y)]])
                ne2[i, j] = n_effective(parts[b][yy] for yy in parts[b] if yy in base and (r == "all" or yy != y))
                pij, puij = mannwhitney_greater(sgn * x[t], sgn * x[pmask & (bv == b)], ne1[i, j], ne2[i, j], both=True)
                ok = (np.isfinite(x[t]).sum(0) >= MIN_TARGET_OBS) & (c["sufficient"].values == 1)
                p[i, j], pu[i, j] = np.where(ok, pij, np.nan), np.where(ok, puij, np.nan)
    ds = xr.Dataset(coords={"year": years, "bin": bins, LAT: daily[LAT], LON: daily[LON]})
    units = daily[var].attrs.get("units", "")
    ds["dx"] = (("year", "bin", LAT, LON), dxb, dict(long_name="bin-median anomaly (composite - baseline median)", units=units))
    ds["z"] = (("year", "bin", LAT, LON), zb, dict(long_name="bin-median robust z"))
    ds["p_a1"] = (("year", "bin", LAT, LON), p.astype("float32"),
                  dict(long_name="Method A1 one-sided Mann-Whitney p (year shows more signal than baseline), per pixel",
                       direction="year > baseline" if signal_of(product, var) > 0 else "year < baseline (lower = more signal)",
                       note=f"Corrected for autocorrelation: effective sample sizes n_eff = n^2 / sum r(|t_i - t_j|) from the "
                            f"empirical autocorrelation of the baseline daily anomalies (anomaly_acf); NO FDR; NaN if "
                            f"< {MIN_TARGET_OBS} observations of the year or insufficient baseline"))
    ds["neff_year"] = (("year", "bin", LAT, LON), ne1, dict(long_name="effective sample size of the tested year"))
    ds["neff_base"] = (("year", "bin", LAT, LON), ne2, dict(long_name="effective sample size of the baseline pool"))
    ds["p_a1_uncorr"] = (("year", "bin", LAT, LON), pu.astype("float32"),
                         dict(long_name="as p_a1 without the autocorrelation correction"))
    ds["sufficient"] = (("year", "bin", LAT, LON), suff, dict(long_name="baseline sufficiency of the reference used"))
    ds["n"] = bins_ds[f"n_{var}"]
    ds["nflag"] = bins_ds[f"nflag_{var}"]
    ds["med"] = bins_ds[f"med_{var}"]
    ds.attrs.update(variable=var, product=product)
    return ds


def usage_counts(product: str, daily: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    """Valid and flagged pixels per date of the main variable in one tile (summed over tiles for the audit)."""
    spec = config.PREPROC[product]
    x = daily[spec["main"]].values
    f = daily[f"flag_{spec['main']}"].values.astype(bool) & np.isfinite(x)
    return np.isfinite(x).sum(axis=(1, 2)), f.sum(axis=(1, 2))


def image_usage(product: str, times, bins, valid: np.ndarray, flagged: np.ndarray, inventory_dates: set[str]) -> pd.DataFrame:
    """One row per date of the product: valid pixels after masking (whole domain) and which statistics it entered."""
    spec = config.PREPROC[product]
    base = config.BASELINE[product]
    rows = []
    for k, t in enumerate(pd.DatetimeIndex(times)):
        nv = int(valid[k])
        y = int(t.year)
        rows.append(dict(product=product, date=t.strftime("%Y-%m-%d"), year=y, bin=str(bins[k]),
                         variable=spec["main"], valid_pixels=nv, flagged_pixels=int(flagged[k]),
                         in_composite=nv > 0, in_climatology=(nv > 0) and (y in base), in_anomaly=nv > 0,
                         in_inventory=t.strftime("%Y-%m-%d") in inventory_dates,
                         status="used" if nv > 0 else "no valid pixels (all masked or cloud)"))
    df = pd.DataFrame(rows)
    missing = sorted(inventory_dates - set(df["date"]))
    if missing:
        df = pd.concat([df, pd.DataFrame([dict(product=product, date=d, status="ERROR: in inventory, not processed")
                                          for d in missing])], ignore_index=True)
    return df


def window_stats(daily: xr.Dataset, var: str, product: str, year: int = config.EVENT_YEAR,
                 half: int = config.WINDOW_HALF, acf: np.ndarray | None = None) -> xr.Dataset | None:
    """Daily sliding window (for the movie): per centre day of `year` and pixel, the median of `year` minus the baseline
    median over the same calendar days, and a one-sided Mann-Whitney p of `year` vs baseline values (as Method A1).

    Centres run from the season start to the last date of `year`. The window [centre - half, centre + half] is clipped
    to the season and to that last date, so `year` and the baseline cover the same calendar days; win_start / win_end
    give the clipped window. p is NaN with < MIN_TARGET_OBS observations of `year` or an insufficient baseline (same
    rule as the bins: N >= min_n and >= min_years baseline years). Corrected for autocorrelation with the effective
    sample sizes from `acf` (as the bins); no FDR; windows of consecutive days overlap, so successive frames are not
    independent.
    """
    base, suff = config.BASELINE[product], config.SUFFICIENCY[product]
    t = pd.DatetimeIndex(daily["time"].values)
    off = np.array([(x - pd.Timestamp(x.year, *config.SEASON["start"])).days for x in t])   # day of season, 0 = start
    x, yv = daily[var].values, daily["year"].values
    ev = yv == year
    if not ev.any():
        return None
    last = int(off[ev].max())
    inbase = np.isin(yv, base)
    sgn = signal_of(product, var)
    s0 = pd.Timestamp(year, *config.SEASON["start"])
    shape = (last + 1, daily.sizes[LAT], daily.sizes[LON])
    dx, p, pu = (np.full(shape, np.nan, "float32") for _ in range(3))
    times = daily["time"].values
    acf = acf if acf is not None else np.ones((1,) + x.shape[1:], "float32")
    n, nb = np.zeros(shape, "int16"), np.zeros(shape, "int16")
    nyears, ok_base = np.zeros(shape, "int8"), np.zeros(shape, "int8")
    lo = np.maximum(np.arange(last + 1) - half, 0)
    hi = np.minimum(np.arange(last + 1) + half, last)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for c in range(last + 1):
            win = (off >= lo[c]) & (off <= hi[c])
            xt, xb = x[win & ev], x[win & inbase]
            n[c], nb[c] = np.isfinite(xt).sum(0), np.isfinite(xb).sum(0)
            nyears[c] = sum(np.isfinite(x[win & (yv == y)]).any(0) for y in base)
            ok_base[c] = (nb[c] >= suff["min_n"]) & (nyears[c] >= suff["min_years"])
            if not len(xt) or not len(xb):
                continue
            dx[c] = np.nanmedian(xt, 0) - np.nanmedian(xb, 0)
            parts = pair_sums(x, times, win & (ev | inbase), yv, acf)
            ne1 = n_effective([parts[year]]) if year in parts else 0.0
            ne2 = n_effective(parts[y] for y in parts if y in base)
            pc, puc = mannwhitney_greater(sgn * xt, sgn * xb, ne1, ne2, both=True)
            okc = (n[c] >= MIN_TARGET_OBS) & (ok_base[c] == 1)
            p[c], pu[c] = np.where(okc, pc, np.nan), np.where(okc, puc, np.nan)
    centres = s0 + pd.to_timedelta(np.arange(last + 1), "D")
    ds = xr.Dataset(coords={"time": centres, LAT: daily[LAT], LON: daily[LON]})
    units = daily[var].attrs.get("units", "")
    dims = ("time", LAT, LON)
    ds["dx"] = (dims, dx, dict(long_name=f"window median of {var}, {year} minus baseline", units=units))
    ds["p"] = (dims, p, dict(long_name=f"one-sided Mann-Whitney p, {year} vs baseline values in the window",
                             direction="year > baseline" if sgn > 0 else "year < baseline (lower = more signal)",
                             note=f"corrected for autocorrelation (n_eff); NO FDR; NaN if < {MIN_TARGET_OBS} "
                                  "observations of the year or insufficient baseline"))
    ds["p_uncorr"] = (dims, pu, dict(long_name="as p without the autocorrelation correction"))
    ds["n"] = (dims, n, dict(long_name=f"valid {year} values in the window"))
    ds["n_base"] = (dims, nb, dict(long_name="valid baseline values in the window"))
    ds["nyears"] = (dims, nyears, dict(long_name="baseline years with data in the window"))
    ds["sufficient"] = (dims, ok_base, dict(long_name=f"baseline sufficiency: N >= {suff['min_n']} and >= "
                                                      f"{suff['min_years']} years"))
    ds["win_start"] = ("time", s0 + pd.to_timedelta(lo, "D"), dict(long_name="first day of the clipped window"))
    ds["win_end"] = ("time", s0 + pd.to_timedelta(hi, "D"), dict(long_name="last day of the clipped window"))
    ds.attrs.update(variable=var, product=product, year=year, half_width_days=half, baseline=f"{base[0]}-{base[-1]}")
    return ds


def season_stats(daily: xr.Dataset, ad: xr.Dataset, var: str, product: str, year: int = config.EVENT_YEAR,
                 acf: tuple | None = None) -> xr.Dataset:
    """Whole-season (all bins) statistics per pixel, for the season climatology and anomaly figures.

    clim_med / clim_sd / clim_n : median, robust SD and count of all valid baseline daily values in the season
    dx_med / dx_n               : median of the daily anomalies of `year` (each day against its own bin climatology;
                                  user decision 2026-10-23) and their number
    p_season                    : one-sided Mann-Whitney p, daily anomalies of `year` vs the baseline years' daily
                                  anomalies (leave-one-year-out), corrected for autocorrelation with n_eff; no FDR
    p_season_uncorr             : the same without the autocorrelation correction
    acf / acf_raw / acf_npairs  : autocorrelation of the baseline daily anomalies by lag (anomaly_acf output) as used,
                                  the pixel's own estimate, and its pairs; neff_year / neff_base of the season test
    """
    base, suff = config.BASELINE[product], config.SUFFICIENCY[product]
    x, yv = daily[var].values, daily["year"].values
    dx = ad["dx"].values
    pool = x[np.isin(yv, base)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(pool, 0)
        sd = 1.4826 * np.nanmedian(np.abs(pool - med), 0)
        ev = dx[yv == year]
        dmed = np.nanmedian(ev, 0) if len(ev) else np.full(med.shape, np.nan)
    n_base = np.isfinite(pool).sum(0)
    n_ev = np.isfinite(ev).sum(0) if len(ev) else np.zeros(med.shape, int)
    sgn = signal_of(product, var)
    acf = acf if acf is not None else anomaly_acf(ad, product)
    parts = pair_sums(dx, ad["time"].values, np.isin(yv, base) | (yv == year), yv, acf[0])
    ne1 = n_effective([parts[year]]) if year in parts else np.zeros(med.shape)
    ne2 = n_effective(parts[y] for y in parts if y in base)
    if len(ev):
        p, pu = mannwhitney_greater(sgn * ev, sgn * dx[np.isin(yv, base)], ne1, ne2, both=True)
    else:
        p = pu = np.full(med.shape, np.nan)
    okp = (n_ev >= MIN_TARGET_OBS) & (n_base >= suff["min_n"])
    p, pu = np.where(okp, p, np.nan), np.where(okp, pu, np.nan)
    ds = xr.Dataset(coords={LAT: daily[LAT], LON: daily[LON]})
    units = daily[var].attrs.get("units", "")
    ds["clim_med"] = ((LAT, LON), med.astype("float32"), dict(long_name=f"season median of {var}, baseline", units=units))
    ds["clim_sd"] = ((LAT, LON), sd.astype("float32"), dict(long_name="season robust SD, baseline", units=units))
    ds["clim_n"] = ((LAT, LON), n_base.astype("int32"), dict(long_name="valid baseline daily values in the season"))
    ds["dx_med"] = ((LAT, LON), dmed.astype("float32"), dict(long_name=f"median of {year} daily anomalies", units=units))
    ds["dx_n"] = ((LAT, LON), n_ev.astype("int32"), dict(long_name=f"valid {year} daily anomalies"))
    ds["p_season"] = ((LAT, LON), p.astype("float32"),
                      dict(long_name=f"one-sided Mann-Whitney p, {year} vs baseline daily anomalies, whole season",
                           note="corrected for autocorrelation (effective sample sizes from acf); NO FDR"))
    ds["p_season_uncorr"] = ((LAT, LON), pu.astype("float32"),
                             dict(long_name="as p_season without the autocorrelation correction"))
    ds = ds.assign_coords(lag=np.arange(acf[0].shape[0]))
    ds["acf"] = (("lag", LAT, LON), acf[0], dict(long_name="autocorrelation of baseline daily anomalies, as used",
                                                 note=f"tile-pooled where < {MIN_ACF_PAIRS} pairs; floored at 0",
                                                 units="1", lag_units="days"))
    ds["acf_raw"] = (("lag", LAT, LON), acf[1], dict(long_name="pixel estimate (NaN with too few pairs)"))
    ds["acf_npairs"] = (("lag", LAT, LON), acf[2], dict(long_name="day pairs at this lag"))
    ds["neff_year"] = ((LAT, LON), np.asarray(ne1, "float32") * np.ones(med.shape, "float32"),
                       dict(long_name=f"effective sample size of {year} in the season test"))
    ds["neff_base"] = ((LAT, LON), np.asarray(ne2, "float32") * np.ones(med.shape, "float32"),
                       dict(long_name="effective sample size of the baseline in the season test"))
    ds.attrs.update(variable=var, product=product, year=year, baseline=f"{base[0]}-{base[-1]}")
    return ds
