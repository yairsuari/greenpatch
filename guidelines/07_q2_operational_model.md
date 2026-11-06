# 07 — Q2: the operational biogeochemical system

**Question:** did the operational Mediterranean biogeochemical system represent the 2026 patch at all, even in its best estimate (the analysis, with satellite chlorophyll assimilated), and does it contain the processes and inputs needed to forecast it?

Status: implemented 2026-10-30 (`scripts/08_q2_operational_model.py`; first results in section 8). ⚙ = parameter still to be agreed. Background and reasoning: `../q2_way_forward.md`.

## 1. Why the question is worded this way
- The operational system makes a 10-day forecast every day; when a day arrives, its forecast is overwritten by the analysis. **The issued forecasts are not stored** (OGS, reply to the user, 2026-10-29 [VERIFY: how to cite — personal communication]).
- So "did it forecast the patch?" cannot be tested directly. What can be tested:
  - whether the patch appears in the analysis (an **upper bound** on the forecast);
  - how fast the model loses the patch between assimilations (**saw-tooth test**);
  - whether the model has the **inputs and processes** a forecast would need.
- Lead-time skill is tested in Q3 with our own reforecasts (`03_models.md`).

## 2. The system (from the product documentation)
Sources: QUIDs of `MEDSEA_ANALYSISFORECAST_BGC_006_014` (issue 3.3), `MEDSEA_MULTIYEAR_BGC_006_008` (issue 3.3) and `MEDSEA_ANALYSISFORECAST_PHY_006_013` (issue 2.6), all dated 28 May 2025; Teruzzi et al. (2021, Biogeosciences 18, 6147–6166). The QUIDs describe the 2025 system: **confirm with OGS that this setup ran in Aug–Oct 2026** [VERIFY].

| Item | Analysis-forecast (006_014, MedBFM4.3) | Reanalysis (006_008, MedBFM3.2) |
|---|---|---|
| Grid | 1/24° (~4.2 km), daily | 1/24°, daily |
| Physics | NEMO 006_013, ECMWF operational analyses/forecasts (~0.1°) | Med physics reanalysis 006_004 (interim: ERA5/ERA5T forcing; reanalysis forcing [VERIFY]) |
| Satellite chl assimilated | `OCEANCOLOUR_MED_BGC_L3_NRT_009_141` (NRT L3) | ESA-CCI-based OC product; interim run: NRT L3 |
| Other assimilated data | BGC-Argo chl, nitrate, oxygen; neural-network nitrate profiles | — |
| Assimilation timing | **Weekly, on Tuesday**; satellite composite of days −11 to −5; then 7 days of analysis, 1 day hindcast, 10-day forecast. Wed–Mon: hindcast + forecast only | Weekly, 7-day composite |
| Coast assimilated? | No coastal mask mentioned; coastal and open-sea data assimilated (Teruzzi et al. 2021) | Yes: "over the whole domain including both the open sea and the coastal areas" |
| Rivers | 39; daily EFAS discharge for 38; **Nile = monthly climatology** (Said et al. 2011); fixed nutrient concentrations per land macro-region | Same 39 rivers; PERSEUS 1999–2018 annual loads × climatological monthly runoff |
| SE Levantine land inputs | **Only the Nile** (one point). No Gaza, Israeli streams, wastewater or lagoon outflows | Same |
| Atmospheric deposition | Fixed winter/summer values for 32 areas (from CAMS reanalysis) | Constant in time |
| Time coverage (catalogue, 2026-10-26) | 2024-07-23 → rolling (past = analysis) | 1999-01-01 → 2026-09-30 (interim since the end of the reanalysis) |

**Known coastal bias** (QUID 006_014, Table 13; waters < 200 m, 2022–2024; model before assimilation vs satellite), summer:

| Sub-basin | Bias (mg m⁻³) | Bias, log10 |
|---|---|---|
| lev3 (south-central Levantine) | −0.42 | −0.38 |
| lev4 (eastern Levantine) | −0.22 | −0.29 |

These are the most negative coastal biases in the Mediterranean. The QUID suggests that the model underestimates the local fertilising effect of the Nile. Sub-basins (QUID 006_014, Figure 3, p. 24, checked 2026-10-30): the lev3/lev4 boundary lies at about 33.3°E (read from the map). The Israeli coast, Gaza and northern Sinai east of ~33.3°E (including the pilot box) are in **lev4**; the Nile delta coast from Rosetta to about El-Arish is in **lev3**. Our full domain therefore spans both.

### 2b. The Nile in the operational system (QUIDs read 2026-11-06)
What the documents say, quoted or paraphrased closely, with sources:

| Aspect | Physics (006_013, NEMO v4.2; QUID issue 2.6, p. 16 and 18, change log) | Biogeochemistry (006_014, OGSTM-BFM; QUID issue 3.3, setup item 9, p. 23–24, Table 9) |
|---|---|---|
| Freshwater discharge | "monthly mean dataset for the Nile River (Said et al., 2011)": a **monthly climatology**, identical every year. The other 38 rivers use daily EFAS v5.0 | "Only for Nile, freshwater discharges are provided by climatological data. River locations and their freshwater input are aligned with the Med-physics setup": the same climatology as the physics |
| How it enters | As runoff in the water balance (E − P − R) at the river mouth | Tracer load = daily freshwater discharge × a **fixed reference concentration** per tracer (mass m⁻³) |
| Tracers carried | Fresh water (salinity and volume) | N, P, Si, alkalinity and DIC. Nothing in the text about organic matter or CDOM |
| Concentrations | — | One reference concentration set for each of **4 Mediterranean land macro-regions**, from a literature review (Di Biagio et al. 2025). The Nile values are **not given in the QUID** [VERIFY: ask OGS] |
| Mouths | Not stated in the text | River no. 1 in Table 9 and **one red dot** on the Figure 3 map, i.e. apparently **one input point** for the Nile, not separate Rosetta and Damietta mouths [VERIFY: grid cell(s) with OGS] |
| Since when | Change log: "Use of EFAS v5.0 daily discharge data for 38 rivers and Nile river discharge from monthly climatology", entry dated **25 Nov 2025**, so this setup was in force during Aug–Oct 2026, unless a later change exists [VERIFY with OGS] | Same, through the physics alignment |

Reference: Said, M. A., Gerges, M. A., Maiyza, I. A., Hussein, M. A., Radwan, A. A. (2011). Changes in Atlantic Water
characteristics in the south-eastern Mediterranean Sea as a result of natural and anthropogenic activities.
*Oceanologia* 53(1), 81–95. (Cited in the physics QUID; we have not read the paper itself, and the monthly values
used by the model are not reproduced in either QUID [VERIFY].)

**Consequences for Q2 and Q3:**
- The system **cannot know** of any 2026 anomaly in Nile releases, drain or lagoon outflows. Its Nile is the same in
  every year, and the reanalysis baseline 2016–2025 shares it. The only route by which a 2026 Nile anomaly could
  enter the analysis is the weekly chl assimilation, which corrects phytoplankton only (`03_models.md`, QUID facts),
  not the nutrients or the salinity.
- A model freshening in 2026 (Level C) therefore cannot come from a larger Nile. It would have to come from transport
  or mixing, or from the assimilation of in-situ salinity in the physics.
- The Nile's nutrient load scales with its climatological discharge × a macro-region concentration. Nutrient-rich
  outflows from agricultural drains and the Manzala/Burullus lagoons (`02_data_sources.md`), Gaza and the Israeli
  streams are absent.
- Q3 S0 and N-runs: use the same Nile climatology and concentrations as the operational system. **Ask OGS** for the
  monthly Nile discharge, its grid cell(s) and the Nile reference concentrations (N, P, Si, ALK, DIC).

Datasets (catalogue check 2026-10-26):
- 006_014: `cmems_mod_med_bgc-pft_anfc_4.2km_P1D-m` (chl + functional types), `-nut_` (NO3, PO4, NH4, Si), `-bio_`, `-optics_` (kd490).
- 006_008: `cmems_mod_med_bgc-plankton_my_4.2km_P1D-m` (chl, phyc), `-nut_my_`.
- 006_013: `-sal_`, `-tem_`, `-cur_`, `-mld_`, `-ssh_` (anfc, 4.2 km), from 2024-08-27.

## 3. Level A — the upper-bound test
1. **Data:** model surface chlorophyll; baseline 2016–2025 from the reanalysis (006_008); 2026 from the reanalysis-interim (to 30 Sep) and the analysis (006_014) for October. ⚙ Check that the interim and the analysis agree in September 2026, where they overlap; if they differ strongly, report both.
2. **Statistics:** the Q1 pipeline unchanged (`05`): log10, leave-one-year-out climatology per 10-day bin, Mann–Whitney with the autocorrelation n_eff, Benjamini–Hochberg q = 0.10, effect size ≥ ×1.5. ⚙ Minimum object area: 1 km² is smaller than one model cell (~17 km²); use one cell (no removal) or two cells.
3. **Domain:** the 5 × 5 km pilot box is about one model cell. Use an intermediate box (⚙ e.g. Gaza–Ashdod, 0–20 km offshore) for the first test, then the full domain.
4. **Comparison with Q1:** aggregate the 300 m satellite patch to the model grid (area fraction of patch pixels per model cell; ⚙ a cell counts as "patch" if ≥ 50 % of it is). Per bin: hit rate, false-alarm ratio, critical success index; onset and peak dates; alongshore extent.
5. **Interpretation:**

| Analysis in 2026 | Meaning for the forecast |
|---|---|
| No significant anomaly, even with assimilation | The forecast almost certainly missed the patch (strong result) |
| Significant anomaly matching the satellite patch | Forecast skill unknown: the patch may come from the assimilation alone |
| Anomaly misplaced, too weak or late | The system "knew" something but did not reproduce it; describe the mismatch |

## 3b. Level A for salinity (user request 2026-10-30; planned, not implemented)
The same anomaly analysis as for chlorophyll, applied to model **sea-surface salinity**, because the event was also reported as a marked salinity drop.

1. **Data** (catalogue check 2026-10-30):
   - physics reanalysis `MEDSEA_MULTIYEAR_PHY_006_004`, dataset `cmems_mod_med_phy-sal_my_4.2km_P1D-m` (`so`, daily, 4.2 km), 1987-01-01 → 2026-09-30 (interim);
   - analysis-forecast `MEDSEA_ANALYSISFORECAST_PHY_006_013` (`-sal_` anfc, from 2024-08-27) for October 2026.

   Surface level only (first model level, ⚙ ~1 m). Same baseline years, season, bins and domain as chlorophyll. ⚙ Same rule for the 2026 source as chlorophyll: reanalysis-interim to 30 Sep, analysis for October; check where they overlap.
2. **Statistics:** the Q1 pipeline, with these changes:
   - **no log transform** (salinity is roughly normal, in psu);
   - **one-sided test for lower salinity** (freshening; the pipeline already supports the "lower" direction, as used for r412_443);
   - **effect size as an absolute difference**, because ×1.5 has no meaning for salinity: ⚙ bin-median anomaly ≤ −0.3 psu (to be agreed; compare with the model's coastal salinity variability in the baseline);
   - autocorrelation n_eff, BH q = 0.10 and the minimum object area as for model chlorophyll.

   Output: a "freshening patch" per bin, and a whole-season test.
3. **What the model's salinity can tell us.** The physics assimilates in-situ temperature/salinity profiles (XBT, Argo, gliders) and satellite sea level, and relaxes towards satellite SST. It does **not** assimilate satellite surface salinity, and coastal profiles are rare. So, unlike chlorophyll, model coastal salinity is close to a **free model result**: it shows what the forcing and dynamics produce on their own. Its only freshwater sources nearby are the climatological Nile and precipitation (section 2).

| Model salinity in 2026 | Meaning |
|---|---|
| Significant freshening co-located with the satellite chl patch | The physics (transport of Nile water, winds, mixing) produced it without event-specific land inputs: points to ocean conditions (H2) and to a potentially forecastable signal |
| No freshening | Either the freshening came from inputs the model lacks (Gaza, streams, real Nile), or the model's physics missed it. Supports H1 if the observed freshening is confirmed |
| Freshening elsewhere or at another time | Describe the mismatch (position, timing, alongshore extent) |

4. **Comparison:**
   - with the satellite chlorophyll patch (Q1): overlap in space and time, and the lag between freshening and chlorophyll;
   - with the model chlorophyll patch (Level A): does the model link its own freshening to chlorophyll?
   - with observed salinity, if any. Little in-situ data is expected. Satellite SSS (SMOS/SMAP, ~25–70 km) is too coarse for the coastal strip; it could only check offshore freshening ⚙ (not in the plan unless the user wants it).
5. **Figures:** as for chlorophyll (bin anomaly maps with the patch outline; alongshore Hovmöller), one figure for salinity. Colour map: diverging, fresh = blue.

## 4. Level B′ — the saw-tooth test
- Satellite chlorophyll corrects the model once a week; for the other six days the model runs on its own.
- If the model cannot sustain the patch, the daily analysis in the patch area should **jump at each assimilation and decay over the next days**.
- Measure: mean log10 chl in the patch cells on days 1–7 after each assimilation, August–October 2026. Compare with the same days in baseline years (normal decay) and with the satellite on the same days.
- The decay over 1–7 days approximates **what an operational forecast started from that analysis would have lost**.
- Needed first: on which day of the published daily files the assimilation increment appears [VERIFY with OGS]. It can also be read from the data: look for step changes repeating every 7 days.
- Also check the OGS near-real-time validation page (https://medeaf.inogs.it/nrt-validation): the system compares its 7-day pre-assimilation state with satellite each week. If the 2026 values are archived, they give a real (sub-basin-averaged) forecast score.

## 5. Level C — inputs and physics
- **Inputs:** document what the model knows about land inputs (table in section 2). If the patch is driven by land inputs (Q3, H1), the system was **structurally unable** to forecast it: its only nearby river is a climatological Nile.
- **Physics:** formal salinity anomaly test in section 3b; here, the descriptive part: model surface salinity along the coast in Aug–Oct 2026 versus observed freshening (satellite SSS offshore; desalination intake records if obtained). If the physics shows the freshening but the biology does not, the problem is in inputs or biology; if the physics misses it too, it is in the forcing.
- **Nutrients:** model NO3/PO4 near the coast in 2026 versus baseline years.

## 6. Reporting
- Methods 2.8 (operational model output) and a Discussion paragraph: operational forecasts that are not archived cannot be checked against events that matter to the public; recommendation to archive them.
- Optional practical step (user to decide): start saving the daily forecast for our domain ourselves for future events.

## 8. First results (2026-10-30, full domain, model Jul–Sep 2026)
Run: `03_download_cmems.py --domain full --model`; `01_inventory.py --domain full`; `05`/`06 --domain full --products medbgc medphy`; `08_q2_operational_model.py`. Tables in `results/full/tables/q2_*.csv`, figures in `results/full/figures/q2/`.

1. **The analysis cannot be spliced onto the reanalysis.** On common days the operational analysis is offset from the reanalysis at the coast: salinity +0.07 to +0.25 psu (every month of 2025–2026), chlorophyll −0.06 to +0.13 log10. Splicing October 2026 created a false "record salty" October. **User decision (2026-10-30): keep October in** — October 2026 comes from the operational analysis, appended to the reanalysis-interim. October anomalies therefore include the offset: model salinity in October is +0.23 to +0.25 psu along the coast (rank 11/11 = saltiest), about the size of the offset, so it is not evidence of a real salinity rise; figures mark October with an asterisk.
2. **Formal test (as Q1): no FDR-significant cell, for either variable.** This reflects **no power**, not absence: the model fields are smooth, a 10-day bin has n_eff ≈ 1.4 per year (salinity ≈ 1.0), the smallest p is ≈ 0.03, and BH over ~4,600 cells per map passes none.
3. **Model chlorophyll shows the event's timing, at much lower amplitude.** Israel/Gaza coastal strip (< 12 km, 143 cells): 2026 is the **highest of 11 years** in every bin from 1 Sep to 31 Oct (Sep ×2.0, ×1.9, ×1.3; Oct ×1.6, ×1.4, ×1.4, October with the offset caveat); 21–31 Aug ×1.3 (rank 3). Record cells (beyond all baseline years and ≥ ×1.5) in the strip: 27 (21–31 Aug), 98, 91, 47 (Sep bins). In the map, the record area lies along the coast from Gaza to ~32.6°N in early September.
4. **Amplitude and level gap.** At the pilot box (2 model cells): model chl 0.13–0.15 mg m⁻³ in Sep 2026 (×2.2–2.5 its baseline of ~0.05–0.07); satellite 300 m 12–25 mg m⁻³ (×6.5–8.8 its baseline of ~1.8–2.7). In normal years the model is already ~25–40× below the satellite at this coast (resolution and representativeness explain part of it: 4.2 km cells vs 300 m pixels within ~2–3 km of the shore).
5. **Saw-tooth confirmed.** In the operational analysis the largest day-to-day change falls on **Mondays** (mean |Δlog10| 0.11; Tue 0.05; other days 0.02–0.04, all decreasing). This matches the first day of the 7-day analysis window of the Tuesday run. After each jump the coastal chl decays: from the day-1 peak to day 6, −0.17 log10 (×0.67) in Sep–Oct 2026 and −0.25 (×0.56) in Jul–Aug 2026, against −0.11 (×0.78) in Sep–Oct 2024–2025. **The model does not sustain the assimilated signal; it loses it faster in 2026 than in normal years.**
6. **Model salinity: no freshening.** (October: see item 1.) Coastal strip Jul–Sep 2026: median anomaly −0.13 to −0.01 psu, rank 3–7 of 11 (rank 1 = freshest); no record-fresh cell in the strip (threshold −0.3 psu). The physics alone did not produce a freshening event at this coast.
7. **Reading (to discuss):** the system's best estimate "knew" that something happened (record chl in the right place and time), but only through the weekly assimilation, at about a quarter of the observed log-anomaly, and it loses it within days. Without land inputs other than a climatological Nile, and without a freshening in its physics, a forecast started from the analysis would likely have decayed towards normal values. The direct statement "the forecast missed it" remains an inference (forecasts not archived).

## 7. Open points
- Confirm the 2025 QUID setup was in operation in Aug–Oct 2026; archived 2026 pre-assimilation misfits; assimilation day in the daily files (all: ask OGS).
- ⚙ intermediate box; minimum object area on the model grid; patch fraction threshold for the comparison.
- ⚙ salinity: effect-size threshold (proposed −0.3 psu); surface level; whether to add satellite SSS offshore.
- How to present Level A given the power problem (descriptive record cells / ranks next to the formal test?).
- Offset of the operational analysis vs the reanalysis (October kept in by the user): report it in the paper; ask OGS about it.
- Domain and sub-basins: the Israeli coast, Gaza and the pilot box are in lev4 (user confirmed 2026-10-30); the full domain's western part (Nile delta, west of ~33.3°E) is in lev3.
