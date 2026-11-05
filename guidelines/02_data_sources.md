# 02 — Data sources

Status column: `proposed` → `access ok` → `downloaded` → `in use`. Product IDs must be verified in the CMEMS catalogue before use (products are renamed occasionally).

## Section 2 — Satellite observations (current focus: chlorophyll and the plume)

### 2.1 Chlorophyll and ocean-colour sources
| Source | Resolution | Period | Cost | Use | Status |
|---|---|---|---|---|---|
| **CMEMS `OCEANCOLOUR_MED_BGC_L3_MY_009_143`, 300 m OLCI dataset** (multi-year, Med-tuned algorithms) | 300 m, daily | 2016–present (interim "myint" datasets extend the record to recent months; verify that Aug–Sep 2026 is covered) | Free, registration | Daily timing, baseline climatology, CDOM check if its optics dataset (ADG443) exists at 300 m (verify) | **selected** |
| ~~CMEMS `OCEANCOLOUR_MED_BGC_L3_MY_009_143`, 1 km multi-sensor dataset~~ | ~~1 km, daily~~ | ~~1997–present~~ | ~~Free, registration~~ | ~~Long robustness baseline~~ | ~~dropped~~ |
| ~~CMEMS `OCEANCOLOUR_MED_BGC_L3_NRT_009_141` and gap-free L4 `009_142`~~ | ~~1 km / 300 m, daily~~ | ~~rolling recent years~~ | ~~Free, registration~~ | ~~2026 event, daily maps~~ | ~~dropped~~ |
| CMEMS `OCEANCOLOUR_MED_BGC_HR_L3_NRT_009_205` (Sentinel-2 + Landsat coastal) | ~100 m | ~2020– (verify) | Free, registration | Nearshore plume structure | **selected** |
| ~~ESA OC-CCI v6~~ | ~~1 km Med subset; 4 km global~~ | ~~1997–~~ | ~~Free~~ | ~~Independent long record, robustness check~~ | ~~dropped~~ |
| ~~Sentinel-3 A/B OLCI L2 WFR (EUMETSAT / Copernicus Data Space)~~ | ~~300 m~~ | ~~2016– (3B from 2018)~~ | ~~Free, registration~~ | ~~Own processing: Rrs, CDOM proxy, consistent single-sensor baseline~~ | ~~dropped~~ |
| ~~NASA OB.DAAC: MODIS-Aqua, VIIRS (SNPP, NOAA-20/21)~~ | ~~750 m–1 km~~ | ~~2002– / 2012–~~ | ~~Free, NASA Earthdata login~~ | ~~Cross-check; MODIS-Aqua is aging~~ | ~~dropped~~ |
| ~~NASA PACE OCI (hyperspectral)~~ | ~~≈1 km~~ | ~~2024–~~ | ~~Free, NASA Earthdata login~~ | ~~Phytoplankton type; separate real bloom from CDOM~~ | ~~dropped~~ |
| ~~PlanetScope (commercial)~~ | ~~≈3 m, daily~~ | ~~2017–~~ | ~~Paid; academic programs may give limited quota~~ | ~~Only if very-nearshore detail is needed; optional~~ | ~~dropped~~ |

### 2.1a Fit to a nearshore patch
The 2026 patch was mostly close to the shore, so each product is rated on four criteria, listed in order of importance.

| Criterion (weight) | What it means here |
|---|---|
| Coastal accuracy (×4) | Reliable values in the first ~0–5 km: few masked or contaminated coastal pixels (land adjacency, mixed pixels), atmospheric correction that copes with turbid water, and a chlorophyll algorithm suited to Case-2 water |
| Spatial resolution (×3) | Pixel size relative to a patch a few km wide |
| Temporal resolution (×2) | Effective revisit for daily evolution. Summer cloud cover over the Levant is low, so nominal revisit is roughly the effective revisit |
| Accuracy (×1) | Validation record and retrieval quality in general, mainly offshore |

Scale: ●●● good (3), ●●○ fair (2), ●○○ poor (1). Overall = 4·coastal + 3·spatial + 2·temporal + 1·accuracy, maximum 30.

| Product | Coastal accuracy | Spatial res. | Temporal res. | Accuracy | Overall | Rationale |
|---|---|---|---|---|---|---|
| CMEMS HR coastal `009_205` | ●●● | ●●● | ●●○ | ●●○ | **27** | Built by the provider from Sentinel-2 MSI and Landsat 8-9, ~100 m, ready-made; from 2020-01-01 |
| ~~PlanetScope (paid)~~ | ~~●●○~~ | ~~●●●~~ | ~~●●●~~ | ~~●○○~~ | ~~24~~ | ~~Daily at ~3 m, but its few broad bands give only qualitative chlorophyll. Useful for plume outlines only~~ |
| CMEMS MY 300 m OLCI variant (`009_143`) | ●●○ | ●●○ | ●●● | ●●● | 23 | Best long, consistent, daily product at useful resolution. Pixels within ~1 km of the coast are often flagged |
| ~~Sentinel-3 OLCI L2 WFR (own processing)~~ | ~~●●○~~ | ~~●●○~~ | ~~●●●~~ | ~~●●○~~ | ~~22~~ | ~~Daily at 300 m. Includes a neural-network Case-2 chlorophyll product and a CDOM product (`ADG443_NN`), which is useful for the CDOM check. Adjacency effects persist~~ |
| ~~CMEMS NRT L3 300 m (`009_141`)~~ | ~~●●○~~ | ~~●●○~~ | ~~●●●~~ | ~~●●○~~ | ~~22~~ | ~~Same as the multi-year product but not reprocessed. Needed for 2026 until the multi-year product catches up~~ |
| ~~CMEMS MY 1 km multi-sensor (`009_143`)~~ | ~~●○○~~ | ~~●○○~~ | ~~●●●~~ | ~~●●●~~ | ~~16~~ | ~~The 1 km pixels lose the nearshore band. Best for the long robustness baseline~~ |
| ~~ESA OC-CCI v6~~ | ~~●○○~~ | ~~●○○~~ | ~~●●●~~ | ~~●●●~~ | ~~16~~ | ~~Well validated, with per-pixel uncertainty. Too coarse for the coastal strip~~ |
| ~~CMEMS L4 gap-free (`009_142`)~~ | ~~●○○~~ | ~~●○○~~ | ~~●●●~~ | ~~●●○~~ | ~~15~~ | ~~Interpolation smooths sharp coastal gradients. Use for context maps only~~ |
| ~~MODIS-Aqua / VIIRS (NASA)~~ | ~~●○○~~ | ~~●○○~~ | ~~●●●~~ | ~~●●○~~ | ~~15~~ | ~~Standard atmospheric correction fails in turbid nearshore water, and MODIS-Aqua is aging. Cross-check only~~ |
| ~~PACE OCI~~ | ~~●○○~~ | ~~●○○~~ | ~~●●●~~ | ~~●●○~~ | ~~15~~ | ~~≈1.2 km, too coarse nearshore, and still being validated. Its value is phytoplankton type, not mapping~~ |

**Update 2026-10-20 (user decision): the statistics use the two Copernicus Marine products only** — the 300 m OLCI product (chlorophyll + five reflectance bands 412.5/442.5/490/560/665 nm for the organic-matter proxy) and the ~100 m HR coastal mosaic (chlorophyll, turbidity, suspended matter). **Own processing of Sentinel-2/Landsat (ACOLITE) was dropped from the project altogether on 2026-10-26 (user).** Estimated download: about 50–100 GB compressed for 2016–2026 July–October, which fits on the local disk.

**Selected products (2026-10-20; other rows kept above struck through for the record):**
1. **CMEMS multi-year 300 m OLCI dataset (`009_143`)** — daily timing and evolution, the per-pixel climatology, and the formal significance test; five reflectance bands for the organic-matter proxy.
2. **CMEMS HR coastal product `009_205`** — ~100 m nearshore structure (chlorophyll, turbidity, suspended matter); baseline 2020–2025 only.


**Estimated volumes:** see the full-domain dry run in `handoff.md` (Copernicus Marine products only).

Consequences of dropping the other products:
- There is no 1 km long-record robustness baseline. The baseline is limited to the Sentinel-3 era (2016–) for 300 m and 2020– for HR.
- The CDOM check uses the QAA proxies computed from the five 300 m reflectance bands; the main proxy is a_dg443 (user 2026-10-26). HR turbidity and suspended matter cover sediment.
- 2026 coverage comes from the multi-year product's interim extension. Verify that August–September 2026 is available; otherwise the NRT 300 m dataset is the fallback.

All core sources are free; the real costs are storage and processing time.

**Caveat — chlorophyll versus CDOM.** The coastal strip is optically complex (Case-2 water). Freshwater brings coloured dissolved organic matter (CDOM) and sediment, which inflate standard chlorophyll retrievals. Part of the 2026 "chlorophyll" may be a freshwater-colour signal. CDOM absorption is also a known proxy for low-salinity plume water, so every analysis runs on chlorophyll and on a CDOM/a_dg(443) or Rrs-ratio product side by side.

### 2.2 Baseline period
- 2020–2025 alone (six years) is too short for stable per-pixel percentiles or z-scores; it can only rank 2026.
- **Proposed main baseline: 2016–2025** (Sentinel-3 OLCI, 300 m, one sensor family).
- ~~**Robustness: 2003–2025 (or 2010–2025)** from the merged 1 km multi-year product.~~ Dropped with the 1 km product (2026-10-14). Robustness is now tested by baseline sub-periods instead (e.g. 2016–2020 vs 2021–2025).
- Figures may show only 2020–2026.

### 2.3 Analysis methods
The full statistical procedure for identifying the patch in space and time is in `05_stage1_patch_identification.md`.

---

## Section 3 — Oceanographic data and modelling (DRAFT, not yet reviewed)

Research questions Q1–Q3: `00_project_overview.md`. Q2 uses the operational model output (3.4, `07`); Q3 our own model (`03`). Little in-situ data is expected (user 2026-10-26).

### 3.1 Salinity, temperature, sea level
- **SSS:** SMOS, SMAP, CMEMS `MULTIOBS_GLO_PHY_S_SURFACE_MYNRT_015_013`, ESA CCI SSS. ~25–70 km, land contamination near the coast. Good for offshore large-scale freshening, poor in the nearshore band.
- **SST:** CMEMS `SST_MED_SST_L4_NRT_010_004` and multi-year `010_021`, ~1–4 km. Upwelling, fronts, stratification proxies.
- **Altimetry / currents:** CMEMS sea-level L4 products. Eddies (Shikmona/Cyprus eddy) and the Levantine coastal current carrying Nile water northward.

### 3.2 In situ observations
- **IOLR** (Israel Oceanographic & Limnological Research): national Mediterranean monitoring program, Haifa section cruises, DeepLev mooring, ISRAMAR portal. Most important ground truth; access likely needs direct contact.
- **THEMO buoys** (University of Haifa) and university cruises.
- **Desalination plant intake records** (Sorek, Hadera, Ashkelon, Palmachim, Ashdod): salinity, turbidity, chlorophyll, SDI. Via the Water Authority or operators.
- **Argo / BGC-Argo, EMODnet Chemistry, CMEMS `INSITU_MED_PHYBGCWAV_DISCRETE_MYNRT_013_035`.** Sparse near the coast; vertical structure.

### 3.3 Freshwater and nutrient sources (H1)
- **Nile:** Rosetta and Damietta outflows are regulated by Aswan and small; agricultural drains and the Manzala/Burullus lagoon outflows matter more. GloFAS discharge reanalysis; Lake Nasser levels from altimetry (DAHITI, Hydroweb); reports on GERD/Aswan operations in 2026.
- **Gaza:** wastewater treatment collapsed after 2023; raw sewage into Wadi Gaza and coastal outfalls. UNEP, WHO, OCHA, Palestinian Water Authority reports; satellite plume imagery as an independent proxy (Copernicus products only).
- **Israeli streams** (Kishon, Alexander, Yarkon, Soreq, Lachish): Israel Hydrological Service.
- **Atmosphere:** ERA5 (winds, Ekman transport, heat fluxes), GPM IMERG (rain over Nile basin/Ethiopia), CAMS dust deposition (possible third nutrient source).

### 3.4 Existing ocean model outputs (Q2) — verified 2026-10-26/30
- `MEDSEA_ANALYSISFORECAST_BGC_006_014`: daily 4.2 km chl, functional types, nutrients, kd490; 2024-07-23 → rolling; past days are the **analysis** (issued forecasts are not archived, OGS 2026-10-29).
- `MEDSEA_MULTIYEAR_BGC_006_008`: daily 4.2 km chl, phyc, nutrients; 1999 → 2026-09-30 (interim).
- `MEDSEA_ANALYSISFORECAST_PHY_006_013`: salinity, temperature, currents, mixed layer, sea level; 2024-08-27 → rolling.
- Product documentation facts (assimilation, rivers, coastal bias): `07_q2_operational_model.md`. Other models: `03_models.md`.
