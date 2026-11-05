"""Stage 1 steps 9-10 in spatial tiles: baseline climatology, anomalies, per-pixel A1 p-values, whole-season
statistics, image-usage audit; then, product-wide, Method A steps 4-6 (FDR, effect size, small-object removal).

Inputs: data/processed/<domain>/<product>/daily_t*.nc, bins_t*.nc, meta.json (scripts/05_preprocess.py);
        data/interim/<domain>/availability_<product>.csv (scripts/01_inventory.py) for the audit.
Outputs per product, variable and tile (data/processed/<domain>/<product>/)
  <var>_clim_t<NNNN>.nc        ref x bin x pixel: median, robust SD, P90, P95, max, N, years, sufficiency
  <var>_anom_daily_t<NNNN>.nc  per observation: dx, z, percentile, exceedances
  <var>_anom_bins_t<NNNN>.nc   per year x bin: composite dx, z, A1 p-value (autocorrelation-corrected and
                               uncorrected), counts
  <var>_season_t<NNNN>.nc      whole season: climatology median/SD, median 2026 daily anomaly, p-value, autocorrelation
                               function of the baseline daily anomalies (lags 0-30 days)
  <var>_anom_window_t<NNNN>.nc daily sliding window (+-config.WINDOW_HALF days) for config.WINDOW_VARS: 2026 window
                               median minus baseline median, p-value (A1 test), counts (for the chlorophyll movie)
Product-wide output (after all tiles; src/greenpatch/significance.py)
  <var>_significance.nc        per year x bin (and season, movie window): BH q-value over the whole domain,
                               significant (q <= 0.10), elevated (>= x1.5), patch (both, objects < 1 km2 removed)
and results/<domain>/tables/image_usage.csv (every inventoried image and what it entered; errors reported).

Usage (from the project root)
  .venv/Scripts/python scripts/06_climatology_anomaly.py
  .venv/Scripts/python scripts/06_climatology_anomaly.py --workers 8
  .venv/Scripts/python scripts/06_climatology_anomaly.py --products hr --tile 12    # one batch job
  .venv/Scripts/python scripts/06_climatology_anomaly.py --significance-only        # after all tiles (batch mode)
  .venv/Scripts/python scripts/06_climatology_anomaly.py --audit-only               # after all tiles
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from greenpatch import config  # noqa: E402
from greenpatch import tiles as T  # noqa: E402
from greenpatch import significance  # noqa: E402
from greenpatch.bench import Benchmark  # noqa: E402
from greenpatch.climatology import (anomalies_bins, anomalies_daily, anomaly_acf, climatology, effect_min_of,  # noqa: E402
                                    image_usage, season_stats, usage_counts, window_stats)
from greenpatch.preprocess import save  # noqa: E402


def variables(name):
    return [s["out"] for s in config.PREPROC[name]["vars"].values()]


def run_tile(name, k):
    """All variables of one tile. Returns small summaries for the console report and the audit."""
    daily = T.load_tile(name, "daily", k)
    bins = T.load_tile(name, "bins", k)
    sea = (daily["mask_land"] + daily["mask_buffer"]).values == 0
    summ = {}
    for v in variables(name):
        with Benchmark("climatology_anomaly", f"{name}_{v}_t{k:04d}", out_path=T.tile_path(name, f"{v}_anom_daily", k),
                       n_cell_days=int(daily[v].size)):
            clim = climatology(daily, v, name)
            save(clim, T.tile_path(name, f"{v}_clim", k))
            ad = anomalies_daily(daily, v, clim, name)
            save(ad, T.tile_path(name, f"{v}_anom_daily", k))
            acf = anomaly_acf(ad, name)   # Method A step 3: effective n from the baseline autocorrelation
            ab = anomalies_bins(daily, bins, v, clim, name, acf[0])
            save(ab, T.tile_path(name, f"{v}_anom_bins", k))
            save(season_stats(daily, ad, v, name, acf=acf), T.tile_path(name, f"{v}_season", k))
            if (name, v) in config.WINDOW_VARS:
                ws = window_stats(daily, v, name, acf=acf[0])
                if ws is not None:
                    save(ws, T.tile_path(name, f"{v}_anom_window", k))
        c = clim.sel(ref="all")
        s = dict(sea_bins=int(sea.sum()) * c.sizes["bin"], sufficient=int(c["sufficient"].values[:, sea].sum()),
                 n_values=c["n"].values[:, sea].ravel().tolist() if sea.sum() * c.sizes["bin"] < 200000 else [],
                 tested=0, sig=0, baseline=clim.attrs["baseline"])
        if config.EVENT_YEAR in ab["year"].values:
            pv = ab["p_a1"].sel(year=config.EVENT_YEAR).values[:, sea]
            s.update(tested=int(np.isfinite(pv).sum()), sig=int((pv < 0.05).sum()))
        summ[v] = s
    valid, flagged = usage_counts(name, daily)
    return dict(k=k, summ=summ, valid=valid, flagged=flagged, times=daily["time"].values, bins=daily["bin"].values)


def run_significance(name):
    """Method A steps 4-6 over the whole domain (all tiles must be done)."""
    for v in variables(name):
        ds = significance.run(name, v)
        save(ds, significance.path(name, v))
        ev = config.EVENT_YEAR
        if ev in ds["year"].values:
            e = ds.sel(year=ev)
            emin = effect_min_of(name, v)
            etxt = f"x{10 ** emin:.1f}" if ds.attrs["effect_min_is_log10"] else f"{emin} {v}"
            print(f"[{name} {v}] {ev}, all bins: significant after FDR (q <= {significance.FDR_Q}) "
                  f"{int(e['sig'].sum())} pixel-bins, patch {int(e['patch'].sum())} (effect >= "
                  f"{etxt}, {int(e['removed_objects'].sum())} objects < "
                  f"{significance.MIN_AREA_KM2} km2 removed)")


def pmap(fn, jobs, workers):
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(fn, *zip(*jobs)))
    return [fn(*j) for j in jobs]


def audit(name, results):
    av = config.DATA_INTERIM / f"availability_{name}.csv"
    inv = set(pd.read_csv(av)["date"].astype(str)) if av.exists() else set()
    if not inv:
        print(f"  warning: no inventory for {name} ({av.name}); run 01_inventory.py first")
    valid = sum(r["valid"] for r in results)
    flagged = sum(r["flagged"] for r in results)
    return image_usage(name, results[0]["times"], results[0]["bins"], valid, flagged, inv)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products", nargs="+", default=config.SATELLITE_PRODUCTS, choices=list(config.PREPROC),
                    help="default: the satellite products; Q2 model output: --domain full --products medbgc medphy")
    ap.add_argument("--tile", type=int, help="process only this tile (batch job)")
    ap.add_argument("--audit-only", action="store_true", help="only rebuild image_usage.csv from the daily tiles")
    ap.add_argument("--significance-only", action="store_true",
                    help="only the product-wide FDR / effect size / small-object step (after all tiles)")
    ap.add_argument("--workers", type=int, default=1)
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe())
    usage = []
    for name in a.products:
        tl = T.read_meta(name)["tiles"]
        if a.tile is not None:
            run_tile(name, a.tile)
            print(f"[{name}] tile {a.tile} done ({len(tl)} tiles); when all are done run --significance-only, "
                  "then --audit-only")
            continue
        if a.significance_only:
            run_significance(name)
            continue
        if a.audit_only:
            res = []
            for t in tl:
                d = T.load_tile(name, "daily", t["k"])
                valid, flagged = usage_counts(name, d)
                res.append(dict(valid=valid, flagged=flagged, times=d["time"].values, bins=d["bin"].values))
        else:
            res = pmap(run_tile, [(name, t["k"]) for t in tl], a.workers)
            for v in variables(name):
                ss = [r["summ"][v] for r in res]
                nvals = sum((s["n_values"] for s in ss), [])
                msg = (f"[{name} {v}] baseline {ss[0]['baseline']}: "
                       + (f"median N per pixel-bin {np.median(nvals):.0f}, " if nvals else "")
                       + f"sufficient {100 * sum(s['sufficient'] for s in ss) / max(sum(s['sea_bins'] for s in ss), 1):.0f} % "
                       f"of sea pixel-bins; {config.EVENT_YEAR}: tested pixel-bins {sum(s['tested'] for s in ss)}, "
                       f"p < 0.05 in {sum(s['sig'] for s in ss)}")
                print(msg)
            run_significance(name)
        usage.append(audit(name, res))

    if not usage:
        return
    u = pd.concat(usage, ignore_index=True)
    out = config.RESULTS / "tables" / "image_usage.csv"
    if out.exists():   # keep the rows of products not run this time
        old = pd.read_csv(out)
        u = pd.concat([old[~old["product"].isin(u["product"].unique())], u], ignore_index=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    u.to_csv(out, index=False)
    print("\n=== Image usage (results/<domain>/tables/image_usage.csv) ===")
    print(u.groupby(["product", "status"]).size().unstack(fill_value=0).to_string())
    err = u["status"].str.startswith("ERROR")
    if err.any():
        print(f"\nERROR: {err.sum()} inventoried images entered no statistic (see image_usage.csv)")
        sys.exit(2)
    print("\nOK: every inventoried image was processed; images without valid pixels are listed, none discarded.")
    print("Next: .venv/Scripts/python scripts/07_figures_stage1.py")


if __name__ == "__main__":
    main()
