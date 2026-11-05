"""Step 1 (guidelines/05_stage1_patch_identification.md): inventory and integrity of downloaded satellite data.

Outputs (<domain> = pilot or full, see config.DOMAINS)
  data/interim/<domain>/inventory_<product>.csv        one row per file / scene (size, checksum, dates, status)
  data/interim/<domain>/availability_<product>.csv     one row per product x date x sensor x tile
  results/<domain>/tables/inventory_summary.csv      per product and year: coverage, longest gap
  results/<domain>/tables/missing_dates.csv      season dates without data
  results/<domain>/figures/inventory_coverage.png      calendar of available dates per product

Usage (from the project root)
  .venv/Scripts/python scripts/01_inventory.py                      # default project folders
  .venv/Scripts/python scripts/01_inventory.py --valid-fraction     # also % valid pixels in the domain (slower)
  .venv/Scripts/python scripts/01_inventory.py --no-checksum        # skip SHA-256 (faster)
  .venv/Scripts/python scripts/01_inventory.py --raw-root X --out-root Y   # e.g. test data elsewhere

Checksums are cached: files whose path, size and modification time are unchanged since the last run
reuse the stored SHA-256.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
from greenpatch import config  # noqa: E402
from greenpatch.inventory import (availability_table, coverage, files_table,  # noqa: E402
                                  inventory_product, season_dates)

GRAY, INK, MUTED = "#eeeeee", "#222222", "#666666"


def plot_coverage(av, summary, products, years, season, out_png):
    n = len(products)
    days = season_dates(2000, season)  # leap year -> full day-of-season axis
    fig, axes = plt.subplots(n, 1, figsize=(12, 2.0 + 0.32 * len(years) * n), squeeze=False)
    cmap = plt.get_cmap("Blues")
    im = None
    for ax, (name, spec) in zip(axes[:, 0], products.items()):
        grid = np.full((len(years), len(days)), np.nan)
        sub = av[av["product"] == name] if len(av) else av
        for i, y in enumerate(years):
            sdays = season_dates(y, season)
            sy = sub[sub["date"].str.startswith(str(y))] if len(sub) else sub
            if len(sy):
                vf = sy.groupby("date")["valid_fraction"].max()
            else:
                vf = pd.Series(dtype=float)
            for j, d in enumerate(sdays):
                key = d.strftime("%Y-%m-%d")
                if key in vf.index:
                    grid[i, j] = vf[key] if np.isfinite(vf[key]) else 1.0
        has_fraction = len(sub) and sub["valid_fraction"].notna().any()
        masked = np.ma.masked_invalid(grid)
        ax.set_facecolor(GRAY)
        if has_fraction:
            im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
        else:
            ax.imshow(masked, aspect="auto", cmap=ListedColormap([cmap(0.75)]), interpolation="nearest")
        cov = summary[summary["product"] == name]
        ax.set_yticks(range(len(years)), [f"{y}  ({d:>3d} d)" for y, d in zip(years, cov["days_with_data"])],
                      fontsize=8, family="monospace")
        # 10-day bin boundaries (days 1, 11, 21 of each month), the statistical time unit
        for j, d in enumerate(days):
            if d.day in (11, 21):
                ax.axvline(j - 0.5, color="white", lw=0.6)
            elif d.day == 1 and j:
                ax.axvline(j - 0.5, color="white", lw=1.6)
        month_starts = [j for j, d in enumerate(days) if d.day == 1]
        ax.set_xticks(month_starts, [days[j].strftime("%b") for j in month_starts], fontsize=8)
        ax.set_xticks(np.arange(-0.5, len(days), 10), minor=True)
        ax.tick_params(which="both", length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(f"{spec['label']}   ·   seasons with any data: {(cov['days_with_data'] > 0).sum()}/{len(years)}"
                     f"   ·   mean coverage {cov['coverage_pct'].mean():.0f}%",
                     loc="left", fontsize=9.5, color=INK)
    fig.suptitle("Step 1 inventory: dates with data in the analysis season "
                 "(gray = no data; thin white lines = 10-day bins; (n d) = days with data)",
                 x=0.01, ha="left", fontsize=11, color=INK, weight="bold")
    fig.tight_layout(rect=(0, 0, 0.93 if im is not None else 1, 0.97))
    if im is not None:
        cax = fig.add_axes([0.945, 0.25, 0.012, 0.5])
        cb = fig.colorbar(im, cax=cax)
        cb.set_label("valid pixel fraction in domain (blue without shading = not computed)", fontsize=8, color=MUTED)
        cb.ax.tick_params(labelsize=7)
    fig.savefig(out_png, dpi=150, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-root", type=Path, help="replace data/raw with this folder (same sub-structure)")
    ap.add_argument("--out-root", type=Path, help="write outputs under this folder instead of the project")
    ap.add_argument("--no-checksum", action="store_true")
    ap.add_argument("--valid-fraction", action="store_true", help="compute valid-pixel fraction per date (slower)")
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe())

    raw_root = a.raw_root or config.DATA_RAW
    out_root = a.out_root or ROOT
    interim, tables, figs = (out_root / config.DATA_INTERIM.relative_to(ROOT),
                             out_root / config.RESULTS.relative_to(ROOT) / "tables",
                             out_root / config.RESULTS.relative_to(ROOT) / "figures")
    for d in (interim, tables, figs):
        d.mkdir(parents=True, exist_ok=True)

    all_files, all_av = [], []
    for name, spec in config.PRODUCTS.items():
        src = Path(spec["folder"])   # raw products under data/raw; derived ones (cdom300) under data/interim
        folder = (raw_root / src.relative_to(config.DATA_RAW) if src.is_relative_to(config.DATA_RAW)
                  else out_root / src.relative_to(ROOT))
        cache_file = interim / f"inventory_{name}.csv"
        cache = pd.read_csv(cache_file, dtype=str).astype({"size_bytes": int}) if cache_file.exists() else None
        recs = inventory_product(name, spec, config.DOMAIN, checksums=not a.no_checksum,
                                 valid_fraction=a.valid_fraction, cache=cache, folder=folder, rel_to=raw_root)
        ft, av = files_table(recs), availability_table(recs)
        ft.to_csv(cache_file, index=False)
        av.to_csv(interim / f"availability_{name}.csv", index=False)
        all_files.append(ft)
        all_av.append(av)
        shown = ("raw/" + folder.relative_to(raw_root).as_posix() if folder.is_relative_to(raw_root)
                 else folder.relative_to(out_root).as_posix() if folder.is_relative_to(out_root) else folder)
        print(f"[{name}] {shown}: {len(ft)} items, {len(av)} date entries")

    files = pd.concat(all_files, ignore_index=True)
    av = pd.concat(all_av, ignore_index=True)
    summary, missing = coverage(av, config.PRODUCTS, config.YEARS, config.SEASON)
    summary.to_csv(tables / "inventory_summary.csv", index=False)
    missing.to_csv(tables / "missing_dates.csv", index=False)
    plot_coverage(av, summary, config.PRODUCTS, config.YEARS, config.SEASON, figs / "inventory_coverage.png")

    # ---------------- console report
    pd.set_option("display.width", 160, "display.max_columns", 20, "display.max_colwidth", 70)
    print("\n=== Files per product and status ===")
    counts = (files.groupby(["product", "status"]).size().unstack(fill_value=0)
              .reindex(columns=["ok", "warning", "error"], fill_value=0))
    counts["GB"] = (files.groupby("product")["size_bytes"].sum() / 1e9).round(2)
    print(counts.to_string())

    problems = files[files["status"] != "ok"].copy()
    problems["file"] = problems["path"].str.split("/").str[-1]
    problems["message"] = problems["message"].str.slice(0, 80)
    print("\n=== Problems (full paths in data/interim/inventory_<product>.csv) ===")
    print(problems[["product", "status", "file", "message"]].to_string(index=False) if len(problems) else "none")

    dups = av[av["duplicate"]] if len(av) else av
    print("\n=== Duplicate acquisitions (same product, date, time, sensor, tile) ===")
    if len(dups):
        dups = dups.assign(file=dups["source"].str.split("/").str[-1])
        print(dups[["product", "date", "time_utc", "sensor", "tile", "file"]].to_string(index=False))
    else:
        print("none")

    n_days = summary["season_days"].iloc[0] if len(summary) else 0
    print(f"\n=== Days with data per season (out of {n_days}) ===")
    print(summary.pivot(index="year", columns="product", values="days_with_data").to_string())
    print("\n=== Longest run of days without data ('-' = no data that season) ===")
    print(summary.pivot(index="year", columns="product", values="longest_gap_days")
          .to_string(na_rep="-", float_format=lambda v: f"{v:.0f}"))

    ev = config.EVENT_YEAR
    print(f"\n=== Event year {ev}: missing dates in nominally daily products ===")
    m = missing[(missing["year"] == ev) & missing["nominally_daily"]]
    for name, g in m.groupby("product"):
        print(f"{name}: {len(g)} missing -> {', '.join(g['date'].str[5:].tolist()[:40])}"
              + (" ..." if len(g) > 40 else ""))
    if not len(m):
        print("none")

    print(f"\nTables: {interim} and {tables}\nFigure: {figs / 'inventory_coverage.png'}")


if __name__ == "__main__":
    main()
