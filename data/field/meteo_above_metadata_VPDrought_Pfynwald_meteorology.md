# Dataset Metadata — VPDrought Pfynwald meteorology measurements

---

## 1. Title

**Title:** Pfynwald VPDrought experiment atmospheric parameters and manipulations

**Titles (per file, for separate EnviDat publications):**
Pfynwald VPDrought experiment atmospheric parameters in canopy and VPD manipulation
Pfynwald VPDrought experiment atmospheric parameters over canopy
Pfynwald VPDrought experiment irrigation

---

## 2. Keywords

- VPDrought
- Pfynwald
- Rhone valley
- Drought experiment
- Irrigation
- Irrigation manipulation
- Continuous monitoring
- Long-term
- Forest ecosystem
- Air temperature
- Relative humidity
- VPD
- Precipitation
- Global radiation
- Photosynthetically Active Radiation
- PAR
- Wind speed
- Wind direction
- Atmospheric observations
- Meteorological measurements

---

## 3. Description

### Dataset content

This dataset provides the main atmospheric measurements and treatment information from the VPDrought
experiment at the Pfynwald research platform. It comprises three data files:

- **Over-canopy meteorological data** (`pfynwald_vpdrought_meteorology_oc_<YEAR>.txt`): in-situ
  measurements from the meteorological station located above the canopy. These represent atmospheric
  conditions above the canopy and are not affected by the VPD manipulation treatment. Provided at
  1-minute resolution: precipitation, air temperature, relative humidity, VPD, global radiation, PAR,
  wind speed, and wind direction.
- **In-canopy meteorological data** (`pfynwald_vpdrought_meteorology_ic_<YEAR>.txt`): aggregated
  measurements from multiple measurement points within the canopy at 1-minute resolution. Depending on
  the parameter, measurements are distinguished between ambient (`_amb`) and VPD-manipulated (`_manip`)
  conditions; parameters unaffected by the manipulation are provided as a single aggregated variable.
  Includes air temperature, relative humidity, VPD, wind speed, wind direction, and the operation status
  of the VPD reduction system.
- **Irrigation data** (`pfynwald_vpdrought_meteorology_irrigation_<YEAR>.txt`): daily irrigation sums
  aggregated across the four irrigated sub-plots (2, 3, 6, and 7).

### General quality control and gap filling

All meteorological and treatment data were subjected to a combined automatic and visual quality-control
(QC) procedure before gap filling: parameter-specific hard-limit, temporal-consistency,
consecutive-value, and spatial-consistency checks, followed by visual inspection of suspicious values
and periods. Implausible values were excluded.

After QC, the resulting time series were completely gap filled. The gap-filling method was selected
according to the characteristics of the individual parameter and the available reference data. Short
gaps were filled by linear interpolation; longer gaps were filled using parameter-specific approaches,
including fitting external reference data or using valid observations from preceding/following days at
the same time of day.

Value classes used across the data files:
- `observed` = directly measured value that passed QC
- `corrected` = measured value to which a correction was applied
- `derived` = value derived from multiple observations
- `estimated` = value estimated to fill a missing or excluded observation

`quality_flag` indicates the quality and origin of each value (1 = highest quality, up to 3 = lowest).
For `quality_flag` > 1, as well as for estimated or corrected values, `comment` gives additional
information on the method used to obtain the value and/or the reason for the reduced quality. Full
per-parameter definitions are below.

### Treatment and measurement conditions

- Irrigation and VPD reduction were generally limited to the period May–September.
- Irrigation added approximately 600 mm of water per year.
- The VPD reduction system mostly operated during periods of high VPD, typically from late morning to
  the evening; during operation, VPD was reduced by approximately 25%.
- During a few periods, treatments could not be applied (e.g. power cuts, lack of available water, or
  technical failures).
- In-canopy measurements were taken at the center of the tree crowns, exposed either to ambient
  atmospheric conditions or to VPD-reduced conditions. They are representative of the VPD treatment
  effects, although some gradients in VPD reduction occurred within the VPD-reduced canopies.
- For further information, see: Schaub, M., Hunziker, S., Gisler, J., Bortolami, G., Trotsiuk, V.,
  Meusburger, K., Hug, C., Rigling, A., Gessler, A. & Grossiord, C. *Disentangling atmospheric and soil
  drought: A new stand-level manipulation approach for mature forests.* Manuscript under review at New
  Phytologist.

### Processing — in-canopy data (`_ic_`)

Measurements were aggregated to one value per parameter and timestamp using the median across available
sensors (circular median for wind direction; missing wind-direction values were then filled by circular
interpolation between the preceding/following aggregated values). OPERATION_STATUS indicates whether the
VPD reduction system was operating (0 = not operating, 1 = operating): a timestamp was classified as
operational when water pressure was >60 bar and at least one valve was open (valve state < −0.99).

Quality flags: 1 = sufficient valid measurements, no issue; 2 = <50% of expected measurements available
(for OPERATION_STATUS: an individual valve state deviates from the median valve state by >0.4 while
pressurized >60 bar); 3 = only one valid measurement available.

Comments: `less_than_50%_valid_measurement_values`, `only_1_valid_measurement_value`; for
OPERATION_STATUS, `treatment_deviation_<scaffold(s)>` (e.g. `treatment_deviation_PFY_SC03_PFY_SC10`)
identifies individual scaffolds whose valve state deviated from the others during system operation —
trees around these scaffolds were consequently exposed to VPD conditions that deviated from the intended
treatment.

### Processing — over-canopy data (`_oc_`)

Parameter-specific processing (see `envidat_resource_description.md` for the column-level summary; full
detail below):

- **Precipitation:** gaps ≤2 min linearly interpolated; longer gaps within a 10-min block filled from
  MeteoSwiss Sierre 10-min precipitation totals, divided equally across the ten 1-min values.
  Quality flags: 1 = measured, no issue; 2 = interpolated (≤2 min gap); 3 = estimated from MeteoSwiss
  Sierre. Comments: `linear_interpolation`, `meteoswiss_sierre_10min`.
- **Air temperature / relative humidity:** gaps ≤2 min linearly interpolated; longer gaps estimated from
  aggregated in-canopy ambient measurements via an additive correction (interpolated for gaps ≤3 h;
  three-section approach for gaps >3 h). Quality flags: 1 = measured; 2 = interpolated (≤2 min);
  3 = estimated from fitted in-canopy ambient. Comments: `linear_interpolation`,
  `fitted_in_canopy_ambient`.
- **VPD:** same gap structure as TA/RH, using a multiplicative correction factor when VPD ≥0.5 kPa or an
  additive offset otherwise. Same quality-flag/comment scheme as TA/RH.
- **Global radiation / PAR:** measured values <4 set to 0 (`nighttime_noise_removed`, global radiation
  only) to account for low-light sensor noise. Gaps ≤10 values linearly interpolated; longer gaps
  estimated as the mean of the nearest valid same-time-of-day observations (quality_flag <3) before and
  after. Quality flags: 1 = measured; 2 = interpolated (≤10 values); 3 = same-time-of-day mean. Comments:
  `nighttime_noise_removed`, `linear_interpolation`,
  `mean_of_previous_and_following_valid_messval_same_time_of_day`.
- **Wind speed:** gaps ≤2 min linearly interpolated; longer gaps estimated from in-canopy ambient wind
  speed via a correction (multiplicative when in-canopy WS ≥0.4 m/s, else additive); negative results
  from the correction set to 0. Quality flags: 1 = measured; 2 = interpolated (≤2 min); 3 = estimated
  from fitted in-canopy ambient. Comments: `linear_interpolation`, `fitted_in_canopy_ambient`.
- **Wind direction:** gaps ≤2 min filled by circular linear interpolation (accounting for the 0°/360°
  boundary); longer gaps estimated from in-canopy ambient wind direction via an additive circular
  correction (three-section approach for gaps >3 h, using the shortest angular difference when
  interpolating). If a circular mean is undefined because the two reference values are diametrically
  opposed (e.g. 90° and 270°), the first value is nudged by +1° and the mean recalculated. Final
  estimates are circularly rounded to integer degrees (0–359). Quality flags: 1 = measured;
  2 = circular interpolation (≤2 min); 3 = estimated from fitted in-canopy ambient circular correction.
  Comments: `linear_interpolation`, `fitted_in_canopy_ambient`.

### Processing — irrigation data

Irrigation measurements ≤1 mm were excluded (non-relevant, maintenance activities). Irrigation generally
occurs overnight (~3.5 h); events outside this window are assigned to a day as: ≤19:00 UTC → same day,
>19:00 UTC → following day. Daily sums were calculated per sub-plot, then the median of the four sub-plot
sums (sub-plots 2, 3, 6, 7; scaffolds 3, 4, 10, 14, 15, 901) taken as the final daily sum, timestamped
02:00 UTC.

Quality flags (consistency among the four sub-plots, 10% deviation threshold vs. the daily median):
1 = no issue; 2 = one or two sub-plot values deviate >10%; 3 = more than two sub-plot values deviate >10%.
Comment: `treatment_deviation_pl<N>_pl<M>` identifies the deviating sub-plot(s); empty if no deviation.

### Limitations

- Gap-filled (`estimated`) values are model/reference-derived, not direct measurements — treat
  `quality_flag` > 1 rows accordingly for analyses sensitive to measurement provenance.
- Over-canopy gap filling for TA/RH/VPD/WS/WD relies on the in-canopy ambient signal as a reference;
  periods where the in-canopy ambient signal is itself compromised will propagate into over-canopy
  estimates.
- In-canopy `_amb` vs `_manip` split only applies to parameters affected by the VPD manipulation system.

### Methods

- Database query: R, `rLWFpg`, `collapse`, `dplyr`
- See processing scripts: `meteorology_metadata.R`, `issue_19_meteo_ic_derived_messvar.R`

---

## 4. Authors

| # | First name | Last name | Email | Affiliation | ORCID |
|---|------------|-----------|-------|-------------|-------|
| 1 | Stefan | Hunziker | | WSL — Swiss Federal Institute for Forest, Snow and Landscape Research | 0000-0001-6900-5684 |
| 2 | Jonas | Gisler | | WSL — Swiss Federal Institute for Forest, Snow and Landscape Research | |
| 3 | Volodymyr | Trotsiuk | volodymyr.trotsiuk@wsl.ch | WSL — Swiss Federal Institute for Forest, Snow and Landscape Research | |
| 4 | Marcus | Schaub | | WSL — Swiss Federal Institute for Forest, Snow and Landscape Research | |

*Emails not supplied for Hunziker/Gisler/Schaub — fill in before submission.*

---

## 5. Geospatial information

- **Site:** Pfynwald, Valais, Switzerland
- **Latitude / Longitude:** 46.302°N, 7.612°E (approximate centroid)
- **Elevation:** ~615 m a.s.l.

---

## 6. Time information

| Type | Start | End |
|------|-------|-----|
| **Created** | 2026-08-22 | |
| **Collected** | 2024-01-01 | 2025-12-31 |
| **Processing date** | 2026-08-25 | |

---

## 7. Processing & provenance

- **Source data:** LWF database, `ada.v_messvar`, Pfynwald VPDrought meteorology installations —
  full traceability via `messvar_id` in each file's metadata companion.
- **Script / repository:** `meteorology_metadata.R`, `issue_19_meteo_ic_derived_messvar.R` — <add
  repository URL or zip location>
- **Software & version:** R (>= 4.4), `rLWFpg`, `collapse`, `readr`, `dplyr`
- **Aggregation:** native 1-minute (oc, ic) / 1-day (irrigation); ic values are additionally
  spatially aggregated (median, circular median for wind direction) across in-canopy sensors
- **QC criteria / gap filling:** parameter-specific, see Description §3 above
- **Corrections:** in-canopy-ambient-derived corrections applied to oc TA/RH/VPD/WS/WD gap filling
  (see §3); nighttime radiation noise removal for oc global radiation
- **Related publication:** Schaub, M., Hunziker, S., Gisler, J., Bortolami, G., Trotsiuk, V.,
  Meusburger, K., Hug, C., Rigling, A., Gessler, A. & Grossiord, C. *Disentangling atmospheric and soil
  drought: A new stand-level manipulation approach for mature forests.* Manuscript under review at New
  Phytologist.

---

## 8. Funding

- **Institution:** <Swiss National Science Foundation / WSL internal / other>
- **Project / grant number:** VPDrought — <grant number>
- **Link:** https://www.wsl.ch/en/projects/vpdrought/

---

## 9. Organization & license

- **Organization:** WSL — Swiss Federal Institute for Forest, Snow and Landscape Research
- **License:** CC-BY 4.0 *

---

## 10. Resources

| File | Format | Description |
|------|--------|-------------|
| `pfynwald_vpdrought_meteorology_ic_<YEAR>.txt` | TXT | In-canopy meteorology, 1-minute, ambient/manipulated |
| `pfynwald_vpdrought_meteorology_metadata_ic_<YEAR>.txt` | TXT | Metadata for in-canopy variables |
| `pfynwald_vpdrought_meteorology_oc_<YEAR>.txt` | TXT | Over-canopy meteorology, 1-minute |
| `pfynwald_vpdrought_meteorology_metadata_oc_<YEAR>.txt` | TXT | Metadata for over-canopy variables |
| `pfynwald_vpdrought_meteorology_irrigation_<YEAR>.txt` | TXT | Daily irrigation amount |
| `pfynwald_vpdrought_meteorology_metadata_irrigation_<YEAR>.txt` | TXT | Metadata for irrigation variable |
| `metadata_VPDrought_Pfynwald_meteorology.md` | MD | This document |
