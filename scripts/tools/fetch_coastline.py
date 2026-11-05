"""Fetch the full-resolution GSHHG coastline (level 1: land/ocean) and store the study region as GeoJSON.

Source: GSHHG v2.3.7 (Wessel & Smith), full resolution, downloaded by cartopy from NOAA NCEI into its cache.
Output: background_data/coastline/gshhg_f_L1_east_med.geojson  (lon/lat, WGS84), read by greenpatch.geo.
Run once (from the project root):  .venv/Scripts/python scripts/tools/fetch_coastline.py
"""
import json
from pathlib import Path

import cartopy.io.shapereader as shpreader
from shapely.geometry import box, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "background_data" / "coastline" / "gshhg_f_L1_east_med.geojson"
VIEW = (28.0, 38.0, 29.0, 37.0)   # lon0, lon1, lat0, lat1 (same as geo.mainland_utm)

clip = box(VIEW[0], VIEW[2], VIEW[1], VIEW[3])
shp = shpreader.gshhs(scale="f", level=1)
geoms = [g.intersection(clip) for g in shpreader.Reader(shp).geometries() if g.intersects(clip)]
land = unary_union(geoms)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"source": "GSHHG v2.3.7 full resolution, level 1", "view": VIEW},
     "geometry": mapping(land)}]}), encoding="utf-8")
print("saved", OUT, f"({OUT.stat().st_size / 1e6:.1f} MB, from {shp})")
