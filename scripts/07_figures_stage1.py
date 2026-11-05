"""Stage 1 figures from the preprocessing, climatology and anomaly outputs (scripts/05, 06). Works for any domain size:
map figures read only the 2-D slices they show (lazy, tiled data) and are block-median coarsened for display above
MAX_DISPLAY cells per side; daily-level figures stream the tiles one at a time (exact counts, or a fixed sample of sea
pixels where a sample suffices).

Figure set agreed with the user (2026-10-21, 2026-10-23); all for the event year (config.EVENT_YEAR) unless noted:
  overview_dx_<product>_<var>.png      small multiples: bin-median anomaly per calendar bin
  bin_<product>_<var>_<bin>.png        one page per bin: raw bin median | climatology median | climatology robust SD |
                                       anomaly || 3x3 local median + outlier flags | p-value (A1, autocorr.-corrected) |
                                       observations in the year | baseline support (N, insufficient hatched)
  timeseries_<product>_<var>.png       daily values at key points (3x3 box median) over the baseline envelope per bin
  chl_vs_cdom.png                      chl, adg443, aph443 anomalies and a class map (chl-only / CDOM-only / both)
  hr_vs_300m.png                       monthly median daily anomaly: 300 m chl | HR chl | HR turbidity
  distributions_<product>_<var>.png    per bin: box values of every year (event year highlighted) [sampled pixels]
  coverage.png                         valid-pixel fraction per bin and year, per product [exact]
  qi_vs_z.png                          provider QI_CHL against our robust z (300 m chl) [sampled pixels]
  season_climatology.png               whole-season baseline median: chl (greens), CDOM a_dg443, HR turbidity
  season_anomaly.png                   2026 median daily anomaly of the same three, with significance (green = BH q <= 0.10)
  paper_<product>_<var>.png            manuscript candidate (user 2026-10-26): anomaly per bin with the patch outline
  autocorrelation.png                  autocorrelation of the baseline daily anomalies by lag, per variable (Method A
                                       step 3 effective sample sizes)
  movie_<product>_<var>_window11d.mp4  (user 2026-10-26) one frame per day: 2026 window median minus baseline median |
                                       p-value, window = day +-5 days (config.WINDOW_HALF), with a timeline; for
                                       config.WINDOW_VARS (300 m chl); needs the <var>_anom_window output of script 06
  onset_<product>_<var>.png            (2026-11-05) onset date per pixel from the daily-window patch, onset against the
                                       alongshore coordinate, patch extent per day
  tables/colocation_chl_patch.csv      (2026-11-05) per bin: land-input indicators (a_dg443, a_ph443, Rrs412/443, HR
                                       turbidity) inside vs outside the 300 m chl patch
Every multi-panel figure carries panel letters and every map a scale bar; significance maps: green = significant after
Benjamini-Hochberg (q <= 0.10), light red = tested, not significant; outlines = patch (also >= x1.5, >= 1 km2). Every bin label is shown with its calendar date range (e.g. '08-2: 11-20 Aug').
Output: results/<domain>/figures/stage1/<group>/ with group = chlorophyll (chl, a_ph443, QI), cdom (a_dg443,
Rrs412/443), turbidity (HR turbidity, SPM) or combined (figures with several variables) (user 2026-10-26).

Usage (from the project root)
  .venv/Scripts/python scripts/07_figures_stage1.py                 # main variables
  .venv/Scripts/python scripts/07_figures_stage1.py --all-vars      # bin pages and time series for every variable
  .venv/Scripts/python scripts/07_figures_stage1.py --domain full --max-pixels 20000
  .venv/Scripts/python scripts/07_figures_stage1.py --movie-only --fps 4   # only the movie (4 days per second)
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap, LogNorm, Normalize  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from scipy import stats  # noqa: E402
from shapely.geometry import box, shape  # noqa: E402

from greenpatch import config  # noqa: E402
from greenpatch import tiles as T  # noqa: E402
from greenpatch.climatology import signal_of  # noqa: E402
from greenpatch.plotting import add_scalebar  # noqa: E402

# ---------------------------------------------------------------- style (dataviz reference palette)
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
SURFACE, LAND, NODATA = "#fcfcfb", "#e3e1da", "#ffffff"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9993"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#86b6ef", "#f0efec", "#f4a3a2", "#e34948", "#8c1c1c"])
GREENS = LinearSegmentedColormap.from_list("greens", ["#e5f5e0", "#a1d99b", "#41ab5d", "#238b45", "#006d2c", "#00441b"])
YLORBR = LinearSegmentedColormap.from_list("cdom", ["#fff7bc", "#fec44f", "#ec7014", "#cc4c02", "#8c2d04", "#662506"])
BROWN = LinearSegmentedColormap.from_list("turbidity", ["#f3ebe1", "#d9c2a3", "#b8916a", "#8c6239", "#5e3c1e", "#3b240f"])
VAR_CMAP = {"chl": GREENS, "aph443": GREENS, "adg443": YLORBR, "tur": BROWN, "spm": BROWN}   # user 2026-10-23
P_GREEN, P_RED = "#1a9641", "#fbe0dc"   # p < 0.05 green, p >= 0.05 very light red (user 2026-10-23)
PCMAP = ListedColormap([P_GREEN, P_RED])
PNORM = BoundaryNorm([0, 0.05, 1.0], 2)
for c in (SEQ, DIV, GREENS, YLORBR, BROWN, PCMAP):
    c.set_bad(NODATA)
DX_LIM = 1.2   # anomaly colour range in log10 units: ±1.2 = x16 / x1/16 (2026 pilot reaches +1.6)
MAX_DISPLAY = 1200   # maps larger than this (cells per side) are block-median coarsened for display only
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titlesize": 8.5, "axes.titlecolor": INK, "figure.facecolor": "white",
                     "savefig.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False})

OUT = config.RESULTS / "figures" / "stage1"
EV = config.EVENT_YEAR
LAT, LON = "latitude", "longitude"
MAIN = [("olci300", "chl"), ("cdom300", "adg443"), ("hr", "chl")]
NICE = {"chl": "chlorophyll-a", "adg443": "CDOM+detritus absorption a_dg(443)", "aph443": "phytoplankton absorption a_ph(443)",
        "r412_443": "Rrs(412)/Rrs(443)", "tur": "turbidity", "spm": "suspended matter"}
PNAME = {"olci300": "300 m OLCI", "cdom300": "300 m OLCI (QAA)", "hr": "HR ~100 m"}
MAX_PIXELS = 5000   # sea pixels sampled for distribution and QI figures (all pixels if the domain has fewer)
# Output subfolder per variable (user 2026-10-26); figures that combine several variables go to "combined"
GROUP = {"chl": "chlorophyll", "aph443": "chlorophyll", "adg443": "cdom", "r412_443": "cdom",
         "tur": "turbidity", "spm": "turbidity"}
COMBINED = "combined"
MOVIE_FPS = 4


def dstr(t):
    t = pd.Timestamp(t)
    return f"{t.day} {t:%b}"


def bin_dates(b):
    """Calendar date range of a bin label: '08-2' -> '11–20 Aug', '08' -> '1–31 Aug'."""
    m, _, k = str(b).partition("-")
    m = int(m)
    end = (pd.Timestamp(2001, m, 1) + pd.offsets.MonthEnd(0)).day
    d0, d1 = {"": (1, end), "1": (1, 10), "2": (11, 20), "3": (21, end)}[k]
    return f"{d0}–{d1} {pd.Timestamp(2001, m, 1):%b}"


SEASON_TXT = f"{dstr(pd.Timestamp(2001, *config.SEASON['start']))}–{dstr(pd.Timestamp(2001, *config.SEASON['end']))}"


def quiet():
    w = warnings.catch_warnings()
    w.__enter__()
    warnings.simplefilter("ignore", RuntimeWarning)
    return w


# ---------------------------------------------------------------- data access (tiled, lazy)
def opened(p, kind):
    """One output kind of a product, all tiles combined, lazily (only what is selected is read)."""
    return T.open_product(p, kind, load=False)


def load(p, v):
    """Map-level inputs: bin composites (with masks), climatology, bin anomalies. No daily data."""
    return opened(p, "bins"), opened(p, f"{v}_clim"), opened(p, f"{v}_anom_bins")


def sea_mask(ds):
    return ((ds["mask_land"] + ds["mask_buffer"]).values == 0)


def units_of(ds, v):
    a = ds[v] if v in ds else ds[f"med_{v}"]
    u = a.attrs.get("units", "")
    return u[6:-1] if u.startswith("log10(") else u


def linear(v, x):
    """Back-transform for display in natural units (log10 variables -> value)."""
    logv = any(s["out"] == v and s["log"] for spec in config.PREPROC.values() for s in spec["vars"].values())
    return 10 ** x if logv else x, logv


def has_year(ab, b):
    return EV in ab["year"].values and np.isfinite(ab["med"].sel(year=EV, bin=b).values).any()


def tiles_of(p):
    return T.read_meta(p)["tiles"]


def sample_index(p, max_pixels):
    """Per tile: flat indices of a fixed, evenly spread sample of sea pixels (every k-th sea pixel of the domain)."""
    meta = T.read_meta(p)
    n_sea = meta["cells"] - meta["land_cells"] - meta["buffer_cells"]
    step = max(1, int(np.ceil(n_sea / max_pixels)))
    out, offset = {}, 0
    for t in meta["tiles"]:
        with xr.open_dataset(T.tile_path(p, "bins", t["k"])) as b:
            sea = sea_mask(b).ravel()
        idx = np.flatnonzero(sea)
        first = (-offset) % step
        out[t["k"]] = idx[first::step]
        offset += len(idx)
    return out, step, n_sea


# ---------------------------------------------------------------- map helpers
_land = shape(json.loads(config.COASTLINE.read_text(encoding="utf-8"))["features"][0]["geometry"])
d = config.DOMAIN
M = 0.1 * max(d["lat1"] - d["lat0"], d["lon1"] - d["lon0"])
VIEW = (d["lon0"] - M, d["lon1"] + M, d["lat0"] - M, d["lat1"] + M)
_land_view = _land.intersection(box(VIEW[0], VIEW[2], VIEW[1], VIEW[3]))
ASPECT = 1 / np.cos(np.radians((d["lat0"] + d["lat1"]) / 2))


def draw_land(ax):
    for g in getattr(_land_view, "geoms", [_land_view]):
        if g.geom_type == "Polygon" and not g.is_empty:
            ax.add_patch(MplPolygon(np.asarray(g.exterior.coords), closed=True, facecolor=LAND, edgecolor=MUTED,
                                    linewidth=0.6, zorder=3))


def coarsen(lon, lat, a):
    """Block nanmedian to at most MAX_DISPLAY cells per side (display only; statistics are never coarsened)."""
    f = int(np.ceil(max(a.shape) / MAX_DISPLAY))
    if f <= 1:
        return lon, lat, a
    ny, nx = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    blk = a[:ny, :nx].reshape(ny // f, f, nx // f, f)
    w = quiet()
    out = np.nanmedian(blk, axis=(1, 3))
    w.__exit__(None, None, None)
    return lon[:nx].reshape(-1, f).mean(1), lat[:ny].reshape(-1, f).mean(1), out


def pmap(ax, ds, field, cmap, norm, title, sea=None):
    a = np.asarray(field, float)
    if sea is not None:
        a = np.where(sea, a, np.nan)
    lon, lat, a = coarsen(ds[LON].values, ds[LAT].values, a)
    m = ax.pcolormesh(lon, lat, np.ma.masked_invalid(a), cmap=cmap, norm=norm, shading="nearest", zorder=1)
    draw_land(ax)
    ax.set_xlim(VIEW[0], VIEW[1])
    ax.set_ylim(VIEW[2], VIEW[3])
    ax.set_aspect(ASPECT)
    add_scalebar(ax, VIEW, fontsize=6.5)
    ax.set_facecolor(NODATA)
    ax.set_title(title, loc="left")
    ax.tick_params(labelsize=6.5, length=2)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(0.5)
    return m


def cbar(fig, m, ax, label, **kw):
    kw = {"shrink": 0.85, "pad": 0.02, **kw}
    cb = fig.colorbar(m, ax=ax, **kw)
    cb.set_label(label, fontsize=7, color=MUTED)
    cb.ax.tick_params(labelsize=6.5)
    cb.outline.set_linewidth(0.4)
    if isinstance(m.norm, LogNorm):   # plain numbers instead of 3x10^0
        from matplotlib.ticker import FuncFormatter, LogLocator
        cb.ax.yaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
        cb.ax.yaxis.set_minor_formatter(FuncFormatter(lambda x, _: ""))
        cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
    return cb


def dx_cbar(fig, m, ax, signal=1, **kw):
    cb = cbar(fig, m, ax, "anomaly (log10 ratio to baseline median)" + ("" if signal > 0 else ", sign flipped: red = more CDOM"), **kw)
    ticks = [-1.2, -0.6, -0.3, 0, 0.3, 0.6, 1.2]
    cb.set_ticks(ticks, labels=[f"{t:+.1f} (×{10 ** t:.2g})" for t in ticks])
    return cb


def p_cbar(fig, m, ax, **kw):
    """Two-class colour bar for significance maps (sig_class)."""
    cb = cbar(fig, m, ax, "Mann-Whitney + FDR", **kw)
    cb.set_ticks([0.025, 0.525], labels=["significant\n(FDR q ≤ 0.10)", "not\nsignificant"])
    cb.ax.tick_params(length=0)
    return cb


def sig_class(sig, p):
    """Map for PCMAP / PNORM: 0 = significant after FDR (green), 0.5 = tested, not significant, NaN = not tested."""
    return np.where(np.isfinite(p), np.where(np.asarray(sig) > 0, 0.0, 0.5), np.nan)


def significance(p, v):
    """Product-wide FDR / effect-size / small-object output of scripts/06 (src/greenpatch/significance.py)."""
    return xr.open_dataset(T.product_dir(p) / f"{v}_significance.nc")


def norm_for(v, *arrays):
    vals = np.concatenate([np.ravel(a)[np.isfinite(np.ravel(a))] for a in arrays]) if arrays else np.array([])
    _, logv = linear(v, 0.0)
    if logv:
        return LogNorm(*np.percentile(vals, [2, 98])) if vals.size else LogNorm(0.1, 10)
    return Normalize(*np.percentile(vals, [2, 98])) if vals.size else Normalize(0, 1)


def local_median(a):
    pad = np.pad(a, 1, constant_values=np.nan)
    win = np.lib.stride_tricks.sliding_window_view(pad, (3, 3))
    w = quiet()
    out = np.nanmedian(win, axis=(-2, -1))
    w.__exit__(None, None, None)
    return out


def label_panels(fig):
    """Bold letter (a, b, c, ...) at the upper left of every visible panel (colour bars excluded)."""
    axes = [ax for ax in fig.axes if ax.get_visible() and not hasattr(ax, "_colorbar") and ax.get_label() != "<colorbar>"]
    if len(axes) < 2:
        return
    for i, ax in enumerate(axes):
        lab = chr(97 + i) if i < 26 else chr(97 + i // 26 - 1) + chr(97 + i % 26)
        ax.text(-0.03, 1.0, lab, transform=ax.transAxes, ha="right", va="bottom", fontsize=10, fontweight="bold",
                color=INK)


def save(fig, name, group):
    label_panels(fig)
    (OUT / group).mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / group / name, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  ", f"{group}/{name}")


# ---------------------------------------------------------------- 1. overview of anomalies
def fig_overview(p, v):
    bins, clim, ab = load(p, v)
    sea, sgn = sea_mask(bins), signal_of(p, v)
    sg = significance(p, v)
    blist = list(ab["bin"].values)
    nc = 6 if len(blist) > 6 else len(blist)
    nr = int(np.ceil(len(blist) / nc))
    fig, axes = plt.subplots(nr, nc, figsize=(2.1 * nc + 1, 2.2 * nr + 0.6), squeeze=False)
    norm = Normalize(-DX_LIM, DX_LIM)
    m = None
    for k, ax in enumerate(axes.flat):
        if k >= len(blist):
            ax.set_visible(False)
            continue
        b = blist[k]
        if EV in ab["year"].values:
            a = sgn * ab["dx"].sel(year=EV, bin=b).values
            m = pmap(ax, ab, a, DIV, norm, f"{b}: {bin_dates(b)}", sea)
            sig_contour(ax, ab, sg["patch"].sel(year=EV, bin=b).values > 0)
            if not np.isfinite(a[sea]).any():
                ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", va="center", color=MUTED, zorder=5)
        if k % nc:
            ax.set_yticklabels([])
        if k < len(blist) - nc:
            ax.set_xticklabels([])
    fig.suptitle(f"{EV} anomaly of {NICE[v]} by calendar bin ({bins.attrs['bin_kind']}), {PNAME[p]}, domain "
                 f"'{config.DOMAIN_NAME}'  ·  bin median minus baseline {clim.attrs['baseline']} median  ·  "
                 "outline = patch (FDR q ≤ 0.10, ≥ ×1.5, objects < 1 km² removed)",
                 x=0.01, ha="left", fontsize=9.5, color=INK)
    if m is not None:
        dx_cbar(fig, m, axes, sgn)
    save(fig, f"overview_dx_{p}_{v}.png", GROUP[v])


# ---------------------------------------------------------------- 2. per-bin pages
def fig_bin_pages(p, v):
    bins, clim, ab = load(p, v)
    sea, sgn = sea_mask(bins), signal_of(p, v)
    u = units_of(bins, v)
    for b in ab["bin"].values:
        if not has_year(ab, b):
            continue
        e = ab.sel(year=EV, bin=b).load()
        c = clim.sel(ref="all", bin=b).load()
        g = significance(p, v).sel(year=EV, bin=b).load()
        raw, logv = linear(v, e["med"].values)
        cm_, _ = linear(v, c["med"].values)
        vn = norm_for(v, raw[sea], cm_[sea])
        fig, axes = plt.subplots(2, 4, figsize=(15, 7.4))
        m = pmap(axes[0, 0], e, raw, VAR_CMAP.get(v, SEQ), vn, f"{EV} bin median\n(raw composite)", sea)
        cbar(fig, m, axes[0, 0], u)
        m = pmap(axes[0, 1], e, cm_, VAR_CMAP.get(v, SEQ), vn, f"Climatology median\n{clim.attrs['baseline']}", sea)
        cbar(fig, m, axes[0, 1], u)
        sdv = c["sd"].values
        top = np.nanpercentile(sdv[sea], 98) if np.isfinite(sdv[sea]).any() else 1
        m = pmap(axes[0, 2], e, sdv, SEQ, Normalize(0, top), "Climatology robust SD\n", sea)
        cbar(fig, m, axes[0, 2], "log10 units (1.4826·MAD)" if logv else u)
        m = pmap(axes[0, 3], e, sgn * e["dx"].values, DIV, Normalize(-DX_LIM, DX_LIM), f"Anomaly {EV}\n(a − b, log10)", sea)
        dx_cbar(fig, m, axes[0, 3], sgn)
        sig_contour(axes[0, 3], e, g["patch"].values > 0)

        lm, _ = linear(v, local_median(e["med"].values))
        m = pmap(axes[1, 0], e, lm, VAR_CMAP.get(v, SEQ), vn, "3×3 local median of (a)\n× = days flagged as outliers", sea)
        cbar(fig, m, axes[1, 0], u)
        nf = e["nflag"].values
        yy, xx = np.nonzero((nf > 0) & sea)
        if 0 < len(yy) <= 20000:   # markers only where they stay readable
            s = 6 + 30 * nf[yy, xx] / max(nf.max(), 1)
            axes[1, 0].scatter(e[LON].values[xx], e[LAT].values[yy], s=s, marker="x", c=ORANGE, lw=0.8, zorder=4)
        pv = e["p_a1"].values
        m = pmap(axes[1, 1], e, sig_class(g["sig"].values, pv), PCMAP, PNORM, "Significance, A1 one-sided\n"
                 "autocorr.-corrected, FDR q ≤ 0.10", sea)
        p_cbar(fig, m, axes[1, 1])
        n = e["n"].values.astype(float)
        m = pmap(axes[1, 2], e, np.where(n > 0, n, np.nan), SEQ, Normalize(0, max(np.nanmax(n), 1)),
                 f"Observations in {EV}\n(days with data)", sea)
        cbar(fig, m, axes[1, 2], "count")
        nb = c["n"].values.astype(float)
        m = pmap(axes[1, 3], e, np.where(nb > 0, nb, np.nan), SEQ, Normalize(0, max(np.nanmax(nb), 1)),
                 "Baseline support N\n(hatched = insufficient)", sea)
        cbar(fig, m, axes[1, 3], "count")
        ins = (c["sufficient"].values == 0) & sea
        if ins.any():
            lo, la, insd = coarsen(e[LON].values, e[LAT].values, ins.astype(float))
            axes[1, 3].contourf(lo, la, insd, levels=[0.5, 1.5], colors="none", hatches=["////"], zorder=2)
        ny = c["nyears"].values[sea]
        axes[1, 3].text(0.02, 0.02, f"years with data: median {np.median(ny):.0f} (min {ny.min()}) of "
                        f"{len(config.BASELINE[p])}", transform=axes[1, 3].transAxes, fontsize=6.5, color=MUTED, zorder=6)
        sig, tested = int(g["sig"].values[sea].sum()), int(np.isfinite(pv[sea]).sum())
        npatch = int(g["patch"].values[sea].sum())
        fig.suptitle(f"{NICE[v]}, {PNAME[p]}, bin {b} = {bin_dates(b)} ({bins.attrs['bin_kind']}), {EV} vs baseline "
                     f"{clim.attrs['baseline']}  ·  significant (FDR q ≤ 0.10) in {sig}/{tested} tested pixels; patch {npatch} "
                     "(outline in d: also ≥ ×1.5, objects < 1 km² removed)",
                     x=0.01, ha="left", fontsize=10, color=INK)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        save(fig, f"bin_{p}_{v}_{b}.png", GROUP[v])


# ---------------------------------------------------------------- 3. time series at points (only 3x3 cells read)
def points_in_domain():
    pts = dict(config.TS_POINTS)
    kl = pd.read_csv(ROOT / "background_data" / "infrastructure" / "key_locations.csv")
    for _, r in kl[kl["type"] == "desalination"].iterrows():
        if d["lat0"] <= r.lat <= d["lat1"] and d["lon0"] <= r.lon <= d["lon1"]:
            pts[r["name"]] = (r.lon, r.lat)
    return {k: v for k, v in pts.items() if d["lat0"] <= v[1] <= d["lat1"] and d["lon0"] <= v[0] <= d["lon1"]}


def box_series(daily, v, lon, lat):
    j = int(np.abs(daily[LON].values - lon).argmin())
    i = int(np.abs(daily[LAT].values - lat).argmin())
    sub = daily[v].isel({LAT: slice(max(i - 1, 0), i + 2), LON: slice(max(j - 1, 0), j + 2)}).values
    w = quiet()
    out = np.nanmedian(sub.reshape(sub.shape[0], -1), 1)
    w.__exit__(None, None, None)
    return out


def fig_timeseries(p, v):
    pts = points_in_domain()
    if not pts:
        print(f"   (no time-series points inside domain '{config.DOMAIN_NAME}')")
        return
    daily = opened(p, "daily")
    clim_baseline = opened(p, f"{v}_clim").attrs["baseline"]
    t = pd.DatetimeIndex(daily["time"].values)
    doy = np.array([(x - pd.Timestamp(x.year, *config.SEASON["start"])).days for x in t])
    base = np.isin(t.year, config.BASELINE[p])
    bv = daily["bin"].values
    blist = list(dict.fromkeys(bv))
    fig, axes = plt.subplots(len(pts), 1, figsize=(10, 2.6 * len(pts)), squeeze=False)
    for ax, (name, (lo, la)) in zip(axes[:, 0], pts.items()):
        val, logv = linear(v, box_series(daily, v, lo, la))
        for b in blist:
            sel = bv == b
            pool = val[sel & base]
            pool = pool[np.isfinite(pool)]
            days = doy[sel]
            if not len(days) or not len(pool):
                continue
            x0, x1 = days.min() - 0.5, days.max() + 0.5
            ax.fill_between([x0, x1], *np.percentile(pool, [0, 100]), color=GRAY, alpha=0.12, lw=0, zorder=1)
            ax.fill_between([x0, x1], *np.percentile(pool, [10, 90]), color=GRAY, alpha=0.30, lw=0, zorder=2)
            ax.plot([x0, x1], [np.median(pool)] * 2, color=MUTED, lw=1.5, zorder=3)
        ev = t.year == EV
        ax.plot(doy[ev], val[ev], "-", color=BLUE, lw=0.8, alpha=0.5, zorder=4)
        ax.plot(doy[ev], val[ev], "o", ms=3.5, color=BLUE, mec="white", mew=0.5, zorder=5)
        if logv:
            ax.set_yscale("log")
        ax.set_ylabel(f"{v} ({units_of(daily, v)})")
        ax.set_title(f"{name}  ({la:.3f}°N, {lo:.3f}°E; 3×3 pixel median)", loc="left")
        ticks = [(pd.Timestamp(2001, m, 1) - pd.Timestamp(2001, *config.SEASON["start"])).days for m in range(7, 11)]
        ax.set_xticks(ticks, ["1 Jul", "1 Aug", "1 Sep", "1 Oct"])
        ax.grid(axis="y", color=GRID, lw=0.4)
        ax.set_xlim(-1, doy.max() + 1)
    axes[0, 0].legend(handles=[Patch(color=GRAY, alpha=0.3, label="baseline P10–P90 per bin"),
                               Patch(color=GRAY, alpha=0.12, label="baseline min–max"),
                               plt.Line2D([], [], color=MUTED, lw=1.5, label="baseline median"),
                               plt.Line2D([], [], color=BLUE, marker="o", lw=0.8, label=f"{EV} daily")],
                      loc="upper left", fontsize=7, frameon=False, ncol=4)
    fig.suptitle(f"{NICE[v]}, {PNAME[p]}: {EV} against baseline {clim_baseline} ({daily.attrs['bin_kind']} bins), "
                 f"{SEASON_TXT}",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, f"timeseries_{p}_{v}.png", GROUP[v])


# ---------------------------------------------------------------- 4. chl vs CDOM
def fig_chl_vs_cdom():
    sets = [("olci300", "chl"), ("cdom300", "adg443"), ("cdom300", "aph443")]
    data = {k: load(*k) for k in sets}
    bins0, _, ab0 = data[sets[0]]
    sea = sea_mask(bins0)
    blist = [b for b in ab0["bin"].values if has_year(ab0, b)]
    fig, axes = plt.subplots(len(blist), 4, figsize=(11, 2.4 * len(blist) + 0.8), squeeze=False)
    cls_cmap = ListedColormap(["#ecebe7", BLUE, ORANGE, AQUA])
    cls_norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4)
    m = None
    for r, b in enumerate(blist):
        dxs = {}
        for c, (p, v) in enumerate(sets):
            ab = data[(p, v)][2]
            dxs[v] = signal_of(p, v) * ab["dx"].sel(year=EV, bin=b).values
            m = pmap(axes[r, c], ab0, dxs[v], DIV, Normalize(-DX_LIM, DX_LIM), f"{bin_dates(b)}  {v}  anomaly", sea)
        hc, hd = dxs["chl"] >= config.EFFECT_MIN, dxs["adg443"] >= config.EFFECT_MIN
        cls = np.where(hc & hd, 3, np.where(hd, 2, np.where(hc, 1, 0))).astype(float)
        cls[~(np.isfinite(dxs["chl"]) & np.isfinite(dxs["adg443"]))] = np.nan
        pmap(axes[r, 3], ab0, cls, cls_cmap, cls_norm, f"{bin_dates(b)}  elevated (≥ ×{10 ** config.EFFECT_MIN:.1f})", sea)
    if m is not None:
        dx_cbar(fig, m, axes, location="top", orientation="horizontal", shrink=0.5, fraction=0.012, pad=0.015)
    fig.legend(handles=[Patch(color=BLUE, label="chl only"), Patch(color=ORANGE, label="CDOM (a_dg443) only"),
                        Patch(color=AQUA, label="both"), Patch(color="#ecebe7", label="neither"),
                        Patch(facecolor=NODATA, edgecolor=MUTED, label="no data in one of them")],
               loc="lower center", ncol=5, fontsize=7.5, frameon=False, bbox_to_anchor=(0.45, -0.01))
    fig.suptitle(f"Chlorophyll versus organic matter, {EV} bin-median anomalies (300 m)  ·  "
                 "a_ph443 shown for the phytoplankton share of absorption", x=0.01, ha="left", fontsize=10, color=INK)
    save(fig, "chl_vs_cdom.png", COMBINED)


# ---------------------------------------------------------------- 5. HR vs 300 m (monthly median daily anomaly, per tile)
def monthly_dx(p, v):
    """{month: 2-D map} of the median daily anomaly of EV in each month, computed tile by tile."""
    parts = {}
    for t in tiles_of(p):
        with xr.open_dataset(T.tile_path(p, f"{v}_anom_daily", t["k"])) as ad:
            tt = pd.DatetimeIndex(ad["time"].values)
            for mth in range(config.SEASON["start"][0], config.SEASON["end"][0] + 1):
                sel = (tt.year == EV) & (tt.month == mth)
                if sel.any():
                    w = quiet()
                    med = np.nanmedian(ad["dx"].values[sel], 0)
                    w.__exit__(None, None, None)
                    parts.setdefault(mth, []).append(xr.DataArray(med, coords={LAT: ad[LAT], LON: ad[LON]}, dims=(LAT, LON)))
    return {m: xr.combine_by_coords([a.to_dataset(name="dx") for a in arrs])["dx"] for m, arrs in parts.items()}


def fig_hr_vs_300():
    sets = [("olci300", "chl"), ("hr", "chl"), ("hr", "tur")]
    res = {k: monthly_dx(*k) for k in sets}
    masks = {p: opened(p, "bins") for p in ("olci300", "hr")}
    months = sorted(set().union(*[set(r) for r in res.values()]))
    fig, axes = plt.subplots(len(months), 3, figsize=(10, 2.6 * len(months) + 0.6), squeeze=False)
    m = None
    for r, mth in enumerate(months):
        for c, (p, v) in enumerate(sets):
            ds = masks[p]
            a = res[(p, v)].get(mth)
            arr = a.transpose(LAT, LON).values if a is not None else np.full((ds.sizes[LAT], ds.sizes[LON]), np.nan)
            m = pmap(axes[r, c], ds, arr, DIV, Normalize(-DX_LIM, DX_LIM),
                     f"{bin_dates(f'{mth:02d}')}  {PNAME[p]}  {v}", sea_mask(ds))
    if m is not None:
        dx_cbar(fig, m, axes, location="top", orientation="horizontal", shrink=0.6, fraction=0.03, pad=0.04)
    fig.suptitle(f"{EV}: median of daily anomalies per month (each product against its own baseline: "
                 f"300 m {config.BASELINE['olci300'][0]}–{config.BASELINE['olci300'][-1]}, "
                 f"HR {config.BASELINE['hr'][0]}–{config.BASELINE['hr'][-1]})", x=0.01, ha="left", fontsize=10, color=INK)
    save(fig, "hr_vs_300m.png", COMBINED)


# ---------------------------------------------------------------- 6. distributions per bin and year (sampled pixels)
def fig_distributions(p, v, max_pixels):
    idx, step, n_sea = sample_index(p, max_pixels)
    kind = T.read_meta(p)["bin_kind"]
    groups, units = {}, ""
    for t in tiles_of(p):
        if not len(idx[t["k"]]):
            continue
        with xr.open_dataset(T.tile_path(p, "daily", t["k"])) as ds:
            x = ds[v].values.reshape(ds.sizes["time"], -1)[:, idx[t["k"]]]
            yv = ds["year"].values
            bv = T.attach_bins(ds[["year"]], kind)["bin"].values
            units = ds[v].attrs.get("units", "")
        for y in np.unique(yv):
            for b in np.unique(bv):
                vals = x[(yv == y) & (bv == b)].ravel()
                groups.setdefault((b, int(y)), []).append(vals[np.isfinite(vals)])
    blist = sorted({b for b, _ in groups})
    years = sorted({y for _, y in groups})
    nc = 4 if len(blist) > 4 else len(blist)
    nr = int(np.ceil(len(blist) / nc))
    fig, axes = plt.subplots(nr, nc, figsize=(3.1 * nc, 2.4 * nr + 0.5), squeeze=False, sharey=True)
    for k, ax in enumerate(axes.flat):
        if k >= len(blist):
            ax.set_visible(False)
            continue
        b = blist[k]
        data = [np.concatenate(groups.get((b, y), [np.array([])])) for y in years]
        pos = [i for i, g in enumerate(data) if len(g)]
        if pos:
            bp = ax.boxplot([data[i] for i in pos], positions=pos, widths=0.6, whis=(5, 95), showfliers=False,
                            patch_artist=True, medianprops=dict(color=INK, lw=1))
            for i, patch in zip(pos, bp["boxes"]):
                patch.set(facecolor=BLUE if years[i] == EV else "#dddcd7", edgecolor=MUTED, lw=0.5)
        ax.set_xticks(range(len(years)), [str(y)[2:] for y in years], fontsize=6.5)
        ax.set_title(f"{b}: {bin_dates(b)}", loc="left")
        ax.grid(axis="y", color=GRID, lw=0.4)
        if k % nc == 0:
            ax.set_ylabel(units)
    sample = "all sea pixels" if step == 1 else f"a sample of 1 in {step} sea pixels ({int(np.ceil(n_sea / step)):,} of {n_sea:,})"
    fig.suptitle(f"{NICE[v]}, {PNAME[p]}: valid pixel-days per year and bin, {sample} "
                 f"(box P25–P75, whiskers P5–P95; {EV} in blue)", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, f"distributions_{p}_{v}.png", GROUP[v])


# ---------------------------------------------------------------- 7. coverage (exact counts, per tile)
def coverage_table(p, v):
    kind = T.read_meta(p)["bin_kind"]
    valid, total = None, None
    for t in tiles_of(p):
        with xr.open_dataset(T.tile_path(p, "daily", t["k"])) as ds:
            sea = sea_mask(ds)
            x = ds[v].values[:, sea]
            df = pd.DataFrame({"year": ds["year"].values, "bin": T.attach_bins(ds[["year"]], kind)["bin"].values,
                               "valid": np.isfinite(x).sum(1), "total": np.full(len(x), sea.sum())})
        g = df.groupby(["bin", "year"])[["valid", "total"]].sum()
        valid = g["valid"] if valid is None else valid.add(g["valid"], fill_value=0)
        total = g["total"] if total is None else total.add(g["total"], fill_value=0)
    return (100 * valid / total).unstack("year")


def fig_coverage():
    sets = [("olci300", "chl"), ("cdom300", "adg443"), ("hr", "chl")]
    fig, axes = plt.subplots(1, len(sets), figsize=(13, 3.4), squeeze=False)
    for ax, (p, v) in zip(axes[0], sets):
        frac = coverage_table(p, v)
        blist = list(frac.index)
        basecols = [y for y in frac.columns if y in config.BASELINE[p]]
        for y in basecols:
            ax.plot(range(len(blist)), frac[y], color=GRAY, lw=0.6, alpha=0.6)
        ax.plot(range(len(blist)), frac[basecols].median(axis=1), color=MUTED, lw=2, label="baseline median")
        if EV in frac:
            ax.plot(range(len(blist)), frac[EV], color=BLUE, lw=2, marker="o", ms=4, label=str(EV))
        ax.set_xticks(range(len(blist)), [bin_dates(b) for b in blist], rotation=90 if len(blist) > 6 else 0, fontsize=6.5)
        ax.set_ylim(0, 100)
        ax.set_title(f"{PNAME[p]}  {v}", loc="left")
        ax.grid(axis="y", color=GRID, lw=0.4)
    axes[0, 0].set_ylabel("valid pixel-days at sea (%)")
    axes[0, 0].legend(fontsize=7, frameon=False, loc="upper right")
    fig.suptitle(f"Coverage per calendar bin, {SEASON_TXT}: thin gray = individual baseline years (coverage-bias check, Part 3 step 5)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "coverage.png", COMBINED)


# ---------------------------------------------------------------- 8. QI vs our z (sampled pixels)
def fig_qi(max_pixels):
    idx, step, n_sea = sample_index("olci300", max_pixels)
    qs, zs = [], []
    for t in tiles_of("olci300"):
        if not len(idx[t["k"]]):
            continue
        with xr.open_dataset(T.tile_path("olci300", "daily", t["k"])) as ds, \
                xr.open_dataset(T.tile_path("olci300", "chl_anom_daily", t["k"])) as ad:
            if "QI_CHL" not in ds:
                return
            qs.append(ds["QI_CHL"].values.reshape(ds.sizes["time"], -1)[:, idx[t["k"]]].ravel())
            zs.append(ad["z"].values.reshape(ad.sizes["time"], -1)[:, idx[t["k"]]].ravel())
    q, z = np.concatenate(qs), np.concatenate(zs)
    ok = np.isfinite(q) & np.isfinite(z)
    q, z = q[ok], z[ok]
    rho = stats.spearmanr(q, z).statistic
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    hb = ax.hexbin(z, q, gridsize=60, cmap=SEQ, mincnt=1, bins="log", extent=(-6, 8, -6, 16))
    ax.axline((0, 0), slope=1, color=MUTED, lw=0.8, ls="--")
    ax.axhline(0, color=GRID, lw=0.5)
    ax.axvline(0, color=GRID, lw=0.5)
    cbar(fig, hb, ax, "pixel-days (log)")
    ax.set_xlabel("our robust z (baseline 2016–2025, 10-day bin, leave-one-year-out)")
    ax.set_ylabel("provider QI_CHL")
    sample = "" if step == 1 else f", 1 in {step} sea pixels"
    ax.set_title(f"300 m chl, {SEASON_TXT}, all years: provider anomaly score vs ours\nSpearman ρ = {rho:.2f}, n = {ok.sum():,}{sample}", loc="left")
    save(fig, "qi_vs_z.png", GROUP["chl"])


# ---------------------------------------------------------------- 9-10. whole-season climatology and anomaly
SEASON_SET = [("olci300", "chl"), ("cdom300", "adg443"), ("hr", "tur")]   # user 2026-10-23: chl, CDOM, turbidity


def season_data():
    out = {}
    for p, v in SEASON_SET:
        ss = opened(p, f"{v}_season").load()
        bins = opened(p, "bins")
        out[(p, v)] = (ss, sea_mask(bins), units_of(bins, v))
    return out


def fig_season_climatology():
    data = season_data()
    fig, axes = plt.subplots(1, len(SEASON_SET), figsize=(5.2 * len(SEASON_SET), 4.8), squeeze=False)
    for ax, (p, v) in zip(axes[0], SEASON_SET):
        ss, sea, u = data[(p, v)]
        val, _ = linear(v, ss["clim_med"].values)
        m = pmap(ax, ss, val, VAR_CMAP.get(v, SEQ), norm_for(v, val[sea]), f"{NICE[v]}, {PNAME[p]}\nbaseline {ss.attrs['baseline']}", sea)
        cbar(fig, m, ax, f"season median ({u})")
    fig.suptitle(f"Climatology of the whole season ({SEASON_TXT}): median of all valid baseline daily values per pixel",
                 x=0.01, ha="left", fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "season_climatology.png", COMBINED)


def fig_season_anomaly():
    data = season_data()
    n = len(SEASON_SET)
    fig, axes = plt.subplots(2, n, figsize=(5.2 * n, 9.0), squeeze=False)
    for c, (p, v) in enumerate(SEASON_SET):
        ss, sea, u = data[(p, v)]
        sgn = signal_of(p, v)
        g = significance(p, v)
        m = pmap(axes[0, c], ss, sgn * ss["dx_med"].values, DIV, Normalize(-DX_LIM, DX_LIM),
                 f"{NICE[v]}, {PNAME[p]}\n{EV} median daily anomaly vs {ss.attrs['baseline']}", sea)
        dx_cbar(fig, m, axes[0, c], sgn)
        sig_contour(axes[0, c], ss, g["patch_season"].values > 0)
        pv = ss["p_season"].values
        m = pmap(axes[1, c], ss, sig_class(g["sig_season"].values, pv), PCMAP, PNORM,
                 f"{NICE[v]}: {EV} > baseline?\nsignificant in {int(g['sig_season'].values[sea].sum())} of "
                 f"{int(np.isfinite(pv[sea]).sum())} tested pixels", sea)
        p_cbar(fig, m, axes[1, c])
    fig.suptitle(f"Whole-season anomaly {EV} ({SEASON_TXT}): each day against its own calendar-bin climatology, median over the season; "
                 "one-sided Mann-Whitney test of the daily anomalies, autocorr.-corrected, FDR q ≤ 0.10; outline = patch",
                 x=0.01, ha="left", fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "season_anomaly.png", COMBINED)


# ---------------------------------------------------------------- 11. movie: daily sliding window (anomaly | p-value)
def letter(ax, lab):
    ax.text(-0.03, 1.0, lab, transform=ax.transAxes, ha="right", va="bottom", fontsize=10, fontweight="bold", color=INK)


def fig_movie(p, v, fps):
    """mp4, one frame per day: EV window median minus baseline median (a) and the one-sided p-value (b) of the
    +-WINDOW_HALF-day window (scripts/06 output <v>_anom_window), with a timeline of the sea-median anomaly (c)."""
    try:
        wd = opened(p, f"{v}_anom_window")
    except FileNotFoundError:
        print(f"   (no {v}_anom_window output for {p}; run 06_climatology_anomaly.py first)")
        return
    import imageio_ffmpeg
    from matplotlib.animation import FFMpegWriter
    from matplotlib.cm import ScalarMappable
    plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    sea, sgn = sea_mask(opened(p, "bins")), signal_of(p, v)
    g = significance(p, v)
    times = pd.DatetimeIndex(wd["time"].values)
    w0, w1 = pd.DatetimeIndex(wd["win_start"].values), pd.DatetimeIndex(wd["win_end"].values)
    base, half = wd.attrs["baseline"], wd.attrs["half_width_days"]

    # first pass: per-frame summary for the timeline (one 2-D map in memory at a time)
    w = quiet()
    med, nsig, ntest = [], [], []
    for k in range(len(times)):
        a = sgn * wd["dx"].isel(time=k).values
        pv = wd["p"].isel(time=k).values[sea]
        med.append(np.nanmedian(a[sea]) if np.isfinite(a[sea]).any() else np.nan)
        nsig.append(int(g["sig_window"].isel(time=k).values[sea].sum()))
        ntest.append(int(np.isfinite(pv).sum()))
    w.__exit__(None, None, None)

    fig = plt.figure(figsize=(12, 6.4))   # 1800 x 960 px at dpi 150 (even sizes for H.264)
    ax_a = fig.add_axes([0.05, 0.27, 0.36, 0.58])
    cax_a = fig.add_axes([0.42, 0.32, 0.011, 0.48])
    ax_b = fig.add_axes([0.55, 0.27, 0.36, 0.58])
    cax_b = fig.add_axes([0.92, 0.32, 0.011, 0.48])
    ax_t = fig.add_axes([0.07, 0.07, 0.86, 0.12])
    dnorm = Normalize(-DX_LIM, DX_LIM)
    dx_cbar(fig, ScalarMappable(dnorm, DIV), None, sgn, cax=cax_a)
    p_cbar(fig, ScalarMappable(PNORM, PCMAP), None, cax=cax_b)
    ax_t.plot(times, med, color=BLUE, lw=1.2)
    ax_t.axhline(0, color=MUTED, lw=0.6)
    ax_t.set_ylabel("sea median\nanomaly (log10)", fontsize=6.5)
    ax_t.set_xlim(times[0] - pd.Timedelta(days=1), times[-1] + pd.Timedelta(days=1))
    ax_t.set_xticks([t for t in times if t.day in (1, 11, 21)], [dstr(t) for t in times if t.day in (1, 11, 21)],
                    fontsize=6.5)
    ax_t.grid(axis="y", color=GRID, lw=0.4)
    ax_t.set_title(f"timeline: sea-median anomaly of each window ({EV}); shaded = current window", loc="left",
                   fontsize=7.5)
    letter(ax_t, "c")
    span = ax_t.axvspan(w0[0], w1[0], color=ORANGE, alpha=0.25, lw=0)
    head = fig.text(0.01, 0.985, "", ha="left", va="top", fontsize=11, color=INK, fontweight="bold")
    sub = fig.text(0.01, 0.945, f"{NICE[v]}, {PNAME[p]}, domain '{config.DOMAIN_NAME}': {EV} vs baseline {base} on the "
                   f"same calendar days; window = centre ± {half} days, clipped to the season and to the last {EV} date; "
                   "one-sided Mann-Whitney, autocorr.-corrected, FDR q ≤ 0.10; outline in (a) = patch (also ≥ ×1.5, objects < 1 km² removed)", ha="left", va="top", fontsize=7.5, color=MUTED)
    out = OUT / GROUP[v] / f"movie_{p}_{v}_window{2 * half + 1}d.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = FFMpegWriter(fps=fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p"],
                          metadata=dict(title=f"{NICE[v]} {EV} sliding-window anomaly and p-value"))
    with writer.saving(fig, str(out), dpi=150):
        for k, c in enumerate(times):
            rng = f"{dstr(w0[k])}–{dstr(w1[k])} {EV}"
            ndays = (w1[k] - w0[k]).days + 1
            head.set_text(f"Window {rng}  ({ndays} days{', clipped' if ndays < 2 * half + 1 else ''}; "
                          f"centre {dstr(c)})")
            a = sgn * wd["dx"].isel(time=k).values
            pv = wd["p"].isel(time=k).values
            for ax in (ax_a, ax_b):
                ax.clear()
            pmap(ax_a, wd, a, DIV, dnorm, f"Anomaly, {rng}\n{EV} window median − baseline median", sea)
            sig_contour(ax_a, wd, g["patch_window"].isel(time=k).values > 0)
            pmap(ax_b, wd, sig_class(g["sig_window"].isel(time=k).values, pv), PCMAP, PNORM,
                 f"Significance, {rng}\nsignificant in {nsig[k]} of {ntest[k]} tested pixels", sea)
            if not np.isfinite(a[sea]).any():
                ax_a.text(0.5, 0.5, f"no {EV} data in window", transform=ax_a.transAxes, ha="center", va="center",
                          color=MUTED, zorder=5)
            letter(ax_a, "a")
            letter(ax_b, "b")
            span.remove()
            span = ax_t.axvspan(w0[k] - pd.Timedelta(hours=12), w1[k] + pd.Timedelta(hours=12), color=ORANGE,
                                alpha=0.25, lw=0)
            writer.grab_frame()
    plt.close(fig)
    print("  ", f"{GROUP[v]}/{out.name}  ({len(times)} frames, {fps} per second)")


# ---------------------------------------------------------------- 14. onset map (Q1 land-input indicator, 2026-11-05)
def fig_onset(p, v):
    """Onset date per pixel from the daily-window patch (src/greenpatch/significance.onset): map (a), onset against
    the alongshore coordinate s (b; spreading from a source shows as a slope), share of sea pixels in the patch (c)."""
    g = significance(p, v)
    if "onset" not in g:
        print(f"   (no onset in {v}_significance.nc for {p}; rerun 06_climatology_anomaly.py --significance-only)")
        return
    bins = opened(p, "bins")
    sea = sea_mask(bins)
    on = pd.DatetimeIndex(g["onset"].values.ravel())
    t0 = pd.Timestamp(f"{EV}-07-01")
    days = np.where(on.notna(), (on - t0).days, np.nan).reshape(sea.shape)
    days = np.where(sea, days, np.nan)
    ok = np.isfinite(days)
    if not ok.any():
        print(f"   ({p} {v}: no pixel reaches the onset rule)")
        return
    lo, hi = np.nanmin(days), np.nanmax(days)
    norm = Normalize(lo, max(hi, lo + 1))
    fig = plt.figure(figsize=(13, 4.8))
    ax_a = fig.add_axes([0.04, 0.12, 0.33, 0.72])
    ax_b = fig.add_axes([0.47, 0.12, 0.23, 0.72])
    ax_c = fig.add_axes([0.76, 0.12, 0.22, 0.72])
    cmap = plt.get_cmap("viridis")
    m = pmap(ax_a, g, days, cmap, norm, f"onset date, {EV}\nnever in the patch: grey", sea)
    never = np.where(sea & ~ok, 1.0, np.nan)
    lon, lat, nv = coarsen(g[LON].values, g[LAT].values, never)
    ax_a.pcolormesh(lon, lat, np.ma.masked_invalid(nv), cmap=ListedColormap([GRAY]), shading="nearest", zorder=2)
    ticks = np.linspace(lo, max(hi, lo + 1), 5)
    cb = fig.colorbar(m, ax=ax_a, fraction=0.04, pad=0.02, ticks=ticks)
    cb.ax.set_yticklabels([dstr(t0 + pd.Timedelta(days=float(d))) for d in ticks], fontsize=6.5)
    s = bins["s_km"].values
    ax_b.scatter(days[ok], s[ok], s=4, color=BLUE, alpha=0.5, lw=0)
    ax_b.set_xlabel(f"onset (days after 1 Jul {EV})")
    ax_b.set_ylabel("alongshore s (km from Damietta, north positive)")
    ax_b.set_title("onset along the coast", loc="left")
    ax_b.grid(color=GRID, lw=0.4)
    times = pd.DatetimeIndex(g["time"].values)
    share = [(g["patch_window"].isel(time=k).values > 0)[sea].mean() for k in range(len(times))]
    ax_c.plot(times, np.array(share) * 100, color=BLUE, lw=1.2)
    ax_c.set_ylabel("sea pixels in the patch (%)")
    ax_c.set_title("patch extent per day", loc="left")
    ax_c.set_xticks([t for t in times if t.day == 1], [dstr(t) for t in times if t.day == 1], fontsize=6.5)
    ax_c.grid(color=GRID, lw=0.4)
    fig.suptitle(f"{NICE[v]}, {PNAME[p]}: onset of the patch = first window centre (± {config.WINDOW_HALF} days) that starts "
                 f"≥ {g.attrs.get('onset_persist_days', '?')} consecutive patch days; {int(ok.sum())} of {int(sea.sum())} sea pixels",
                 x=0.01, ha="left", fontsize=10, color=INK)
    save(fig, f"onset_{p}_{v}.png", GROUP[v])


# ---------------------------------------------------------------- 15. co-location of land-input indicators (2026-11-05)
COLOC = [("cdom300", "adg443"), ("cdom300", "aph443"), ("cdom300", "r412_443"), ("hr", "tur")]


def to_grid(src, dst_lon, dst_lat, a):
    """Median of a finer field `a` (on src lon/lat) within each cell of the destination grid (cell centres given)."""
    edges = lambda c: np.concatenate([[c[0] - (c[1] - c[0]) / 2], (c[1:] + c[:-1]) / 2, [c[-1] + (c[-1] - c[-2]) / 2]])  # noqa: E731
    ex, ey = edges(dst_lon), edges(dst_lat)
    assert ex[1] > ex[0] and ey[1] > ey[0], "to_grid expects ascending coordinates"
    ix = np.searchsorted(ex, src[LON].values) - 1
    iy = np.searchsorted(ey, src[LAT].values) - 1
    out = np.full((len(dst_lat), len(dst_lon)), np.nan)
    df = pd.DataFrame({"y": np.repeat(iy, len(ix)), "x": np.tile(ix, len(iy)), "v": np.asarray(a, float).ravel()}).dropna()
    df = df[(df.x >= 0) & (df.x < len(dst_lon)) & (df.y >= 0) & (df.y < len(dst_lat))]
    for (y, x), v in df.groupby(["y", "x"]).v.median().items():
        out[y, x] = v
    return out


def table_colocation():
    """Per 300 m bin of the event year: median anomaly of each indicator inside and outside the 300 m chl patch, and the
    share of patch pixels where the indicator is itself significant. HR (monthly bins, ~100 m) is mapped to the 300 m
    grid (median per cell) and to every 10-day bin of its month."""
    g = significance("olci300", "chl")
    sea = sea_mask(opened("olci300", "bins"))
    lon, lat = g[LON].values, g[LAT].values
    rows = []
    for p, v in COLOC:
        try:
            ab, sg = opened(p, f"{v}_anom_bins"), significance(p, v)
        except FileNotFoundError:
            continue
        sgn = signal_of(p, v)
        for b in g["bin"].values:
            hb = b if b in ab["bin"].values else b[:2] if b[:2] in ab["bin"].values else None
            if hb is None or not has_year(ab, hb):
                continue
            dx = sgn * ab["dx"].sel(year=EV, bin=hb).values
            sig = sg["sig"].sel(year=EV, bin=hb).values.astype(float)
            if p == "hr":
                dx, sig = to_grid(ab, lon, lat, dx), to_grid(ab, lon, lat, sig)
            patch = (g["patch"].sel(year=EV, bin=b).values > 0) & sea
            out = ~patch & sea
            rows.append(dict(bin=b, dates=bin_dates(b), indicator=f"{p}:{v}", indicator_bin=hb,
                             patch_pixels=int(patch.sum()),
                             dx_in_patch=np.nanmedian(dx[patch]) if patch.any() else np.nan,
                             dx_outside=np.nanmedian(dx[out]) if out.any() else np.nan,
                             share_patch_sig=np.nanmean(sig[patch] > 0.5) if patch.any() else np.nan))
    t = pd.DataFrame(rows)
    f = config.RESULTS / "tables" / "colocation_chl_patch.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    t.round(3).to_csv(f, index=False)
    print("  ", f.relative_to(config.ROOT), f"({len(t)} rows; dx in the signal direction, log10 except Rrs412/443)")


# ---------------------------------------------------------------- 13. manuscript candidate: anomaly + p < 0.05 contour
# bins shown (user 2026-10-26: 21 Jul - 10 Oct, 2 x 4); products with other bins (HR monthly) show all their bins
PAPER_BINS = ["07-3", "08-1", "08-2", "08-3", "09-1", "09-2", "09-3", "10-1"]
CONTOUR_SMOOTH_CELLS = 300   # grids larger than this (cells per side) get a 1-cell Gaussian smoothing of the contour


def sig_contour(ax, ds, sig):
    """Outline of a mask, e.g. the patch (display grid; smoothed only on large grids, where it would be noisy)."""
    from scipy.ndimage import gaussian_filter
    lon, lat, m = coarsen(ds[LON].values, ds[LAT].values, sig.astype(float))
    m = np.nan_to_num(m)
    if max(m.shape) > CONTOUR_SMOOTH_CELLS:
        m = gaussian_filter(m, 1.0)
    if m.max() < 0.5:
        return
    # one ring of zeros around the grid, so areas touching the domain edge are closed
    pad = lambda c: np.concatenate([[2 * c[0] - c[1]], c, [2 * c[-1] - c[-2]]])  # noqa: E731
    ax.contour(pad(lon), pad(lat), np.pad(m, 1), levels=[0.5], colors=INK, linewidths=1.0, zorder=4)


def fig_paper(p, v):
    bins, clim, ab = load(p, v)
    sea, sgn = sea_mask(bins), signal_of(p, v)
    sg = significance(p, v)
    blist = [b for b in ab["bin"].values if has_year(ab, b)]
    if set(PAPER_BINS) <= set(ab["bin"].values):
        blist = list(PAPER_BINS)
    nc = 4 if len(blist) in (4, 8) else min(5, len(blist))
    nr = int(np.ceil(len(blist) / nc))
    fig, axes = plt.subplots(nr, nc, figsize=(2.3 * nc + 1, 2.45 * nr + 0.7), squeeze=False)
    norm, m = Normalize(-DX_LIM, DX_LIM), None
    for k, ax in enumerate(axes.flat):
        if k >= len(blist):
            ax.set_visible(False)
            continue
        b = blist[k]
        e = ab.sel(year=EV, bin=b)
        a = sgn * e["dx"].values
        pv = e["p_a1"].values
        sig = (sg["patch"].sel(year=EV, bin=b).values > 0) & sea
        m = pmap(ax, ab, a, DIV, norm, f"{bin_dates(b)} {EV}", sea)
        sig_contour(ax, ab, sig)
        ax.text(0.02, 0.02, f"patch: {100 * sig.sum() / max(np.isfinite(pv[sea]).sum(), 1):.0f}%",
                transform=ax.transAxes, fontsize=6.5, color=INK, zorder=6,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1))
        if k % nc:
            ax.set_yticklabels([])
        if k < len(blist) - nc:
            ax.set_xticklabels([])
    if m is not None:
        dx_cbar(fig, m, axes, sgn)
    fig.legend(handles=[plt.Line2D([], [], color=INK, lw=1.0, label="patch: significant (FDR q ≤ 0.10; one-sided Mann-Whitney with "
                                                                       "effective n for autocorrelation), ≥ ×1.5 above "
                                                                       "the baseline median, objects < 1 km² removed")],
               loc="lower left", fontsize=7.5, frameon=False, bbox_to_anchor=(0.01, -0.01))
    fig.suptitle(f"{NICE[v]}, {PNAME[p]}: {EV} anomaly per {bins.attrs['bin_kind']} bin (bin median minus baseline "
                 f"{clim.attrs['baseline']} median)", x=0.01, ha="left", fontsize=10, color=INK)
    save(fig, f"paper_{p}_{v}.png", GROUP[v])


# ---------------------------------------------------------------- 12. autocorrelation of the daily anomalies
def fig_autocorrelation():
    sets = [(p, s["out"]) for p in config.SATELLITE_PRODUCTS for s in config.PREPROC[p]["vars"].values()]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), squeeze=False, sharey=True)
    for ax, prod in zip(axes[0], config.SATELLITE_PRODUCTS):
        for i, (p, v) in enumerate(s for s in sets if s[0] == prod):
            ss = opened(p, f"{v}_season")
            sea = sea_mask(opened(p, "bins"))
            acf = ss["acf"].values[:, sea]
            raw = ss["acf_raw"].values[:, sea]
            lag = ss["lag"].values
            col = [BLUE, ORANGE, AQUA][i]
            ax.fill_between(lag, *np.percentile(acf, [10, 90], axis=1), color=col, alpha=0.15, lw=0)
            ax.plot(lag, np.median(acf, 1), color=col, lw=1.6, label=v)
            own = np.isfinite(raw).mean(1) < 0.5   # lags taken mostly from the tile-pooled or interpolated value
            ax.plot(lag[own], np.median(acf, 1)[own], "o", ms=3, mfc="white", mec=col, mew=0.8)
        ax.set_title(f"{PNAME[prod]}  (baseline {config.BASELINE[prod][0]}–{config.BASELINE[prod][-1]}, {SEASON_TXT})",
                     loc="left")
        ax.set_xlabel("lag (days)")
        ax.axhline(0, color=MUTED, lw=0.6)
        ax.grid(axis="y", color=GRID, lw=0.4)
        ax.legend(fontsize=7, frameon=False)
    axes[0, 0].set_ylabel("autocorrelation of daily anomalies")
    fig.suptitle("Autocorrelation of the baseline daily anomalies (median over sea pixels, band P10–P90; open circles = "
                 "lags taken mostly from the tile-pooled or interpolated value). Used for the effective sample sizes.",
                 x=0.01, ha="left", fontsize=9.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "autocorrelation.png", COMBINED)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-vars", action="store_true", help="bin pages and time series for every variable")
    ap.add_argument("--movie-only", action="store_true", help="only the sliding-window movie(s) (config.WINDOW_VARS)")
    ap.add_argument("--fps", type=int, default=MOVIE_FPS, help=f"movie frames (days) per second (default {MOVIE_FPS})")
    ap.add_argument("--max-pixels", type=int, default=MAX_PIXELS,
                    help=f"sea pixels sampled for the distribution and QI figures (default {MAX_PIXELS})")
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe(), "->", OUT)
    for p, v in config.WINDOW_VARS:
        fig_movie(p, v, a.fps)
        fig_onset(p, v)
    if a.movie_only:
        return
    allv = [(p, s["out"]) for p in config.SATELLITE_PRODUCTS for s in config.PREPROC[p]["vars"].values()]
    for p, v in allv:
        fig_overview(p, v)
        fig_paper(p, v)
        fig_distributions(p, v, a.max_pixels)
    for p, v in (allv if a.all_vars else MAIN):
        fig_bin_pages(p, v)
        fig_timeseries(p, v)
    fig_chl_vs_cdom()
    fig_hr_vs_300()
    fig_coverage()
    fig_qi(a.max_pixels)
    fig_season_climatology()
    fig_season_anomaly()
    fig_autocorrelation()
    table_colocation()


if __name__ == "__main__":
    main()
