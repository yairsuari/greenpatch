"""Pilot check of the very high 2026 300 m chl: product ceiling, QAA a_ph443 vs chl, and same-day agreement with the HR
product (different sensors and algorithm). Diagnostic only, prints to screen. Usage: python scripts/tools/check_chl_ceiling.py <project root>"""
import numpy as np, xarray as xr, pandas as pd, glob, sys
root = sys.argv[1]
P = f"{root}/data/processed/pilot"
o = xr.open_dataset(f"{P}/olci300/daily_t0000.nc")
c = xr.open_dataset(f"{P}/cdom300/daily_t0000.nc")
h = xr.open_dataset(f"{P}/hr/daily_t0000.nc")
sea = (o.mask_land == 0) & (o.mask_buffer == 0) if "mask_buffer" in o else (o.mask_land == 0)

def season(ds, months=(9, 10)):
    return ds.time.dt.month.isin(months)

# 1. distribution of linear chl
chl = 10 ** o.chl.where(sea)
df = chl.to_dataframe("chl").dropna().reset_index()
df["y"] = df.time.dt.year; df["m"] = df.time.dt.month
sep = df[df.m.isin([9, 10])]
print("1. 300 m chl Sep-Oct, pixel-days, linear mg m-3")
g = sep.groupby(sep.y == 2026).chl
print(pd.DataFrame({"n": g.size(), "median": g.median(), "p90": g.quantile(.9), "p99": g.quantile(.99), "max": g.max(),
                    "frac>=50": g.apply(lambda s: (s >= 50).mean()), "frac>=90": g.apply(lambda s: (s >= 90).mean()),
                    "frac>=99.9": g.apply(lambda s: (s >= 99.9).mean())}).rename(index={True: "2026", False: "2016-25"}))
# raw check: is 100 a hard cap? count raw values exactly at max in raw files
raw = sorted(glob.glob(f"{root}/data/raw/satellite/chl/olci300/**/*.nc", recursive=True))
mx = []
for f in raw:
    r = xr.open_dataset(f)
    v = r["CHL"]
    mx.append((f.split("/")[-1][-40:], float(v.max()), int((v >= 99.99).sum()), int(v.notnull().sum())))
print("raw files: (name, max, n>=99.99, n valid)"); [print(" ", m) for m in mx]

# 2. aph443 vs chl (QAA absorption, semi-independent of the band-ratio chl)
m = xr.merge([o.chl.rename("lchl"), c.aph443.rename("laph"), c.adg443.rename("ladg")]).where(sea)
d = m.to_dataframe().dropna(subset=["lchl", "laph"]).reset_index()
d["y"] = d.time.dt.year; d["m"] = d.time.dt.month
print("\n2. log10 aph443 = a + b log10 chl (all months), by group")
for name, s in [("2016-25", d[d.y < 2026]), ("2026 Jul-Aug", d[(d.y == 2026) & d.m.isin([7, 8])]),
                ("2026 Sep-Oct", d[(d.y == 2026) & d.m.isin([9, 10])])]:
    b, a = np.polyfit(s.lchl, s.laph, 1)
    print(f"  {name:13s} n={len(s):6d} slope={b:.2f} intercept={a:.2f} r={np.corrcoef(s.lchl, s.laph)[0,1]:.2f}"
          f"  median aph/chl* (m2 mg-1)={np.median(10**s.laph/10**s.lchl):.4f}  median adg/aph={np.nanmedian(10**(s.ladg-s.laph)):.2f}")
# residual of 2026 from the baseline fit, in bins of chl
b, a = np.polyfit(d[d.y < 2026].lchl, d[d.y < 2026].laph, 1)
s26 = d[(d.y == 2026) & d.m.isin([9, 10])].copy(); s26["res"] = s26.laph - (a + b * s26.lchl)
s26["chlbin"] = pd.cut(10 ** s26.lchl, [0, 5, 10, 20, 40, 101])
print("  2026 Sep-Oct residual from baseline aph-chl fit (log10), by chl class:")
print(s26.groupby("chlbin", observed=True).res.agg(["size", "median"]).round(3).to_string())

# 3. HR (100 m, Sentinel-2/Landsat, different algorithm) vs 300 m on the same day: box medians
def boxmed(da, mask):
    return da.where(mask).median(["latitude", "longitude"])
hsea = (h.mask_land == 0) & (h.mask_buffer == 0)
bm = pd.DataFrame({"chl300": boxmed(o.chl, sea).to_series(), "aph": boxmed(c.aph443, sea).to_series(),
                   "adg": boxmed(c.adg443, sea).to_series()})
bh = pd.DataFrame({"chlHR": boxmed(h.chl, hsea).to_series(), "tur": boxmed(h.tur, hsea).to_series()})
j = bm.join(bh, how="inner").dropna(subset=["chl300", "chlHR"])
j["y"] = j.index.year; j["m"] = j.index.month
print("\n3. Same-day box medians (log10), 300 m vs HR")
for name, s in [("2020-25", j[j.y < 2026]), ("2026 Sep-Oct", j[(j.y == 2026) & j.m.isin([9, 10])])]:
    print(f"  {name:13s} n={len(s):3d} r(chl300,chlHR)={s.chl300.corr(s.chlHR):.2f} median diff (300-HR)={np.median(s.chl300-s.chlHR):+.2f}"
          f"  r(chl300,tur)={s.chl300.corr(s.tur):.2f}  r(chlHR,tur)={s.chlHR.corr(s.tur):.2f}")
s = j[(j.y == 2026) & j.m.isin([8, 9, 10])]
print("  2026 Aug-Oct same-day box medians (linear):")
print((10 ** s[["chl300", "chlHR", "tur", "aph", "adg"]]).round(3).to_string())

# 4. does turbidity explain the chl anomaly? daily box anomalies vs the same calendar window in the baseline
an = xr.open_dataset(f"{P}/olci300/chl_anom_daily_t0000.nc")
ah = xr.open_dataset(f"{P}/hr/tur_anom_daily_t0000.nc")
print("\n4. anomaly files:", list(an.data_vars), list(ah.data_vars))

# 5. (added 2026-11-05) Is the 300 m chl driven by the Case II branch (AD4, Berthon and Zibordi 2004; QUID 009_141to144
# issue 4.2: Chl = 10^(0.091 - 2.620 x - 1.148 x^2 - 4.949 x^3), x = log10(Rrs490/Rrs555); OLCI 560 used for 555)?
# Needs the raw 300 m reflectance bands (data/raw/satellite/rrs/olci300/<domain>/).
rr = sorted(glob.glob(f"{root}/data/raw/satellite/rrs/olci300/pilot/rrs300_*.nc"))
if rr:
    r = xr.open_mfdataset(rr, combine="by_coords").load()
    cc = xr.open_mfdataset(raw, combine="by_coords").load()
    r, cc = xr.align(r, cc, join="inner")
    ratio = r.RRS490 / r.RRS560
    x = np.log10(ratio)
    ad4 = 10 ** (0.091 - 2.620 * x - 1.148 * x ** 2 - 4.949 * x ** 3)
    t5 = pd.DataFrame({"chl": cc.CHL.values.ravel(), "ad4": ad4.values.ravel(), "ratio": ratio.values.ravel(),
                       "t": np.repeat(cc.time.values, cc.CHL[0].size)}).dropna()
    t5 = t5[t5.t.dt.month.isin([9, 10])]
    print("\n5. Sep-Oct: Rrs490/Rrs560 and AD4 chl vs the product chl (pixel-days)")
    for name, s in [("2016-25", t5[t5.t.dt.year < 2026]), ("2026", t5[t5.t.dt.year == 2026])]:
        print(f"  {name}: n={len(s)} median ratio={s.ratio.median():.2f} (share < 0.6: {(s.ratio < 0.6).mean():.2f}); "
              f"median chl={s.chl.median():.1f}, median AD4={s.ad4.median():.1f}")
    for q in (1.0, 0.8, 0.6, 0.5, 0.4, 0.35):
        print(f"  AD4 at Rrs490/Rrs560 = {q}: {10 ** (0.091 - 2.620 * np.log10(q) - 1.148 * np.log10(q) ** 2 - 4.949 * np.log10(q) ** 3):.1f} mg m-3")
