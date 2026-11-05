"""Geometry helpers: mainland coastline and coastal-strip masks."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon, box
from shapely.ops import transform, unary_union

UTM = "EPSG:32636"   # UTM zone 36N (04_conventions.md)


@lru_cache(maxsize=1)
def mainland_utm(view=(28.0, 38.0, 29.0, 37.0)):
    """Mainland land polygon (Africa + Asia, lagoons filled, islands such as Cyprus dropped), in UTM 36N.

    Source: Natural Earth 1:10m land (cached by cartopy). Accuracy ~ a few hundred metres: fine for crop margins,
    NOT for the distance-to-coast coordinate of the analysis (use a high-resolution coastline there).
    """
    import cartopy.io.shapereader as shpreader
    lon0, lon1, lat0, lat1 = view
    clip = box(lon0, lat0, lon1, lat1)
    shp = shpreader.natural_earth(resolution="10m", category="physical", name="land")
    geoms = [g.intersection(clip) for g in shpreader.Reader(shp).geometries() if g.intersects(clip)]
    to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
    land = transform(to_utm, unary_union(geoms))
    polys = getattr(land, "geoms", [land])
    return unary_union([Polygon(p.exterior) for p in polys if p.area > 1e10])


@lru_cache(maxsize=8)
def coastal_buffer_ll(max_km: float):
    """Polygon (lon/lat) of everything within max_km of the mainland coast (includes the land itself)."""
    to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform
    return transform(to_ll, mainland_utm().buffer(max_km * 1000, resolution=16))


def coastal_mask(lon, lat, max_km: float) -> np.ndarray:
    """Boolean array: True where (lon, lat) lies within max_km of the mainland coast. lon/lat 1-D or 2-D."""
    lon, lat = np.asarray(lon), np.asarray(lat)
    if lon.ndim == 1 and lat.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)
    poly = coastal_buffer_ll(float(max_km))
    shapely.prepare(poly)
    return shapely.contains_xy(poly, lon, lat)


# ---------------------------------------------------------------- high-resolution coastline (analysis)
@lru_cache(maxsize=1)
def mainland_hr_utm():
    """Mainland land polygon from GSHHG full resolution (background_data/coastline, scripts/tools/fetch_coastline.py),
    lagoons filled and islands dropped, in UTM 36N. Used for distance-to-coast and the alongshore coordinate."""
    import json
    from shapely.geometry import shape
    from .config import COASTLINE
    land = shape(json.loads(COASTLINE.read_text(encoding="utf-8"))["features"][0]["geometry"])
    to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
    land = transform(to_utm, land)
    polys = getattr(land, "geoms", [land])
    land = unary_union([Polygon(p.exterior) for p in polys if p.area > 1e10])
    # 500 m closing: bridges the Suez Canal (Africa and Asia are separate polygons in GSHHG) and harbour inlets < ~1 km
    land = land.buffer(500, resolution=8).buffer(-500, resolution=8)
    polys = getattr(land, "geoms", [land])
    return Polygon(max(polys, key=lambda p: p.area).exterior)


def _utm_xy(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    if lon.ndim == 1 and lat.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)
    x, y = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform(lon, lat)
    return np.asarray(x), np.asarray(y)


def on_land(lon, lat) -> np.ndarray:
    """True where the cell centre lies on the mainland (GSHHG full resolution)."""
    land = mainland_hr_utm()
    shapely.prepare(land)
    return shapely.contains_xy(land, *_utm_xy(lon, lat))


def distance_to_coast_km(lon, lat) -> np.ndarray:
    """Distance (km) from each cell centre to the mainland coastline; positive at sea, negative on land."""
    land = mainland_hr_utm()
    x, y = _utm_xy(lon, lat)
    pts = shapely.points(x, y)
    d = shapely.distance(land.exterior if hasattr(land, "exterior") else land.boundary, pts) / 1000.0
    return np.where(on_land(lon, lat), -d, d)


@lru_cache(maxsize=1)
def alongshore_line():
    """Smoothed coastline (UTM) from config.ALONGSHORE['start'] to ['end'], and the position of the origin on it."""
    from shapely.ops import substring
    from .config import ALONGSHORE as A
    # close lagoon outlets and inlets (Manzala, Bardawil) so the coordinate follows the open-sea shore
    land = mainland_hr_utm().buffer(A["closing_km"] * 1000, resolution=8).buffer(-A["closing_km"] * 1000, resolution=8)
    land = max(getattr(land, "geoms", [land]), key=lambda g: g.area)
    ring = land.exterior
    to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
    pos = [ring.project(shapely.Point(*to_utm(*A[k]))) for k in ("start", "end")]
    a, b = sorted(pos)
    arc1 = substring(ring, a, b)                                            # one way round the ring
    arc2 = shapely.line_merge(shapely.MultiLineString([substring(ring, b, ring.length), substring(ring, 0, a)]))
    line = arc1 if arc1.length <= arc2.length else arc2                     # the coast, not the clip box edges
    if line.project(shapely.Point(*to_utm(*A["start"]))) > line.length / 2:
        line = line.reverse()                                               # run from start (south-west) to end
    line = line.simplify(A["smooth_km"] * 1000.0)
    s0 = line.project(shapely.Point(*to_utm(*A["origin"])))
    return line, s0


def alongshore_km(lon, lat) -> np.ndarray:
    """Alongshore coordinate s (km) of each cell centre: projection onto the smoothed coast, 0 at the origin."""
    line, s0 = alongshore_line()
    x, y = _utm_xy(lon, lat)
    return (shapely.line_locate_point(line, shapely.points(x, y)) - s0) / 1000.0


def cell_area_km2(lon, lat) -> np.ndarray:
    """Area (km²) of each cell of a regular lon/lat grid (1-D coordinates), spherical approximation."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    dlon, dlat = np.abs(np.gradient(lon)), np.abs(np.gradient(lat))
    r = 6371.0088
    return (np.radians(dlat)[:, None] * r) * (np.radians(dlon)[None, :] * r * np.cos(np.radians(lat))[:, None])
