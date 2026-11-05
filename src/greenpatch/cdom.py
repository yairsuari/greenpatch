"""Coloured-organic-matter (CDOM) proxies from the CMEMS 300 m OLCI reflectance bands.

For every downloaded reflectance file (one year, July-October, daily time steps):
    compute -> write a compressed NetCDF raster -> verify -> delete the five source bands (logged).
The source bands are re-fetchable satellite data (CLAUDE.md exception, user instruction 2026-10-20).

Three proxies are stored so the choice of algorithm stays open after the bands are deleted:
    adg443      absorption by dissolved + detrital matter at 443 nm [m-1], QAA v6
    aph443      absorption by phytoplankton at 443 nm [m-1], QAA v6 (separates algae from CDOM)
    r412_443    Rrs(412.5) / Rrs(442.5) band ratio [-]; decreases as CDOM increases

QAA: Quasi-Analytical Algorithm, Lee, Carder and Arnone (2002, Applied Optics 41, 5755-5772),
version 6 update (Lee et al., IOCCG). Implemented here for the OLCI bands 412.5, 442.5, 490, 560, 665 nm
in place of the original 412, 443, 490, 555, 670 nm.
[VERIFY] the pure-water absorption values AW below (interpolated from Pope and Fry 1997 to the OLCI
wavelengths, written from memory) and the QAA v6 coefficients against the QAA v6 document before
the results are used in the manuscript.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import xarray as xr

BANDS = {"412": "RRS412_5", "443": "RRS442_5", "490": "RRS490", "555": "RRS560", "670": "RRS665"}
WL = {"412": 412.5, "443": 442.5, "490": 490.0, "555": 560.0, "670": 665.0}

# Pure-water absorption [m-1] at the OLCI wavelengths. [VERIFY] see module docstring.
AW = {"412": 0.00468, "443": 0.00696, "490": 0.0150, "555": 0.0619, "670": 0.429}


def bbw(wl):
    """Pure seawater backscattering [m-1], QAA v6 form: 0.0038 (400/wl)^4.32."""
    return 0.0038 * (400.0 / wl) ** 4.32


def qaa_v6(R: dict):
    """QAA v6 on above-water remote-sensing reflectance Rrs [sr-1].

    R: mapping band key ("412", "443", "490", "555", "670") -> array (numpy or xarray).
    Returns (adg443, aph443); negative or non-finite results become NaN.
    """
    g0, g1 = 0.089, 0.1245
    rrs = {k: v / (0.52 + 1.7 * v) for k, v in R.items()}                 # below-surface rrs
    u = {k: (-g0 + np.sqrt(g0 ** 2 + 4 * g1 * r)) / (2 * g1) for k, r in rrs.items()}

    # Step 2: total absorption at the reference wavelength (555 nm, or 670 nm in turbid water)
    chi = np.log10((rrs["443"] + rrs["490"]) /
                   (rrs["555"] + 5 * rrs["670"] / rrs["490"] * rrs["670"]))
    a555 = AW["555"] + 10 ** (-1.146 - 1.366 * chi - 0.469 * chi ** 2)
    a670 = AW["670"] + 0.39 * (R["670"] / (R["443"] + R["490"])) ** 1.14
    use670 = R["670"] >= 0.0015
    where = xr.where if isinstance(R["670"], xr.DataArray) else np.where   # keeps xarray/dask lazy
    bbp_ref = where(use670,
                    u["670"] * a670 / (1 - u["670"]) - bbw(WL["670"]),
                    u["555"] * a555 / (1 - u["555"]) - bbw(WL["555"]))
    wl_ref = where(use670, WL["670"], WL["555"])

    # Step 3-4: spectral backscattering and total absorption
    eta = 2.0 * (1 - 1.2 * np.exp(-0.9 * rrs["443"] / rrs["555"]))
    a = {}
    for k in ("412", "443"):
        bbp = bbp_ref * (wl_ref / WL[k]) ** eta
        a[k] = (1 - u[k]) * (bbw(WL[k]) + bbp) / u[k]

    # Step 5-6: split total absorption into dissolved/detrital and phytoplankton parts
    ratio = rrs["443"] / rrs["555"]
    zeta = 0.74 + 0.2 / (0.8 + ratio)                                    # aph(412)/aph(443)
    S = 0.015 + 0.002 / (0.6 + ratio)                                    # spectral slope of adg
    xi = np.exp(S * (WL["443"] - WL["412"]))                             # adg(412)/adg(443)
    adg443 = ((a["412"] - zeta * a["443"]) - (AW["412"] - zeta * AW["443"])) / (xi - zeta)
    aph443 = a["443"] - adg443 - AW["443"]

    def clean(x):
        return x.where(np.isfinite(x) & (x > 0)) if isinstance(x, xr.DataArray) else \
            np.where(np.isfinite(x) & (x > 0), x, np.nan)
    return clean(adg443), clean(aph443)


def compute(ds: xr.Dataset) -> xr.Dataset:
    """CDOM proxies for a dataset holding the five reflectance bands."""
    missing = [v for v in BANDS.values() if v not in ds]
    if missing:
        raise ValueError(f"reflectance bands missing: {missing}")
    R = {k: ds[v].astype("float32") for k, v in BANDS.items()}
    valid = np.isfinite(R["412"])
    for k in R:
        valid &= np.isfinite(R[k]) & (R[k] > 0)
    R = {k: v.where(valid) for k, v in R.items()}
    adg, aph = qaa_v6(R)
    out = xr.Dataset({
        "adg443": adg.astype("float32").assign_attrs(
            long_name="absorption by dissolved and detrital matter at 442.5 nm (QAA v6)", units="m-1"),
        "aph443": aph.astype("float32").assign_attrs(
            long_name="absorption by phytoplankton at 442.5 nm (QAA v6)", units="m-1"),
        "r412_443": (R["412"] / R["443"]).astype("float32").assign_attrs(
            long_name="Rrs(412.5) / Rrs(442.5) band ratio; lower = more CDOM", units="1"),
    })
    out.attrs.update(source_bands=", ".join(BANDS.values()),
                     method="QAA v6 (Lee et al. 2002, v6 update) on OLCI 300 m Rrs; see src/greenpatch/cdom.py",
                     history=f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ} computed by greenpatch.cdom")
    return out


ENC = dict(zlib=True, complevel=4, shuffle=True, significant_digits=4,
           quantize_mode="GranularBitRound", _FillValue=np.float32(-999.0))


def process_file(src: Path, dst: Path, chunk_days: int = 8) -> dict:
    """Compute the CDOM raster for one reflectance file and verify it. Does NOT delete anything."""
    with xr.open_dataset(src, chunks={"time": chunk_days}) as ds:
        out = compute(ds)
        out.attrs["source_file"] = src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp.nc")
        enc = {v: dict(ENC, chunksizes=(1,) + tuple(out[v].shape[1:])) if "time" in out[v].dims else dict(ENC)
               for v in out.data_vars}
        out.to_netcdf(tmp, encoding=enc)
        ok, msg = verify(ds, tmp)
    if ok:
        tmp.replace(dst)
    else:
        tmp.unlink(missing_ok=True)
    return dict(ok=ok, message=msg)


def verify(src_ds: xr.Dataset, out_path: Path, n_check: int = 3, tol: float = 2e-3):
    """Same time steps; variables present; values on a few time steps equal a fresh recomputation."""
    with xr.open_dataset(out_path) as out:
        for v in ("adg443", "aph443", "r412_443"):
            if v not in out:
                return False, f"{v} missing"
        if "time" in src_ds.dims and not np.array_equal(out["time"].values, src_ds["time"].values):
            return False, "time steps differ from source"
        idx = np.unique(np.linspace(0, out.sizes.get("time", 1) - 1, n_check).astype(int)) \
            if "time" in out.dims else [None]
        for i in idx:
            sel = {"time": [int(i)]} if i is not None else {}
            ref = compute(src_ds.isel(sel).load())
            got = out.isel(sel)
            for v in ref.data_vars:
                a, b = ref[v].values.astype(float), got[v].values.astype(float)
                if not np.array_equal(np.isfinite(a), np.isfinite(b)):
                    return False, f"{v}: valid-pixel pattern differs at time index {i}"
                f = np.isfinite(a)
                if f.any() and (np.abs(b[f] - a[f]) / np.maximum(np.abs(a[f]), 1e-9)).max() > tol:
                    return False, f"{v}: values differ at time index {i}"
        frac = float(out["adg443"].notnull().mean())
    return True, f"ok (valid adg443 fraction {frac:.2f})"


def run(src: Path, out_dir: Path, delete: bool = True, log: Path | None = None) -> dict:
    """Compute + verify the CDOM raster for one downloaded reflectance file, then delete the source.

    Output name follows guidelines/04_conventions.md: cdom_cmems-olci_300m_<period>_qaa.nc,
    where <period> is taken from the source name (rrs300_<year>_<MMDD-MMDD>.nc).
    The source is deleted only if verification passed; the deletion is logged with its checksum.
    """
    from .bench import Benchmark
    from .config import DELETION_LOG
    from .inventory import sha256
    from .slim import log_deletion

    period = src.stem.replace("rrs300_", "")
    dst = Path(out_dir) / f"cdom_cmems-olci_300m_{period}_qaa.nc"
    if dst.exists():
        return dict(ok=True, message="exists, skipped", dst=dst, deleted=False)
    with Benchmark("cdom_qaa", src.stem, out_path=dst):
        res = process_file(src, dst)
    res.update(dst=dst, deleted=False)
    if res["ok"] and delete:
        size = src.stat().st_size
        log_deletion(log or DELETION_LOG, src, size, sha256(src), f"CDOM raster verified: {dst.name}")
        src.unlink()
        res["deleted"] = True
    return res
