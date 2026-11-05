"""Map of the provisional analysis domain (guidelines/04_conventions.md).

Left: full domain with the coastal analysis bands and key freshwater sources.
Right: zoom on the Israeli coast with desalination plants and stream mouths.

Output: results/maps/domain_map.png and .pdf (both domains; the pilot box is outlined in panel b)
        results/maps/pilot_box_map.png       close-up of the pilot box with the 300 m and ~100 m grid cells
Run from the project root:  .venv/Scripts/python scripts/00_domain_map.py
"""
import sys
from pathlib import Path

import numpy as np

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from greenpatch import config  # noqa: E402
from greenpatch.plotting import add_scalebar  # noqa: E402

OUT = ROOT / "results" / "maps"
OUT.mkdir(parents=True, exist_ok=True)

# Domains (04_conventions.md, config.DOMAINS)
_f, _p = config.DOMAINS["full"], config.DOMAINS["pilot"]
LAT0, LAT1, LON0, LON1 = _f["lat0"], _f["lat1"], _f["lon0"], _f["lon1"]
PILOT = (_p["lon0"], _p["lon1"], _p["lat0"], _p["lat1"])
GRIDS = {"300 m (009_143)": 0.0027, "~100 m HR (009_205)": 0.00093}   # grid steps in degrees (config.CMEMS notes)
VIEW = (29.9, 36.2, 30.6, 35.0)            # lon0, lon1, lat0, lat1 for the main panel
ZOOM = (33.9, 35.4, 31.2, 33.2)            # Israeli coast panel
BANDS_KM = [1, 5, 15, 30]                  # offshore band edges (05_stage1_patch_identification.md)

# Okabe-Ito colours (colour-blind safe) + distinct marker shapes
STYLE = {
    "desalination": dict(c="#D55E00", marker="s", label="Desalination plant"),
    "nile":         dict(c="#0072B2", marker="v", label="Nile mouth / lagoon outlet"),
    "gaza":         dict(c="#E69F00", marker="D", label="Wadi Gaza outflow"),
    "stream":       dict(c="#009E73", marker="^", label="Israeli stream mouth"),
}
LAND, SEA, INK, MUTED = "#e6e3dc", "#ffffff", "#222222", "#666666"
BAND_COLORS = ["#08306b", "#2171b5", "#6baed6", "#c6dbef"]  # one hue, dark (nearshore) -> light

# ---------------------------------------------------------------- geometry
land_shp = shpreader.natural_earth(resolution="10m", category="physical", name="land")
clip = box(VIEW[0] - 1, VIEW[2] - 1, VIEW[1] + 1, VIEW[3] + 1)
land_geoms = [g.intersection(clip) for g in shpreader.Reader(land_shp).geometries() if g.intersects(clip)]
land = unary_union(land_geoms)

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32636", always_xy=True).transform
to_ll = Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True).transform
land_utm = transform(to_utm, land)
# Mainland only: drop Cyprus and small islands so their buffers do not enter the domain
polys = getattr(land_utm, "geoms", [land_utm])
from shapely.geometry import Polygon
mainland_utm = unary_union([Polygon(p.exterior) for p in polys if p.area > 1e10])  # fill lagoons

domain_ll = box(LON0, LAT0, LON1, LAT1)
bands = []
inner = mainland_utm
for km in BANDS_KM:
    outer = mainland_utm.buffer(km * 1000, resolution=32)
    ring = transform(to_ll, outer.difference(inner)).intersection(domain_ll)
    bands.append(ring)
    inner = outer

isobath = None
try:  # 200 m isobath (shelf edge) from Natural Earth, if downloadable
    bshp = shpreader.natural_earth(resolution="10m", category="physical", name="bathymetry_K_200")
    isobath = [g for g in shpreader.Reader(bshp).geometries() if g.intersects(clip)]
except Exception as exc:  # noqa: BLE001
    print("200 m isobath not available:", exc)

pts = pd.read_csv(ROOT / "background_data" / "infrastructure" / "key_locations.csv")


# ---------------------------------------------------------------- plotting
def base(ax, extent):
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.set_facecolor(SEA)
    for g, col in zip(bands, BAND_COLORS):
        if not g.is_empty:
            ax.add_geometries([g], ccrs.PlateCarree(), facecolor=col, edgecolor="none", alpha=0.55, zorder=1)
    if isobath:
        ax.add_geometries(isobath, ccrs.PlateCarree(), facecolor="none", edgecolor="#999999",
                          linewidth=0.6, linestyle=(0, (3, 2)), zorder=2)
    ax.add_geometries([land], ccrs.PlateCarree(), facecolor=LAND, edgecolor="#555555", linewidth=0.5, zorder=3)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="#bbbbbb", alpha=0.8)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = {"size": 8, "color": MUTED}


def points(ax, extent, label_types, offsets=None, city_labels=None):
    offsets = offsets or {}
    lon0, lon1, lat0, lat1 = extent
    for _, r in pts.iterrows():
        if not (lon0 <= r.lon <= lon1 and lat0 <= r.lat <= lat1):
            continue
        if r.type == "city":
            ax.plot(r.lon, r.lat, "o", ms=3, color=INK, transform=ccrs.PlateCarree(), zorder=5)
            if city_labels is None or r["name"] in city_labels:
                ax.text(r.lon + 0.06, r.lat, r["name"], fontsize=7.5, color=MUTED, va="center",
                        transform=ccrs.PlateCarree(), zorder=6)
            continue
        s = STYLE[r.type]
        ax.plot(r.lon, r.lat, s["marker"], ms=7, mfc=s["c"], mec="white", mew=1.0,
                transform=ccrs.PlateCarree(), zorder=7)
        if r.type in label_types:
            dx, dy, ha = offsets.get(r["name"], (-0.06, 0.0, "right"))
            ax.annotate(r["name"].replace(" desalination plants", "").replace(" desalination plant", "").replace(" stream mouth", ""),
                        xy=(r.lon, r.lat), xytext=(r.lon + dx, r.lat + dy), fontsize=7.5, color=INK,
                        ha=ha, va="center", xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                        textcoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5) if (dx or dy) else None,
                        zorder=8)


fig = plt.figure(figsize=(13, 7.2))
ax1 = fig.add_axes([0.04, 0.12, 0.56, 0.80], projection=ccrs.PlateCarree())
ax2 = fig.add_axes([0.63, 0.12, 0.34, 0.80], projection=ccrs.PlateCarree())

# Main panel
base(ax1, VIEW)
ax1.add_patch(Rectangle((LON0, LAT0), LON1 - LON0, LAT1 - LAT0, fill=False, edgecolor=INK,
                        linewidth=1.6, transform=ccrs.PlateCarree(), zorder=9))
ax1.text(LON0 + 0.08, LAT1 - 0.12, "Provisional analysis domain\n31.0–34.5°N, 31.0–35.5°E",
         fontsize=8.5, color=INK, va="top", transform=ccrs.PlateCarree(), zorder=9)
ax1.add_patch(Rectangle((ZOOM[0], ZOOM[2]), ZOOM[1] - ZOOM[0], ZOOM[3] - ZOOM[2], fill=False,
                        edgecolor=MUTED, linewidth=0.9, linestyle="--", transform=ccrs.PlateCarree(), zorder=9))
points(ax1, VIEW, label_types={"nile", "gaza"},
       offsets={"Damietta Nile mouth": (0.0, 0.62, "center"),
                "Rosetta Nile mouth": (0.0, 0.35, "center"),
                "Lake Burullus outlet": (-0.1, 0.7, "right"),
                "Lake Manzala outlets (El-Gamil)": (0.45, 0.3, "left"),
                "Wadi Gaza mouth": (-0.25, 0.5, "right")})
dm = pts.loc[pts["name"] == "Damietta Nile mouth"].iloc[0]
ax1.text(dm.lon, dm.lat + 0.47, "(alongshore origin, s = 0)", fontsize=7, color=MUTED, style="italic",
         ha="center", transform=ccrs.PlateCarree(), zorder=8)
add_scalebar(ax1, VIEW, transform=ccrs.PlateCarree(), frac=0.2)
ax1.set_title("a  Analysis domain and freshwater sources", loc="left", fontsize=10, color=INK)

# Zoom panel
base(ax2, ZOOM)
points(ax2, ZOOM, label_types={"desalination", "stream", "gaza"},
       offsets={"Ashkelon desalination plant": (-0.25, -0.05, "right"),
                "Ashdod desalination plant": (-0.3, 0.0, "right"),
                "Sorek and Palmachim desalination plants": (-0.3, 0.08, "right"),
                "Hadera desalination plant": (-0.3, 0.0, "right"),
                "Lachish stream mouth": (0.12, -0.12, "left"),
                "Yarkon stream mouth": (0.12, 0.0, "left"),
                "Alexander stream mouth": (0.12, 0.0, "left"),
                "Kishon stream mouth": (0.10, 0.10, "left"),
                "Wadi Gaza mouth": (-0.25, -0.1, "right")},
       city_labels={"Gaza"})
ax2.add_patch(Rectangle((PILOT[0], PILOT[2]), PILOT[1] - PILOT[0], PILOT[3] - PILOT[2], fill=False,
                        edgecolor="#CC79A7", linewidth=1.8, transform=ccrs.PlateCarree(), zorder=9))
ax2.annotate("Pilot box (5 × 5 km)", xy=(PILOT[0], PILOT[3]), xytext=(PILOT[0] - 0.35, PILOT[3] + 0.12),
             fontsize=7.5, color="#CC79A7", xycoords=ccrs.PlateCarree()._as_mpl_transform(ax2),
             textcoords=ccrs.PlateCarree()._as_mpl_transform(ax2),
             arrowprops=dict(arrowstyle="-", color="#CC79A7", lw=0.6), zorder=9)
add_scalebar(ax2, ZOOM, transform=ccrs.PlateCarree(), frac=0.25)
ax2.set_title("b  Israeli coast", loc="left", fontsize=10, color=INK)

# Legend
handles = [Line2D([], [], linestyle="none", marker=s["marker"], ms=7, mfc=s["c"], mec="white", label=s["label"])
           for s in STYLE.values()]
handles.append(Line2D([], [], linestyle="none", marker="o", ms=3, color=INK, label="City"))
edges = [0] + BANDS_KM
handles += [Patch(facecolor=c, alpha=0.55, label=f"{a}–{b} km from coast") for c, a, b in zip(BAND_COLORS, edges, edges[1:])]
if isobath:
    handles.append(Line2D([], [], color="#999999", lw=0.8, linestyle=(0, (3, 2)), label="200 m isobath"))
handles.append(Line2D([], [], color=INK, lw=1.6, label="Analysis domain"))
fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.0))
fig.text(0.04, 0.955, "Green Patch 2026: provisional study domain", fontsize=13, color=INK, weight="bold")
fig.text(0.04, 0.925, "Point locations are approximate and need verification. Offshore bands follow the stage 1 analysis design.",
         fontsize=8.5, color=MUTED)

for ext in ("png", "pdf"):
    fig.savefig(OUT / f"domain_map.{ext}", dpi=200, facecolor="white")
print("saved", OUT / "domain_map.png")


# ---------------------------------------------------------------- pilot box close-up
def km(lon0, lon1, lat0, lat1):
    c = np.cos(np.radians((lat0 + lat1) / 2))
    return (lon1 - lon0) * 111.32 * c, (lat1 - lat0) * 110.57


m = 0.02
view = (PILOT[0] - m, PILOT[1] + m, PILOT[2] - m, PILOT[3] + m)
fig, axes = plt.subplots(1, 2, figsize=(12, 6), subplot_kw=dict(projection=ccrs.PlateCarree()))
lines = []
for ax, (name, step) in zip(axes, GRIDS.items()):
    ax.set_extent(view, crs=ccrs.PlateCarree())
    ax.set_facecolor(SEA)
    ax.add_geometries([land], ccrs.PlateCarree(), facecolor=LAND, edgecolor="#555555", linewidth=0.6, zorder=3)
    # cell edges of a regular grid (approximate: the product grid origin is not known before download)
    xs = np.arange(np.floor(view[0] / step) * step, view[1] + step, step)
    ys = np.arange(np.floor(view[2] / step) * step, view[3] + step, step)
    if len(xs) < 200:
        for x in xs:
            ax.plot([x, x], view[2:], color="#cccccc", lw=0.3, transform=ccrs.PlateCarree(), zorder=4)
        for y in ys:
            ax.plot(view[:2], [y, y], color="#cccccc", lw=0.3, transform=ccrs.PlateCarree(), zorder=4)
    ax.add_patch(Rectangle((PILOT[0], PILOT[2]), PILOT[1] - PILOT[0], PILOT[3] - PILOT[2], fill=False,
                           edgecolor="#CC79A7", linewidth=2, transform=ccrs.PlateCarree(), zorder=9))
    points(ax, view, label_types={"desalination", "gaza"})
    # count cells inside the box and how many are water (cell centre not on land)
    cx = np.arange(PILOT[0] + step / 2, PILOT[1], step)
    cy = np.arange(PILOT[2] + step / 2, PILOT[3], step)
    gx, gy = np.meshgrid(cx, cy)
    import shapely
    water = ~shapely.contains_xy(land, gx, gy)
    add_scalebar(ax, view, transform=ccrs.PlateCarree(), frac=0.25)
    ax.set_title(f"{name}: {gx.size} cells in box ({len(cx)} × {len(cy)}), {water.sum()} water",
                 loc="left", fontsize=9.5, color=INK)
    lines.append(f"{name}: {gx.size} cells, {water.sum()} water")
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="#bbbbbb")
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = {"size": 7, "color": MUTED}
w, h = km(*PILOT)
fig.suptitle(f"Pilot box {PILOT[2]}–{PILOT[3]}°N, {PILOT[0]}–{PILOT[1]}°E  ({w:.1f} × {h:.1f} km)   ·   "
             "Natural Earth 10 m coast (approximate at this scale)", x=0.02, ha="left", fontsize=11, color=INK)
fig.tight_layout()
fig.savefig(OUT / "pilot_box_map.png", dpi=200, facecolor="white")
print("saved", OUT / "pilot_box_map.png", f"({w:.1f} x {h:.1f} km;", "; ".join(lines) + ")")
