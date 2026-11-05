"""Stage 1 preprocessing, steps 3, 6, 7, 8 (guidelines/05_stage1_patch_identification.md, Part 1), in spatial tiles.

For each product and tile: mask pixels (plausible range, land + coastal buffer), log10 transform, 3x3 outlier FLAG
(values kept), coastal coordinates. Then, over the whole product: choose the bin kind (10-day or monthly fallback) and
compute calendar-bin composites per tile. Every daily field is kept (image-use rule).

Outputs (per domain and product; see src/greenpatch/tiles.py)
  data/processed/<domain>/<product>/daily_t<NNNN>.nc   daily analysis variables, flags, n_km / s_km / area_km2
  data/processed/<domain>/<product>/bins_t<NNNN>.nc    per year x bin: median, count, flagged count
  data/processed/<domain>/<product>/meta.json          tiles, bin kind and its justification, mask statistics
  results/<domain>/tables/preprocess_summary.csv       pixel counts removed / kept / flagged per variable

Usage (from the project root)
  .venv/Scripts/python scripts/05_preprocess.py                         # all products and tiles, then finalize
  .venv/Scripts/python scripts/05_preprocess.py --workers 8             # tiles in parallel
  .venv/Scripts/python scripts/05_preprocess.py --products hr --tile 12 # one tile (one batch job on a server)
  .venv/Scripts/python scripts/05_preprocess.py --products hr --finalize   # after all tiles: bin choice + composites
  .venv/Scripts/python scripts/05_preprocess.py --domain full --products medbgc medphy   # Q2 model output
Re-running a whole product clears its old tiles first.
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

from greenpatch import config  # noqa: E402
from greenpatch import tiles as T  # noqa: E402
from greenpatch.bench import Benchmark  # noqa: E402
from greenpatch.preprocess import choose_bin_kind, composites, preprocess_tile, save  # noqa: E402


def run_tile(name, tile):
    path = T.tile_path(name, "daily", tile["k"])
    with Benchmark("preprocess", f"{name}_t{tile['k']:04d}", out_path=path) as b:
        daily = preprocess_tile(name, tile)
        b.n_cell_days = int(daily.sizes["time"] * daily.sizes["latitude"] * daily.sizes["longitude"])
        save(daily, path)
    return tile["k"]


def run_composites(name, k, kind):
    daily = T.attach_bins(xr.load_dataset(T.tile_path(name, "daily", k)), kind)
    save(composites(daily, name), T.tile_path(name, "bins", k))
    return k


def pmap(fn, jobs, workers):
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(fn, *zip(*jobs)))
    return [fn(*j) for j in jobs]


def finalize(name, workers):
    """Bin choice over the whole product, composites per tile, mask statistics summed over tiles."""
    meta = T.read_meta(name)
    fails = total = 0
    stats, cells, land, buf = {}, 0, 0, 0
    for t in meta["tiles"]:
        with xr.open_dataset(T.tile_path(name, "daily", t["k"])) as ds:
            fails += int(ds.attrs["bin10_fails"])
            total += int(ds.attrs["bin10_total"])
            for var, s in json.loads(ds.attrs["mask_stats"]).items():
                acc = stats.setdefault(var, {k: 0 for k in s})
                for k_, v_ in s.items():
                    acc[k_] += v_
            cells += ds.sizes["latitude"] * ds.sizes["longitude"]
            land += int(ds["mask_land"].sum())
            buf += int(ds["mask_buffer"].sum())
            ndays = ds.sizes["time"]
            src = ds.attrs["source_files"]
    kind, why = choose_bin_kind(name, fails, total)
    T.write_meta(name, bin_kind=kind, attrs=dict(product=name, domain=config.DOMAIN_NAME, bin_kind=kind, bin_choice=why,
                                                 source_files=src),
                 mask_stats=stats, cells=cells, land_cells=land, buffer_cells=buf, days=ndays)
    pmap(run_composites, [(name, t["k"], kind) for t in meta["tiles"]], workers)
    print(f"[{name}] {ndays} days, {cells} cells in {len(meta['tiles'])} tile(s): {land} land/never valid, {buf} coastal "
          f"buffer, {cells - land - buf} analysed; bins: {kind} ({why})")
    rows = []
    for var, s in stats.items():
        pct = 100 * s["flagged"] / max(s["kept"], 1)
        print(f"   {var:9s} valid at sea {s['raw_valid']:>10,}  out of range {s['out_of_range']:>8,}  kept {s['kept']:>10,}  "
              f"flagged (kept) {s['flagged']:>8,} ({pct:.1f} %)   [in land/buffer cells: {s['in_land_or_buffer']:,}]")
        rows.append(dict(product=name, variable=var, days=ndays, cells=cells, land_cells=land, buffer_cells=buf,
                         tiles=len(meta["tiles"]), bin_kind=kind, **s, flagged_pct=round(pct, 2)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products", nargs="+", default=config.SATELLITE_PRODUCTS, choices=list(config.PREPROC),
                    help="default: the satellite products; Q2 model output: --domain full --products medbgc medphy")
    ap.add_argument("--tile", type=int, help="process only this tile (batch job); run --finalize afterwards")
    ap.add_argument("--finalize", action="store_true", help="only the product-wide step (needs all daily tiles)")
    ap.add_argument("--workers", type=int, default=1, help="tiles processed in parallel")
    ap.add_argument("--tile-size", type=int, nargs=2, metavar=("ROWS", "COLS"), help="override config.TILE (testing)")
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe())
    rows = []
    for name in a.products:
        tl = T.tile_list(name, tuple(a.tile_size) if a.tile_size else None)
        if not a.finalize:
            if a.tile is None:   # whole product: start clean
                d = T.product_dir(name)
                for f in list(d.glob("*_t[0-9][0-9][0-9][0-9].nc")) + ([T.meta_path(name)] if T.meta_path(name).exists() else []):
                    f.unlink()
            lat, lon = T.grid(name)
            T.write_meta(name, tiles=tl, grid=[len(lat), len(lon)], halo=config.TILE_HALO)
            jobs = [(name, t) for t in tl if a.tile is None or t["k"] == a.tile]
            pmap(run_tile, jobs, a.workers)
            if a.tile is not None:
                print(f"[{name}] tile {a.tile} done ({len(tl)} tiles in total); run --finalize when all are done")
                continue
        rows += finalize(name, a.workers)
    if rows:
        tables = config.RESULTS / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(tables / "preprocess_summary.csv", index=False)
        print(f"\nSummary -> {tables / 'preprocess_summary.csv'}\nNext: .venv/Scripts/python scripts/06_climatology_anomaly.py")


if __name__ == "__main__":
    main()
