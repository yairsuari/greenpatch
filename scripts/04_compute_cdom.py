"""Compute CDOM rasters for 300 m reflectance files already on disk (same step the download runs automatically).

For each data/raw/satellite/rrs/olci300/<domain>/rrs300_*.nc:
    QAA v6 -> adg443, aph443 and the Rrs(412.5)/Rrs(442.5) ratio
    -> data/interim/<domain>/cdom300/cdom_cmems-olci_300m_<year>_<MMDD-MMDD>_qaa.nc (compressed NetCDF raster)
    -> verify -> keep the source bands (default since 2026-10-23); --delete-bands deletes them (logged with checksum).

Usage (from the project root)
    .venv/Scripts/python scripts/04_compute_cdom.py
    .venv/Scripts/python scripts/04_compute_cdom.py --delete-bands
    .venv/Scripts/python scripts/04_compute_cdom.py --domain full
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greenpatch.runtime import add_domain_arg, domain_from_argv  # noqa: E402
domain_from_argv()  # before config: --domain selects the analysis domain
from greenpatch import cdom, config  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=config.CMEMS["rrs300"]["folder"])
    ap.add_argument("--out", type=Path, default=config.CDOM_OUT)
    ap.add_argument("--log", type=Path, default=config.DELETION_LOG)
    ap.add_argument("--delete-bands", action="store_true", help="delete the reflectance bands after verification")
    add_domain_arg(ap)
    a = ap.parse_args()
    print(config.describe())
    files = sorted(a.src.glob("rrs300_*.nc"))
    if not files:
        print(f"No reflectance files in {a.src}")
        return
    for f in files:
        try:
            res = cdom.run(f, a.out, delete=a.delete_bands, log=a.log)
            print(f"{f.name}: {res['message']} -> {res['dst'].name}; bands {'deleted' if res['deleted'] else 'kept'}")
        except Exception as exc:  # noqa: BLE001
            print(f"{f.name}: FAILED {type(exc).__name__}: {exc}; bands kept")


if __name__ == "__main__":
    main()
