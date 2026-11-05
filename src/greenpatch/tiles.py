"""Spatial tiling of the processing (needed for the full domain: one HR variable is ~44 GB in memory).

The grid of each product is cut into tiles of config.TILE[product] cells (~30 km). Each tile is read with a halo of
config.TILE_HALO cells, so that the coastal buffer and the 3x3 outlier test see their neighbours, and the halo is
trimmed before writing. All per-pixel statistics are independent, so tiles give the same results as one block, except
the outlier test, whose reference spread is the robust SD of that day's residuals within the tile.

Layout:  data/processed/<domain>/<product>/meta.json                 tiles, grid size, chosen bin kind
         data/processed/<domain>/<product>/<kind>_t<NNNN>.nc         kind = daily, bins, <var>_clim, <var>_anom_daily,
                                                                     <var>_anom_bins
One tile = one unit of work: on a server each tile is one batch job (--tile k), followed by one --finalize step.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr

from . import config

LAT, LON = "latitude", "longitude"


def product_dir(name: str) -> Path:
    return config.DATA_PROCESSED / name


def meta_path(name: str) -> Path:
    return product_dir(name) / "meta.json"


def source_files(name: str) -> list[Path]:
    folder = Path(config.PRODUCTS[name]["folder"])
    return sorted(f for f in folder.glob("*.nc") if not f.name.endswith(".tmp.nc"))


def grid(name: str) -> tuple[np.ndarray, np.ndarray]:
    files = source_files(name)
    if not files:
        raise FileNotFoundError(f"no NetCDF files for {name} in {config.PRODUCTS[name]['folder']}")
    with xr.open_dataset(files[0]) as ds:
        lat, lon = ds[LAT].values, ds[LON].values
    for f in files[1:]:   # model series combine two datasets: their grids must be identical
        with xr.open_dataset(f) as ds:
            if ds.sizes[LAT] != len(lat) or ds.sizes[LON] != len(lon) or not (
                    np.allclose(ds[LAT].values, lat, atol=1e-4) and np.allclose(ds[LON].values, lon, atol=1e-4)):
                raise ValueError(f"{name}: grid of {f.name} differs from {files[0].name}")
    return lat, lon


def tile_list(name: str, size: tuple[int, int] | None = None) -> list[dict]:
    """Tiles as dicts k, i0, i1, j0, j1 (core, without halo) over the product grid."""
    lat, lon = grid(name)
    ny, nx = size or config.TILE[name]
    out = []
    for i0 in range(0, len(lat), ny):
        for j0 in range(0, len(lon), nx):
            out.append(dict(k=len(out), i0=i0, i1=min(i0 + ny, len(lat)), j0=j0, j1=min(j0 + nx, len(lon))))
    return out


def tile_path(name: str, kind: str, k: int) -> Path:
    return product_dir(name) / f"{kind}_t{k:04d}.nc"


def write_meta(name: str, **kw):
    p = meta_path(name)
    meta = json.loads(p.read_text()) if p.exists() else {}
    meta.update(kw)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, indent=1))


def read_meta(name: str) -> dict:
    return json.loads(meta_path(name).read_text())


def attach_bins(ds: xr.Dataset, kind: str) -> xr.Dataset:
    """Add the calendar-bin label per time step (Step 8) and record the bin kind."""
    from .preprocess import bin_labels
    if "time" in ds.dims:
        ds["bin"] = ("time", bin_labels(ds.get_index("time"), kind), dict(long_name=f"calendar bin ({kind})"))
    ds.attrs["bin_kind"] = kind
    return ds


def load_tile(name: str, kind: str, k: int) -> xr.Dataset:
    ds = xr.load_dataset(tile_path(name, kind, k))
    return attach_bins(ds, read_meta(name)["bin_kind"]) if kind == "daily" else ds


def open_product(name: str, kind: str, load: bool = False) -> xr.Dataset:
    """All tiles of one output kind as one dataset (lazy with dask; load=True reads into memory)."""
    files = sorted(product_dir(name).glob(f"{kind}_t[0-9][0-9][0-9][0-9].nc"))
    if not files:
        raise FileNotFoundError(f"no {kind} tiles for {name} in {product_dir(name)}")
    ds = xr.open_mfdataset(files, combine="by_coords", data_vars="minimal", coords="minimal", compat="override")
    if load:
        ds = ds.load()
    meta = read_meta(name)
    ds.attrs.update(meta.get("attrs", {}))
    return attach_bins(ds, meta["bin_kind"]) if kind == "daily" else ds
