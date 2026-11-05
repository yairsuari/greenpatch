"""Q2: what the operational Mediterranean model system shows for the 2026 patch (guidelines/07_q2_operational_model.md).

Inputs (run first, on the full domain):
  03_download_cmems.py --domain full --model ; 01_inventory.py --domain full ;
  05_preprocess.py / 06_climatology_anomaly.py --domain full --products medbgc medphy
  and the pilot satellite outputs of 05/06 (data/processed/pilot/olci300/).
Products: medbgc = model surface chl, medphy = model surface salinity, both from the reanalysis(-interim) 2016-2026,
with October 2026 from the operational analysis (user 2026-10-30; the analysis is offset from the reanalysis at the
coast, see q2_overlap_reanalysis_vs_analysis.csv, so October 2026 anomalies include that offset); medbgc_an / medphy_an =
the operational analysis alone (2024/2025-2026), for the saw-tooth test and the overlap check.

Outputs: results/full/tables/q2_*.csv and results/full/figures/q2/*.png
  q2_overlap_reanalysis_vs_analysis.csv  monthly median difference analysis - reanalysis on common days (coast, offshore)
  q2_coastal_strip.csv                   per bin: model 2026 anomaly on the Israel/Gaza coastal strip, rank among years,
                                         formal test (p < 0.05, FDR) and descriptive "record" cells
  q2_pilot_comparison.csv                per bin: satellite 300 m (pilot box) vs model cells covering the pilot box
  q2_sawtooth.csv                        operational analysis: mean daily change of coastal chl by weekday, decay after the
                                         weekly assimilation (2026 vs 2024-2025)
  q2_maps_<product>_<var>.png            2026 bin anomaly maps with the outline of record cells (2026 beyond every
                                         baseline year and beyond the effect size); pilot box marked
  q2_timeseries.png                      daily series at the pilot box: model chl (reanalysis, analysis), satellite chl,
                                         model salinity, with the 2016-2025 envelope
  q2_sawtooth.png                        weekday pattern and weekly decay of the operational analysis chl

Why the "record" maps: the formal per-pixel test (same as Q1) has almost no power on model output. The model fields are
smooth in time, a 10-day bin holds ~1.4 effective values, so the smallest attainable p is ~0.03 and Benjamini-Hochberg
over ~5,000 cells passes none. The descriptive record criterion (rank 1 of 11 years, beyond the effect size) is shown
next to it and labelled as descriptive.

Usage:  .venv/Scripts/python scripts/08_q2_operational_model.py
"""
import glob
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["GREENPATCH_DOMAIN"] = "full"   # model output lives on the full domain; the pilot is read by path

import dask  # noqa: E402
dask.config.set(scheduler="synchronous")   # HDF5 reads are not thread-safe here (segfault with threads)
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from greenpatch import config  # noqa: E402
from greenpatch import tiles as T  # noqa: E402
from greenpatch.climatology import effect_min_of, signal_of  # noqa: E402
from greenpatch.preprocess import bin_labels  # noqa: E402

warnings.simplefilter("ignore", RuntimeWarning)
EV = config.EVENT_YEAR
BASE = config.BASELINE["medbgc"]
PILOT = config.DOMAINS["pilot"]
PILOT_DIR = config.ROOT / "data" / "processed" / "pilot" / "olci300"
OUT_FIG = config.RESULTS / "figures" / "q2"
OUT_TAB = config.RESULTS / "tables"
COAST_KM, COAST_LON = 12.0, 34.2   # Israel/Gaza coastal strip: first ~3 model cells, east of 34.2 E
INK, MUTED, GRID, LANDC = "#0b0b0b", "#52514e", "#d9d8d4", "#e3e1da"
BLUE, ORANGE, GREEN, GRAY = "#2a78d6", "#eb6834", "#1a9641", "#9a9993"
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#86b6ef", "#f0efec", "#f4a3a2", "#e34948", "#8c1c1c"])
DIV.set_bad(LANDC)
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.titlesize": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.facecolor": "white"})
NICE = {"chl": "chlorophyll-a (log10 anomaly)", "so": "sea-surface salinity (anomaly, psu)"}
MAP_BINS = ["07-1", "07-2", "07-3", "08-1", "08-2", "08-3", "09-1", "09-2", "09-3", "10-1", "10-2", "10-3"]


def bin_dates(b):
    m, _, k = str(b).partition("-")
    m = int(m)
    end = (pd.Timestamp(2001, m, 1) + pd.offsets.MonthEnd(0)).day
    d0, d1 = {"": (1, end), "1": (1, 10), "2": (11, 20), "3": (21, end)}[k]
    return f"{d0}–{d1} {pd.Timestamp(2001, m, 1):%b}"


def letter(ax, k):
    ax.text(-0.02, 1.02, "abcdefghijklmnop"[k], transform=ax.transAxes, fontsize=10, fontweight="bold", va="bottom", ha="right")


def load_kind(p, kind):
    """All tiles of one output kind, read fully (no lazy multi-file opening: it crashed in the HDF5 layer here)."""
    files = sorted(T.product_dir(p).glob(f"{kind}_t[0-9][0-9][0-9][0-9].nc"))
    return xr.combine_by_coords([xr.load_dataset(f) for f in files], data_vars="minimal", coords="minimal",
                                compat="override")


def load_files(prod):
    return xr.concat([xr.load_dataset(f) for f in sorted(glob.glob(str(config.PRODUCTS[prod]["folder"] / "*.nc")))],
                     dim="time").sortby("time")


def model(p, v):
    ab = load_kind(p, f"{v}_anom_bins")
    b = load_kind(p, "bins")
    sg = xr.load_dataset(T.product_dir(p) / f"{v}_significance.nc")
    sea = (b["mask_land"] + b["mask_buffer"]).values == 0
    return ab, b, sg, sea


def strip_mask(b, sea):
    lon2 = b["longitude"].values[None, :] + 0 * b["n_km"].values
    return sea & (b["n_km"].values < COAST_KM) & (lon2 > COAST_LON)


def pilot_cells(b, sea):
    """Model sea cells whose 1/24 deg box overlaps the pilot box."""
    lat, lon = b["latitude"].values, b["longitude"].values
    h = 1 / 48
    iy = (lat + h > PILOT["lat0"]) & (lat - h < PILOT["lat1"])
    ix = (lon + h > PILOT["lon0"]) & (lon - h < PILOT["lon1"])
    return sea & iy[:, None] & ix[None, :]


def record_mask(ab, p, v, bn, sea):
    """Descriptive: 2026 bin median beyond every baseline year (in the signal direction) and beyond the effect size."""
    sgn, emin = signal_of(p, v), effect_min_of(p, v)
    med = ab["med"].sel(bin=bn)
    yrs = ab["year"].values
    ev = sgn * med.sel(year=EV).values
    base = sgn * med.sel(year=[y for y in yrs if y in BASE]).values
    dx = sgn * ab["dx"].sel(year=EV, bin=bn).values
    return (ev > np.nanmax(base, axis=0)) & (dx >= emin) & sea


def rank_of_event(ab, p, v, bn, cells):
    """Rank of 2026 among all years (1 = most signal) for the median over `cells`."""
    sgn = signal_of(p, v)
    m = np.nanmedian(ab["med"].sel(bin=bn).values[:, cells], axis=1) * sgn
    yrs = list(ab["year"].values)
    return int((m > m[yrs.index(EV)]).sum()) + 1, len(yrs)


# ---------------------------------------------------------------- 1. overlap reanalysis vs analysis
def overlap_table(b, sea):
    strip, off = strip_mask(b, sea), sea & (b["n_km"].values > 40)
    rows = []
    for v, my, an in (("chl", "medbgc", "medbgc_an"), ("so", "medphy", "medphy_an")):
        M = load_files(my)[v].isel(depth=0)
        A = load_files(an)[v].isel(depth=0)
        t = pd.DatetimeIndex(np.intersect1d(M["time"].values, A["time"].values))
        for (y, m), tt in pd.Series(t, index=t).groupby([t.year, t.month]):
            mm, aa = M.sel(time=tt.values).values, A.sel(time=tt.values).values
            for name, msk in (("coast", strip), ("offshore_gt40km", off)):
                d = (np.log10(aa[:, msk]) - np.log10(mm[:, msk])) if v == "chl" else (aa[:, msk] - mm[:, msk])
                rows.append(dict(variable=v, area=name, year=y, month=m, days=len(tt), median_diff=round(float(np.nanmedian(d)), 3),
                                 units="log10(analysis/reanalysis)" if v == "chl" else "psu (analysis - reanalysis)"))
    df = pd.DataFrame(rows)
    df.to_csv(OUT_TAB / "q2_overlap_reanalysis_vs_analysis.csv", index=False)
    return df


# ---------------------------------------------------------------- 2. coastal strip and pilot comparison
def strip_table():
    rows = []
    for p, v in (("medbgc", "chl"), ("medphy", "so")):
        ab, b, sg, sea = model(p, v)
        strip = strip_mask(b, sea)
        for bn in ab["bin"].values:
            e = ab.sel(year=EV, bin=bn)
            if not np.isfinite(e["dx"].values[strip]).any():
                continue
            rk, ny = rank_of_event(ab, p, v, bn, strip)
            rec = record_mask(ab, p, v, bn, sea)
            pv = e["p_a1"].values[strip]
            rows.append(dict(product=p, variable=v, bin=bn, dates=bin_dates(bn), strip_cells=int(strip.sum()),
                             dx_median=round(float(np.nanmedian(e["dx"].values[strip])), 3),
                             ratio_median=round(float(10 ** np.nanmedian(e["dx"].values[strip])), 2) if v == "chl" else None,
                             rank_2026=f"{rk}/{ny}", p_lt_005=int((pv < 0.05).sum()), p_min=round(float(np.nanmin(pv)), 3),
                             neff_year_median=round(float(np.nanmedian(e["neff_year"].values[strip])), 2),
                             fdr_significant=int(sg["sig"].sel(year=EV, bin=bn).values[strip].sum()),
                             record_cells=int(rec[strip].sum()), record_cells_domain=int(rec.sum())))
    df = pd.DataFrame(rows)
    df.to_csv(OUT_TAB / "q2_coastal_strip.csv", index=False)
    return df


def satellite_pilot():
    """300 m chl in the pilot box: per bin 2026 median, baseline median, anomaly, patch fraction; daily box medians."""
    ab = xr.load_dataset(PILOT_DIR / "chl_anom_bins_t0000.nc")
    sg = xr.load_dataset(PILOT_DIR / "chl_significance.nc")
    bins = xr.load_dataset(PILOT_DIR / "bins_t0000.nc")
    sea = (bins["mask_land"] + bins["mask_buffer"]).values == 0
    daily = xr.load_dataset(PILOT_DIR / "daily_t0000.nc")
    box = pd.Series(np.nanmedian(daily["chl"].values[:, sea], axis=1), index=pd.DatetimeIndex(daily["time"].values))
    out = {}
    for bn in ab["bin"].values:
        if EV not in ab["year"].values:
            continue
        med = ab["med"].sel(bin=bn).values[:, sea]
        yrs = list(ab["year"].values)
        boxmed = np.nanmedian(med, axis=1)
        base = np.nanmedian(boxmed[[yrs.index(y) for y in yrs if y in BASE]])
        out[bn] = dict(sat_chl_2026=10 ** boxmed[yrs.index(EV)], sat_chl_baseline=10 ** base,
                       sat_dx=float(np.nanmedian(ab["dx"].sel(year=EV, bin=bn).values[sea])),
                       sat_patch_pct=100 * float(sg["patch"].sel(year=EV, bin=bn).values[sea].mean()))
    return out, box


def pilot_table(sat):
    rows = {}
    for p, v in (("medbgc", "chl"), ("medphy", "so")):
        ab, b, sg, sea = model(p, v)
        cells = pilot_cells(b, sea)
        for bn in ab["bin"].values:
            med = ab["med"].sel(bin=bn).values[:, cells]
            yrs = list(ab["year"].values)
            m = np.nanmedian(med, axis=1)
            if not np.isfinite(m[yrs.index(EV)]):
                continue
            base = np.nanmedian(m[[yrs.index(y) for y in yrs if y in BASE]])
            rk, ny = rank_of_event(ab, p, v, bn, cells)
            r = rows.setdefault(bn, dict(bin=bn, dates=bin_dates(bn), model_cells=int(cells.sum())))
            if v == "chl":
                r.update(model_chl_2026=round(10 ** m[yrs.index(EV)], 3), model_chl_baseline=round(10 ** base, 3),
                         model_chl_ratio=round(10 ** (m[yrs.index(EV)] - base), 2), model_chl_rank=f"{rk}/{ny}",
                         model_chl_p_min=round(float(np.nanmin(ab["p_a1"].sel(year=EV, bin=bn).values[cells])), 3))
            else:
                r.update(model_so_2026=round(float(m[yrs.index(EV)]), 2), model_so_baseline=round(float(base), 2),
                         model_so_diff=round(float(m[yrs.index(EV)] - base), 2),
                         model_so_rank_fresh=f"{rk}/{ny}")
    for bn, r in rows.items():
        s = sat.get(bn)
        if s:
            r.update(sat_chl_2026=round(s["sat_chl_2026"], 2), sat_chl_baseline=round(s["sat_chl_baseline"], 2),
                     sat_chl_ratio=round(10 ** s["sat_dx"], 2), sat_patch_pct=round(s["sat_patch_pct"]))
    df = pd.DataFrame(list(rows.values()))
    df.to_csv(OUT_TAB / "q2_pilot_comparison.csv", index=False)
    return df


# ---------------------------------------------------------------- 3. maps
def fig_maps(p, v):
    ab, b, sg, sea = model(p, v)
    lat, lon = ab["latitude"].values, ab["longitude"].values
    lim = 0.6 if v == "chl" else 0.6
    fig, axes = plt.subplots(3, 4, figsize=(13, 7.0), squeeze=False)
    fig.subplots_adjust(left=0.04, right=0.9, top=0.89, bottom=0.08, wspace=0.06, hspace=0.32)
    for k, (ax, bn) in enumerate(zip(axes.flat, MAP_BINS)):
        dx = np.where(sea, ab["dx"].sel(year=EV, bin=bn).values, np.nan)
        m = ax.pcolormesh(lon, lat, np.ma.masked_invalid(dx), cmap=DIV, norm=Normalize(-lim, lim), shading="nearest")
        rec = record_mask(ab, p, v, bn, sea).astype(float)
        if rec.any():
            ax.contour(lon, lat, rec, levels=[0.5], colors=INK, linewidths=0.9)
        nsig = int(sg["sig"].sel(year=EV, bin=bn).values[sea].sum())
        ax.add_patch(Rectangle((PILOT["lon0"], PILOT["lat0"]), PILOT["lon1"] - PILOT["lon0"], PILOT["lat1"] - PILOT["lat0"],
                               fill=False, ec=ORANGE, lw=1.2))
        ax.set_title(f"{bin_dates(bn)} {EV}  (FDR-significant: {nsig})" + ("  *" if bn.startswith("10") else ""),
                     loc="left", fontsize=8)
        ax.set_aspect(1 / np.cos(np.radians(32)))
        ax.set_facecolor(LANDC)
        if k % 4:
            ax.set_yticklabels([])
        if k < 8:
            ax.set_xticklabels([])
        letter(ax, k)
    cb = fig.colorbar(m, cax=fig.add_axes([0.915, 0.15, 0.012, 0.68]))
    cb.set_label("2026 bin median − baseline median " + ("(log10; +0.3 = ×2)" if v == "chl" else "(psu; negative = fresher)"))
    eff = f"≥ ×{10 ** effect_min_of(p, v):.1f}" if v == "chl" else f"≤ −{effect_min_of(p, v)} psu"
    fig.legend(handles=[plt.Line2D([], [], color=INK, lw=0.9, label=f"descriptive 'record': 2026 beyond all 10 baseline years and {eff}"),
                        plt.Line2D([], [], color=ORANGE, lw=1.2, label="satellite pilot box (5 × 5 km)")],
               loc="lower left", fontsize=7.5, frameon=False, bbox_to_anchor=(0.01, -0.02), ncol=2)
    fig.text(0.6, 0.005, "* October 2026: operational analysis appended to the reanalysis-interim; includes the "
             "analysis-reanalysis offset", fontsize=7, color=MUTED)
    src = "Med BGC reanalysis 006_008 (interim for 2026)" if v == "chl" else "Med physics reanalysis 006_004 (interim for 2026)"
    fig.suptitle(f"Model {NICE[v]}, {src}: {EV} vs baseline {BASE[0]}–{BASE[-1]}.\nIn brackets: cells significant "
                 "with the Q1 test (Mann-Whitney, effective n, BH q ≤ 0.10).", x=0.01, ha="left", fontsize=9.5)
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG / f"q2_maps_{p}_{v}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 4. time series at the pilot box
def daily_cells(prod, v, cells):
    da = load_files(prod)[v].isel(depth=0)
    x = da.values[:, cells]
    return pd.Series(np.nanmedian(np.log10(x) if v == "chl" else x, axis=1), index=pd.DatetimeIndex(da["time"].values))


def envelope(s):
    """Per day of season over the baseline years: min, median, max."""
    df = pd.DataFrame({"v": s.values, "y": s.index.year, "doy": s.index.strftime("%m-%d")})
    df = df[df["y"].isin(BASE)]
    g = df.groupby("doy")["v"]
    days = pd.DatetimeIndex([f"{EV}-{d}" for d in g.min().index])
    return days, g.min().values, g.median().values, g.max().values


def fig_timeseries(sat_box):
    _, b, _, sea = model("medbgc", "chl")
    cells = pilot_cells(b, sea)
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
    ax = axes[0]
    s = daily_cells("medbgc", "chl", cells)
    d, lo, md, hi = envelope(s)
    ax.fill_between(d, 10 ** lo, 10 ** hi, color=GRAY, alpha=0.25, lw=0, label=f"model, {BASE[0]}–{BASE[-1]} range")
    ax.plot(d, 10 ** md, color=GRAY, lw=1, label="model, baseline median")
    e = s[s.index.year == EV]
    ax.plot(e.index, 10 ** e.values, color=BLUE, lw=1.6, label=f"model reanalysis-interim {EV} (Oct: operational analysis)")
    a = daily_cells("medbgc_an", "chl", cells)
    a = a[a.index.year == EV]
    ax.plot(a.index, 10 ** a.values, color=BLUE, lw=1, ls="--", label=f"model operational analysis {EV}")
    sb = sat_box[sat_box.index.year == EV]
    ax.plot(sb.index, 10 ** sb.values, "o", ms=2.5, color=GREEN, label=f"satellite 300 m, pilot box median {EV}")
    bs = sat_box[sat_box.index.year.isin(BASE)]
    bm = bs.groupby(bs.index.strftime("%m-%d")).median()
    ax.plot(pd.DatetimeIndex([f"{EV}-{x}" for x in bm.index]), (10 ** bm).rolling(11, center=True, min_periods=3).median(),
            color=GREEN, lw=1, alpha=0.7, label="satellite, baseline median (11-day running)")
    ax.set_yscale("log")
    ax.set_ylabel("chlorophyll-a (mg m⁻³)")
    ax.set_title(f"(a) Chlorophyll at the pilot box ({int(cells.sum())} model cell(s), ~4.2 km; satellite pixels 300 m)", loc="left")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(color=GRID, lw=0.4)
    ax = axes[1]
    s = daily_cells("medphy", "so", cells)
    d, lo, md, hi = envelope(s)
    ax.fill_between(d, lo, hi, color=GRAY, alpha=0.25, lw=0, label=f"model, {BASE[0]}–{BASE[-1]} range")
    ax.plot(d, md, color=GRAY, lw=1, label="model, baseline median")
    e = s[s.index.year == EV]
    ax.plot(e.index, e.values, color=BLUE, lw=1.6, label=f"model reanalysis-interim {EV} (Oct: operational analysis)")
    a = daily_cells("medphy_an", "so", cells)
    a = a[a.index.year == EV]
    ax.plot(a.index, a.values, color=BLUE, lw=1, ls="--", label=f"model operational analysis {EV} (offset, see table)")
    ax.set_ylabel("sea-surface salinity (psu)")
    ax.set_title("(b) Model surface salinity at the pilot box", loc="left")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(color=GRID, lw=0.4)
    ax.set_xlim(pd.Timestamp(f"{EV}-07-01"), pd.Timestamp(f"{EV}-10-31"))
    fig.tight_layout()
    fig.savefig(OUT_FIG / "q2_timeseries.png", dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------- 5. saw-tooth test (operational analysis)
def sawtooth():
    _, b, _, sea = model("medbgc", "chl")
    strip = strip_mask(b, sea)
    s = daily_cells("medbgc_an", "chl", strip)          # median log10 chl over the coastal strip, per day
    s = s[(s.index.month >= 7) & (s.index.month <= 10)]
    d = s.diff()
    d = d[(s.index.to_series().diff() == pd.Timedelta(days=1)).values]
    wd = d.groupby(d.index.dayofweek)
    tab = pd.DataFrame({"mean_change": wd.mean(), "mean_abs_change": wd.apply(lambda x: x.abs().mean()), "n": wd.size()})
    tab.index = [pd.Timestamp(2001, 1, 1 + i).strftime("%A") for i in tab.index]   # 2001-01-01 is a Monday
    jump_day = int(d.groupby(d.index.dayofweek).apply(lambda x: x.abs().mean()).idxmax())
    # decay: for each segment starting on the jump day, log10 chl on days 0..6 minus day 0
    rows = []
    for t0 in s.index[s.index.dayofweek == jump_day]:
        seg = s.reindex(pd.date_range(t0, periods=7))
        if seg.isna().any():
            continue
        rows.append(dict(start=t0, year=t0.year, month=t0.month, **{f"d{k}": seg.values[k] - seg.values[0] for k in range(7)}))
    dec = pd.DataFrame(rows)
    groups = {f"{EV} Sep–Oct": dec[(dec.year == EV) & dec.month.isin([9, 10])],
              f"{EV} Jul–Aug": dec[(dec.year == EV) & dec.month.isin([7, 8])],
              "2024–2025 Sep–Oct": dec[(dec.year < EV) & dec.month.isin([9, 10])]}
    summ = []
    for g, x in groups.items():
        summ.append(dict(group=g, segments=len(x), **{f"d{k}": round(float(x[f"d{k}"].mean()), 3) for k in range(7)}))
    out = pd.concat([tab.reset_index().rename(columns={"index": "weekday"}).assign(table="weekday"),
                     pd.DataFrame(summ).assign(table="decay_after_jump_log10")], ignore_index=True)
    out.attrs["jump_day"] = jump_day
    out.to_csv(OUT_TAB / "q2_sawtooth.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), gridspec_kw=dict(width_ratios=[2.2, 1, 1]))
    ax = axes[0]
    e = s[s.index.year == EV]
    ax.plot(e.index, 10 ** e.values, color=BLUE, lw=1.3)
    for t in e.index[e.index.dayofweek == jump_day]:
        ax.axvline(t, color=GRAY, lw=0.5, ls=":")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    ax.set_ylabel("chl (mg m⁻³), coastal-strip median")
    ax.set_title(f"(a) Operational analysis {EV}, Israel/Gaza coastal strip (< {COAST_KM:.0f} km)\ndotted = "
                 f"{pd.Timestamp(2001, 1, 1 + jump_day):%A}s (largest day-to-day change)", loc="left")
    ax.grid(color=GRID, lw=0.4)
    ax = axes[1]
    ax.bar(range(7), tab["mean_abs_change"].values, color=[ORANGE if i == jump_day else GRAY for i in range(7)])
    ax.set_xticks(range(7))
    ax.set_xticklabels([x[:3] for x in tab.index])
    ax.set_ylabel("mean |daily change| (log10)")
    ax.set_title("(b) Day-to-day change by weekday\n(Jul–Oct 2024–2026)", loc="left")
    ax = axes[2]
    for (g, x), c in zip(groups.items(), (BLUE, "#86b6ef", GRAY)):
        if len(x):
            ax.plot(range(7), [x[f"d{k}"].mean() for k in range(7)], "o-", color=c, ms=3, label=f"{g} (n={len(x)})")
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("days after the weekly jump")
    ax.set_ylabel("log10 chl change from day 0")
    ax.set_title("(c) Decay between assimilations", loc="left")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_FIG / "q2_sawtooth.png", dpi=170)
    plt.close(fig)
    return out, jump_day


def main():
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    OUT_TAB.mkdir(parents=True, exist_ok=True)
    _, b, _, sea = model("medbgc", "chl")
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print("== Reanalysis vs operational analysis (coast):")
    ov = overlap_table(b, sea)
    print(ov[ov.area == "coast"].to_string(index=False))
    print("\n== Coastal strip (Israel/Gaza, < 12 km):")
    print(strip_table().to_string(index=False))
    sat, box = satellite_pilot()
    print("\n== Pilot box: satellite vs model:")
    print(pilot_table(sat).to_string(index=False))
    for p, v in (("medbgc", "chl"), ("medphy", "so")):
        fig_maps(p, v)
    fig_timeseries(box)
    st, jd = sawtooth()
    print(f"\n== Saw-tooth (operational analysis, coastal strip), largest change on weekday {jd} (0 = Monday):")
    print(st.to_string(index=False))
    print(f"\nFigures -> {OUT_FIG}\nTables  -> {OUT_TAB}")


if __name__ == "__main__":
    main()
