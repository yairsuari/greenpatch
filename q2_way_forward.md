# What to do now that we cannot test "did we forecast it?"

*Draft by Claude, 2026-10-29. Section 3.2 updated 2026-10-30 from the official product documentation. Not yet part of the guidelines. Uncertain facts are marked [VERIFY].*

---

## 1. What changed

OGS (Trieste) confirmed that **the forecasts as they were issued are not stored**. Every day, the operational system makes a forecast for the next ~10 days. When that day arrives, the forecast is overwritten by the analysis, which is the model's best estimate after it has been corrected with satellite chlorophyll. Only the analysis is kept.

So the original Q2, *"did the operational system forecast the patch?"*, **can no longer be answered directly.** That question asks: on, say, 20 August, did the forecast for 25 August show high chlorophyll off Israel? Answering it needs the 20 August forecast, which no longer exists.

## 2. Why the questions have to change, not only the methods

Keeping the old wording, *"did we forecast it?"*, would promise a result we cannot deliver. I suggest we **reword Q2 so that it asks only what the data can answer**, and give the real forecasting test to Q3, where we make our own forecasts.

| | Old wording | Proposed wording | Answered with |
|---|---|---|---|
| **Q1** | Did we see the patch, and what was its extent in time and space? | *(unchanged)* | Satellite (done for the pilot) |
| **Q2** | Did the operational system forecast it? | **Did the operational system represent the patch at all, even in its best estimate? And does it contain the processes and inputs needed to forecast it?** | Copernicus analysis and reanalysis, plus the product documentation |
| **Q3** | If not, could we forecast it? | **Could the patch have been forecast, how many days ahead, and what would that have required?** | Our own model, run as a forecast |

Attribution (why 2026 was different) stays inside Q3, as decided earlier.

## 3. Q2: what we can still learn from the operational system

### 3.1 The analysis is an upper bound on the forecast

The analysis has satellite chlorophyll assimilated into it, so it is **the best the system could have shown**. A forecast starts from the analysis and then runs without any new observations, so it can only be worse. The analysis therefore works as a one-sided test:

| What the analysis shows in 2026 | What it says about the forecast | How strong |
|---|---|---|
| **No significant anomaly**, even with satellite data assimilated | The forecast almost certainly missed the patch too | **Strong, clear result.** This is the outcome where Q2 counts most |
| **Significant anomaly**, matching the satellite patch | Unknown: the patch may come from the assimilation alone | Weak. The forecast skill stays undetermined, and we say so |
| **Anomaly in the wrong place, too weak, or too late** | The system "knew" something but did not get it right | Medium. We describe the mismatch |

We test the analysis with **exactly the same statistics as Q1**: the same baseline years, the autocorrelation correction, FDR, ×1.5 and minimum area. This makes the satellite result and the model result directly comparable.

### 3.2 What the official documentation says (checked 2026-10-29)

Sources:
- the Quality Information Documents (QUID) of the three products, all issue dated 28 May 2025 and approved in October 2025 (see the source list at the end);
- one peer-reviewed paper on the assimilation (Teruzzi et al.).

The QUIDs describe the system as of 2025. The system may have been upgraded before August–October 2026, so we should confirm with OGS that this setup was in operation during the event [VERIFY].

#### (1) What is assimilated, and is the coast included?

**Operational analysis-forecast (`MEDSEA_ANALYSISFORECAST_BGC_006_014`, MedBFM4.3, ~4 km)**
- **What is assimilated:**
  - surface satellite chlorophyll from the near-real-time Mediterranean ocean-colour product `OCEANCOLOUR_MED_BGC_L3_NRT_009_141`;
  - BGC-Argo profiles of chlorophyll, nitrate and oxygen;
  - nitrate profiles reconstructed with a neural network.
- **Scheme:** a variational method (3DVarBio). It corrects the four phytoplankton groups, nitrate, phosphate and oxygen.
- **When:** the assimilation runs **once a week, on Tuesday**.
  - That run uses a **satellite composite of days −11 to −5** before the Tuesday and then computes seven days of analysis.
  - From Wednesday to Monday, the system only runs forward: one day of hindcast plus a 10-day forecast, with no new chlorophyll observations.
  - In other words, the satellite data that correct the model are **5–11 days old** when they are used, and they are used **only once a week**.
- **Coast:** the QUID for 006_014 does not mention any coastal or depth mask for the assimilation. The reanalysis QUID, below, says explicitly that coastal waters are assimilated. Teruzzi et al. (2021) also state that the assimilated surface chlorophyll includes both open-sea and coastal observations. **So the coastal strip is assimilated**, although at the model's ~4 km resolution our patch occupies only the first one or two grid cells from the shore.

**Reanalysis (`MEDSEA_MULTIYEAR_BGC_006_008`, MedBFM3.2)**
- Weekly assimilation of satellite chlorophyll (ESA-CCI-based product from the Copernicus ocean-colour team).
- The QUID states that the scheme "assimilates chlorophyll concentration over the whole domain including both the open sea and the coastal areas".
- The 2026 part of this product is the **"interim"** run. It is produced monthly with near-real-time ocean-colour data, has the same setup, and may be of lower quality than the reanalysis.

**What this means for Q2**
- The coast is assimilated, so the **upper-bound logic of 3.1 applies**: we cannot treat the analysis as a free model run.
- The weekly cycle gives us **a new test that needs no archived forecasts.** Every Tuesday the analysis is pulled towards the satellite; between Tuesdays the model runs on its own.
  - If the model **cannot sustain the patch by itself**, its chlorophyll will jump up at each assimilation and decay during the following days. This would show up as a **saw-tooth pattern** in the daily analysis.
  - The size of that decay over 1–7 days roughly measures **what the operational forecast would have lost.** It is the closest substitute we have for the missing forecasts.
  - We can compute it from the downloadable daily data. The exact day of the week on which the assimilation increment appears in the published daily files needs checking [VERIFY].
- **Possible partial forecast verification:** the QUID says that OGS compares the model **before assimilation**, after seven days without satellite data, with satellite chlorophyll every week. The results are on a near-real-time validation page (https://medeaf.inogs.it/nrt-validation).
  - If those weekly values are archived for August–October 2026, they give a real forecast score for 2026.
  - However, they are averaged over whole sub-basins: the Israeli and Gaza coast lies in "lev4", the eastern Levantine, and the Nile delta in "lev3" (QUID Figure 3, p. 24). This is much coarser than the patch, and unlikely to resolve it.
  - We should check the page or ask OGS [VERIFY].

#### (2) What river and coastal inputs does the model use?

**Operational analysis-forecast (006_014, with its physics 006_013)**
- **Rivers:** 39 rivers in the whole Mediterranean (QUID Table 9).
  - In the south-eastern Levantine, **the only river is the Nile**, as a single point source. The nearest other listed river is the Asi/Orontes in Turkey/Syria.
  - **No Israeli or Gaza streams, no wastewater outfalls and no other coastal sources** are listed.
- **Nile freshwater:** the **monthly climatology** of Said et al. (2011), in both the physics and the biogeochemistry. The QUID: "Only for Nile, freshwater discharges are provided by climatological data". The Nile is therefore **the same every year**. All other 38 rivers use daily discharges from the European Flood Awareness System (EFAS).
- **River nutrients:** daily water discharge × a fixed reference concentration for each of 4 large land regions, taken from the literature. Nutrient loads therefore do not respond to real changes in effluent or agricultural input either.
- **Atmospheric deposition of N and P:** fixed winter and summer values for 32 areas, derived from the CAMS reanalysis. It is not event-specific.
- **Weather:** operational ECMWF analyses and forecasts, ~0.1°.
- **Ocean physics:** the physics assimilates satellite sea level and sea-surface temperature and in-situ temperature/salinity profiles. A coastal freshening caused by local discharge would therefore not be created by the model; at most it would be pulled in partly by assimilated observations, if any exist nearby.

**Reanalysis (006_008)**
- The same 39 rivers.
- Nutrient loads are the **1999–2018 annual values** from the PERSEUS project, multiplied by a **climatological monthly runoff**.
- Atmospheric deposition is constant in time.
- No interannual variability in land inputs at all.

**Known weakness at exactly our coast**
- In the QUID's coastal validation (Table 13, waters shallower than 200 m, 2022–2024), the south-central and eastern Levantine have the **largest negative bias in the whole Mediterranean**:

  | Sub-basin, summer | Bias (mg m⁻³) | Bias, log10 | Model vs satellite |
  |---|---|---|---|
  | lev3 | −0.42 | −0.38 | about 40 % of satellite |
  | lev4 | −0.22 | −0.29 | about half of satellite |

  These are the model **before** assimilation.
- The QUID attributes this to a "possible underestimation of the local fertilization effect of the Nile input along the southeastern Levantine coastal zone".

**What this means for Q2**
- The operational system **has no way to produce a discharge-driven anomaly at our coast.** Its only river nearby is a climatological Nile; Gaza, Israeli streams and wastewater are missing; and it already underestimates coastal chlorophyll there in normal years.
- Any 2026 anomaly in the analysis can only come from two sources:
  - **assimilation** of the satellite data, which comes back again each week but then decays;
  - **physics**, for example transport or mixing, which the model does see through real weather.
- This turns Q2 from a "miss" into an **explanation**. If the cause was land input, the system was **structurally unable** to forecast the event, whatever its forecast said.
- It also defines Q3 run (a): an "operational-like" run uses a climatological Nile and no Gaza or wastewater input.

### 3.3 Physics check

Did the operational physics show what the patch would need? For example, coastal freshening (low salinity), warming, or the current direction along the coast. This comes from `MEDSEA_ANALYSISFORECAST_PHY_006_013`. If the physics was right and only the biology was wrong, that points to the inputs or the biology model. If the physics was also wrong, that points to the forcing.

### 3.4 Output of Q2

A clear statement such as:
> "Even with satellite data assimilated, the operational system did (not) show a significant anomaly; its river inputs are climatological; therefore it could (not) have forecast the event."

Plus a Discussion paragraph: **operational forecasts that are not archived cannot be checked against events that matter to the public, such as the desalination shutdowns.** This is a limitation of our study and a recommendation to the operational centres.

## 4. Q3: we make the forecasts ourselves

Since the real forecasts are gone, we **re-create forecasts** with our own regional model. These are forecasts run today but using only information available at the time. This is the actual test of "could it have been forecast?".

### 4.1 Design

- **Start dates:** every few days from about 10 August to early September 2026, so that they cover the onset ("between late August and early September" from Q1).
- **Starting conditions:** the Copernicus physics and biogeochemistry analysis on the start date. These are the same starting conditions the operational forecast had.
- **Length:** 10 days, the same as the operational forecasts.
- **Scoring:** each forecast is compared with the Q1 satellite patch and with **persistence** ("tomorrow is like today"). Measures: hit rate, false alarms, and the onset date.

### 4.2 Three run types, each answering a part of the question

| Run | Atmosphere | Rivers and coastal inputs | What it answers |
|---|---|---|---|
| **(a) Operational-like** | Forecasts available at the time [VERIFY: archive] | As in the operational system (3.2): monthly climatological Nile only; no Gaza, Israeli streams or wastewater | A **stand-in for the missing operational forecast**: would a system like the operational one have caught it? |
| **(b) Forecast with better inputs** | Same as (a) | Real 2026 discharge as far as it was knowable | Would **better inputs** have made it forecastable? Is this a practical recommendation? |
| **(c) Perfect forcing** | Reanalysis (the actual weather) | Real 2026 discharge | Upper limit: is it forecastable even with everything known? Also the **mechanism** (attribution) |

The comparison between (a), (b) and (c) is the core result of the paper. It shows where predictability is lost: in the weather forecast, in the inputs, or in the model itself.

Run (a) is the important new idea. It partly **replaces the missing Q2 forecast**. We cannot recover what the operational system said, but we can show what a comparable system would have said.

## 5. What this means for the paper

- **The story stays the same:** observed → did the operational system have it → could it be forecast and why.
- **Q2 becomes shorter and more cautious,** but it can still give a strong result (the first row of the table in 3.1).
- **Q3 becomes the centre of the paper.** That makes the paper stronger, but it depends on running the model.
- **The point that forecasts are not archived** is a finding the community will care about, not only a weakness.
- **Main risk:** Q3 takes the most work (setting up the model, inputs, runs). Until it is done, the paper rests on Q1 and Q2.

## 6. Proposed order of work

1. **Now, no model needed:**
   - ~~Read the product documentation~~ (done 2026-10-29, section 3.2).
   - Ask OGS three things:
     - (i) was the 2025 QUID setup in operation in August–October 2026;
     - (ii) are the weekly "model before assimilation vs satellite" values for 2026 archived;
     - (iii) on which day the weekly assimilation appears in the published daily files.
2. **Q1 on the full domain** (Rosetta to Rosh HaNikra) on the external machine.
3. **Q2:** download the model chlorophyll, salinity and nutrients (reanalysis 2016–2025 plus analysis 2026). Run the existing pipeline on them and compare with the satellite patch.
4. **Q3:** find an archive of atmospheric forecasts from August 2026 [VERIFY], set up the regional model, then run (c), (a) and (b), in that order.
5. **Optional, for the future:** start saving the daily operational forecasts for our region ourselves, so that the next event can be checked.

## 7. Decisions needed from you

*Status 2026-10-30:*
- *1, 2 and 5 accepted by the user.*
- *Moved into `guidelines/07_q2_operational_model.md`, `03_models.md` and the manuscript.*
- *3 and 4 are still open.*

1. Do you accept the **new wording** of Q2 and Q3 (section 2)?
2. Do you accept the **three run types** (a, b, c) for Q3, especially the "operational-like" run as a stand-in for the missing forecast?
3. Should we **start archiving** the operational forecasts now (cheap: a small daily download)?
4. How should the OGS reply be cited (personal communication)? [VERIFY]
5. Add the **saw-tooth test** (3.2 (1)) to Q2 as the substitute for the missing forecasts?

## Sources

- QUID `MEDSEA_ANALYSISFORECAST_BGC_006_014`, issue 3.3 (28 May 2025): https://documentation.marine.copernicus.eu/QUID/CMEMS-MED-QUID-006-014.pdf. Used: sections II.1–II.3 (assimilation, weekly cycle, upstream data, rivers, items 8–9), Table 9 (rivers) and Table 13 (coastal skill, p. 37).
- QUID `MEDSEA_MULTIYEAR_BGC_006_008`, issue 3.3 (28 May 2025): https://documentation.marine.copernicus.eu/QUID/CMEMS-MED-QUID-006-008.pdf. Used: II.2–II.5 (assimilation of coastal areas, PERSEUS river loads, interim run).
- QUID `MEDSEA_ANALYSISFORECAST_PHY_006_013`, issue 2.6 (28 May 2025): https://documentation.marine.copernicus.eu/QUID/CMEMS-MED-QUID-006-013.pdf. Used: forcing section (ECMWF, EFAS for 38 rivers, Nile monthly climatology from Said et al. 2011).
- Teruzzi, A. et al. (2021). Deep chlorophyll maximum and nutricline in the Mediterranean Sea: emerging properties from a multi-platform assimilated biogeochemical model experiment. *Biogeosciences* 18, 6147–6166. https://doi.org/10.5194/bg-18-6147-2021 (coastal and open-sea satellite chlorophyll assimilated).
- OGS near-real-time validation page (named in the 006_014 QUID): https://medeaf.inogs.it/nrt-validation (not yet checked).
