"""Reduce storage: slim copies of downloaded / processed files, then (optionally) delete the originals.

What it does per product (settings in src/greenpatch/config.py -> SLIM):
  olci300, hr   CMEMS NetCDF in data/raw/...  -> keep listed variables, crop to the domain, compress

Slim copies go to data/interim/<domain>/slim/<product>/ and are verified against the source
(same variables and time steps, values within 0.1 %) before any deletion.
Deletions are logged with checksums in data/interim/<domain>/deletion_log.csv (files can be re-downloaded).

Usage (from the project root)
  .venv/Scripts/python scripts/02_slim_storage.py                       # dry run: plan + estimated saving
  .venv/Scripts/python scripts/02_slim_storage.py --apply               # write + verify slim copies
  .venv/Scripts/python scripts/02_slim_storage.py --apply --delete-originals
  options: --domain pilot|full   --products olci300 hr   --root <other project-like folder, for testing>
"""
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
from greenpatch import config  # noqa: E402
from greenpatch.inventory import discover, sha256  # noqa: E402
from greenpatch.slim import _size, delete_path, log_deletion, slim_dataset, verify  # noqa: E402


def remap(p: Path, root: Path) -> Path:
    return root / Path(p).relative_to(config.ROOT)


def known_checksums(interim: Path) -> dict:
    out = {}
    for f in interim.glob("inventory_*.csv"):
        df = pd.read_csv(f, dtype=str)
        out.update(dict(zip(df["path"], df["sha256"])))
    return out


def slim_one(src: Path, dst: Path, spec: dict):
    src_ds, sub, enc, mask = slim_dataset(src, spec["keep"], spec["bbox"], spec["coast_km"], spec["sig_digits"])
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp.nc")
        sub.to_netcdf(tmp, encoding=enc)
        ok, msg = verify(src_ds, sub, tmp)
    finally:
        src_ds.close()
    if ok:
        tmp.replace(dst)
    else:
        tmp.unlink(missing_ok=True)
    return ok, msg, list(sub.data_vars)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products", nargs="+", default=list(config.SLIM), choices=list(config.SLIM))
    ap.add_argument("--apply", action="store_true", help="write slim copies (default: dry run)")
    ap.add_argument("--delete-originals", action="store_true",
                    help="after verification, delete source files")
    ap.add_argument("--root", type=Path, default=config.ROOT, help="project-like root (for testing)")
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe())
    if a.delete_originals and not a.apply:
        ap.error("--delete-originals requires --apply")

    raw_root = remap(config.DATA_RAW, a.root)
    interim = remap(config.DATA_INTERIM, a.root)
    log = interim / "deletion_log.csv"
    sums = known_checksums(interim)

    rows, problems = [], []
    for name in a.products:
        spec = config.SLIM[name]
        src_dir = remap(spec["folder"], a.root)
        out_dir = remap(config.SLIM_OUT, a.root) / name
        files = [p for p in discover(src_dir) if p.suffix == ".nc" and not p.name.endswith(".tmp.nc")]
        before = sum(_size(p) for p in files)
        stat = dict(product=name, files=len(files), before_GB=before / 1e9, after_GB=0.0,
                    slimmed=0, skipped=0, failed=0, deleted=0)

        if not a.apply:
            # dry run: slim one sample into a temporary folder to estimate the ratio
            if files:
                sample = max(files, key=_size)
                with tempfile.TemporaryDirectory() as td:
                    try:
                        ok, msg, kept = slim_one(sample, Path(td) / sample.name, spec)
                        ratio = _size(Path(td) / sample.name) / _size(sample) if ok else float("nan")
                        print(f"[{name}] sample {sample.name}: keeps {kept}; size ratio {ratio:.2f} ({msg})")
                    except Exception as exc:  # noqa: BLE001
                        ratio = float("nan")
                        print(f"[{name}] sample {sample.name}: cannot slim ({exc})")
                stat["after_GB"] = before * ratio / 1e9
            rows.append(stat)
            continue

        for src in files:
            dst = out_dir / src.name
            if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                stat["skipped"] += 1
                stat["after_GB"] += dst.stat().st_size / 1e9
                ok = True
                if a.delete_originals:   # never delete on trust: re-verify the existing slim copy first
                    try:
                        src_ds, sub, _, _ = slim_dataset(src, spec["keep"], spec["bbox"], spec["coast_km"],
                                                         spec["sig_digits"])
                        try:
                            ok, msg = verify(src_ds, sub, dst)
                        finally:
                            src_ds.close()
                    except Exception as exc:  # noqa: BLE001
                        ok, msg = False, f"{type(exc).__name__}: {exc}"
                    if not ok:
                        stat["failed"] += 1
                        problems.append(dict(product=name, file=src.name,
                                             problem=f"existing slim copy failed re-verification: {msg}"[:120]))
                        continue
            else:
                try:
                    ok, msg, _ = slim_one(src, dst, spec)
                except Exception as exc:  # noqa: BLE001
                    ok, msg = False, f"{type(exc).__name__}: {exc}"
                if not ok:
                    stat["failed"] += 1
                    problems.append(dict(product=name, file=src.name, problem=msg[:120]))
                    continue
                stat["slimmed"] += 1
                stat["after_GB"] += dst.stat().st_size / 1e9

            if ok and a.delete_originals:
                rel = src.relative_to(raw_root).as_posix() if src.is_relative_to(raw_root) else str(src)
                log_deletion(log, src, _size(src), sums.get(rel) or sha256(src), f"slim copy verified: {dst}")
                delete_path(src)
                stat["deleted"] += 1
        rows.append(stat)

    # ---------------- report
    df = pd.DataFrame(rows)
    df["saved_GB"] = df["before_GB"] - df["after_GB"]
    pd.set_option("display.width", 160)
    mode = "DRY RUN (estimate from one sample file per product)" if not a.apply else "APPLIED"
    print(f"\n=== Storage reduction: {mode} ===")
    cols = ["product", "files", "before_GB", "after_GB", "saved_GB"]
    if a.apply:
        cols[2:2] = ["slimmed", "skipped", "failed", "deleted"]
    print(df[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nTotal saved: {df['saved_GB'].sum():.3f} GB")
    if problems:
        print("\n=== Problems ===")
        print(pd.DataFrame(problems).to_string(index=False))
    if a.delete_originals:
        print(f"\nDeletion log: {log}")
    elif a.apply:
        print("\nOriginals kept. Re-run with --delete-originals to free the space.")


if __name__ == "__main__":
    main()
