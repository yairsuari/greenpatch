"""Shared map helpers."""
from __future__ import annotations

import numpy as np

NICE_KM = (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000)


def add_scalebar(ax, extent=None, frac=0.25, loc=(0.62, 0.06), color="#0b0b0b", transform=None, fontsize=7, zorder=10):
    """Draw a metric scale bar on a lon/lat map.

    extent: (lon0, lon1, lat0, lat1) of the view; default ax limits (works for plain axes in degrees and for cartopy
    PlateCarree axes). The bar length is the largest 'nice' value <= frac of the view width, measured at the bar's
    latitude (1° lon = 111.32 km x cos(lat)). loc: lower-left corner in axes fractions. For cartopy axes pass
    transform=ccrs.PlateCarree().
    """
    if extent is None:
        (lon0, lon1), (lat0, lat1) = ax.get_xlim(), ax.get_ylim()
    else:
        lon0, lon1, lat0, lat1 = extent
    x0 = lon0 + loc[0] * (lon1 - lon0)
    y0 = lat0 + loc[1] * (lat1 - lat0)
    km_per_deg = 111.32 * np.cos(np.radians(y0))
    width_km = (lon1 - lon0) * km_per_deg
    length = max([k for k in NICE_KM if k <= frac * width_km] or [NICE_KM[0]])
    dlon = length / km_per_deg
    kw = {} if transform is None else {"transform": transform}
    tick = 0.012 * (lat1 - lat0)
    from matplotlib import patheffects as pe
    halo = [pe.withStroke(linewidth=3, foreground="white")]
    # two-segment bar (black/white) with end ticks
    ax.plot([x0, x0 + dlon / 2], [y0, y0], color=color, lw=3, solid_capstyle="butt", zorder=zorder, path_effects=halo, **kw)
    ax.plot([x0 + dlon / 2, x0 + dlon], [y0, y0], color="white", lw=3, solid_capstyle="butt", zorder=zorder, **kw)
    ax.plot([x0, x0 + dlon], [y0, y0], color=color, lw=0.6, zorder=zorder + 1, **kw)
    for x in (x0, x0 + dlon / 2, x0 + dlon):
        ax.plot([x, x], [y0 - tick, y0 + tick], color=color, lw=0.8, zorder=zorder + 1, **kw)
    label = f"{length:g} km" if length >= 1 else f"{length * 1000:g} m"
    ax.text(x0 + dlon / 2, y0 + 2.2 * tick, label, ha="center", va="bottom", fontsize=fontsize, color=color,
            zorder=zorder + 1, path_effects=halo, **kw)
    return length
