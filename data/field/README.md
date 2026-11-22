# Pfynwald public data learning subset

This is an offline subset of publicly downloaded EnviDat files, not a completed analysis or a new experimental dataset. The fixed interval is 15–21 July 2024 inclusive (source timestamp clock). Selection was based on manageable size and overlapping instrument coverage, not a desired treatment contrast or effect size. All rows and quality flags within that period were retained.

## Provenance and license

- Canopy temperature: d'Odorico, P., Gisler, J., & Schaub, M. (2026). Pfynwald VPDrought experiment canopy temperature parameter. https://doi.org/10.16904/envidat.776
- Meteorology: Hunziker, S., Gisler, J., Trotsiuk, V., & Schaub, M. (2026). Pfynwald VPDrought experiment atmospheric parameters and manipulations. https://doi.org/10.16904/envidat.798
- Optional leaf water potential: Bortolami, G., Milano, A., Gisler, J., Schaub, M., & Grossiord, C. (2026). Pfynwald VPDrought experiment leaf gas exchange and water potential parameter. https://doi.org/10.16904/envidat.799

All three records specify CC-BY 4.0. Attribute the original authors, DOI, and the fact that this is a date-filtered subset. Stable source URLs, SHA-256 hashes, recorded file sizes, row counts and filter description are in manifest.json. Downloaded public ZIP signatures were checked. The full-source data and this subset have not been scientifically validated by the dataset creators for your analysis.

## Files and joins

- canopy_20240715_20240721.csv: 10-minute IR canopy temperatures. Join canopy_metadata.csv by messvar_id.
- meteo_above_20240715_20240721.csv: 1-minute above-canopy meteorology. Join meteo_above_metadata.csv by messvar_id.
- meteo_inside_20240715_20240721.csv: 1-minute spatially aggregated ambient/manipulated in-canopy meteorology and system operation. Join meteo_inside_metadata.csv by messvar_id.
- leaf_water_optional_20240715_20240721.csv: sparse leaf water potential campaign observations. Join leaf_water_optional_metadata.csv by meas_id. Despite the dataset's broad title, the downloaded 2024 file contains only day/predawn leaf water potential, not gas-exchange observations.
- *_metadata.csv maps IDs to units and context. Original README files are included unchanged and can contain incomplete metadata placeholders; those placeholders are not filled here.

Do not conflate messvar_id (sensor/measurement variable) with an independent biological replicate. Fifteen canopy sensors cover five named treatments and three scaffolds per treatment; each IR sensor measures a spatial aggregate over one or two crowns. Precise crown boundaries, projected coordinates, and experimental plot hierarchy are not included.

## Variable mapping

Above canopy: imp_name TA_oc (degC), RH_oc (%), VPD_oc (kPa), GlobalRad_oc (W/m2), PAR_oc (micromol/s/m2), WS_oc (m/s), WD_oc (degrees), RaineH3_amount_dif (mm per minute record).

Inside canopy: TA_ic_amb and TA_ic_manip (degC), RH_ic_amb and RH_ic_manip (%), VPD_ic_amb and VPD_ic_manip (kPa), WS_ic (m/s), WD_ic (degrees), OPERATION_STATUS (0/1).

Canopy: messval is degC; treatment labels are control, irrigation, irrigation_vpd, roof, roof_vpd. For exploratory matching of ambient versus VPD-reduced air references, control/irrigation/roof map to amb and irrigation_vpd/roof_vpd map to manip. This is based on documented treatment naming; the in-canopy air series are spatial aggregates, not sensors paired to each individual crown.

Leaf potential: metadata units are bar. Preserve signs; convert bar to MPa by multiplying by 0.1. Not every measured branch/tree matches the single tree_id listed for the IR field of view. Matching only by scaffold is an approximate spatial association, not proof of measuring the same foliage.

## Quality controls

- Primary canopy view: quality_flag == good. Exclude bad if encountered when extending the time series. outlier can be physically plausible; retain and inspect it for a sensitivity analysis rather than silently deleting it from the source.
- Primary meteorology view: quality_flag == 1, inspect valtype and comments. Flags 2 and 3 have variable-specific meanings. Above-canopy data may be corrected/estimated; values inferred from in-canopy measurements are not an independent meteorological reference.
- Aggregate 1-minute meteorology only after QC. For a 10-minute comparison report how many accepted minutes support each bin (e.g. require >=8/10 as an explicitly analyst-chosen completeness rule).
- Do not average wind direction arithmetically. Sum precipitation instead of averaging. OPERATION_STATUS mean is an operating fraction, not a binary state; label it accordingly.
- The exact interval labelling of the exported 10-minute canopy means is not explicitly documented in the included README. Any alignment using floor-based 10-minute bins is a working convention, requiring sensitivity to shifting bins by 10 minutes.

## Time handling is deliberately unresolved

messtime is stored as a naive timestamp in these exports. Included canopy, meteorology and leaf README files do not explicitly state a timezone; irrigation aggregation describes UTC, but this alone does not establish the clock of every stream. Do not silently assign UTC or Europe/Zurich. Preserve source clocks, flag cross-stream timestamp equality as provisional, and verify conventions before formal matched inference. Use within-stream QC first. For exploratory matched figures, document the same-clock assumption and test shifts of +/-1 and +/-2 hours. These tests assess sensitivity and do not prove the correct timezone.

TreeNet data are not in this starter. Its public record explicitly specifies fixed CET (UTC+1, without DST), illustrating why different sources must be checked independently.

## Suggested first deliverables

1. A data dictionary and quality/coverage plot for all sensors.
2. A seven-day canopy-temperature plot by individual sensor, with raw flags retained.
3. Conditional exploratory plots of canopy-minus-air temperature versus VPD, stratified by radiation and air-reference choice, with the clock assumption stated.
4. An analysis note explaining repeated measurements, possible pseudo-replication, sparse physiological observations, and limits on causal interpretation.

For a serious treatment analysis, extend to the full growing season, verify treatment start dates and operation periods, clarify plot-level replication and clock conventions, and include actual soil/physiological observations. This small subset is sufficient for learning the workflow, not for establishing drought vulnerability or intervention effects.

## Inspect the export rather than assuming the catalogue describes every row

In the seven-day optional leaf-water subset, measured values are already negative: daytime water potential ranges from -21.01 to -3.90 bar (256 rows); predawn water potential ranges from -6.90 to -4.08 bar (24 rows). Multiplication by 0.1 converts these recorded values to MPa without changing sign. These are diagnostic ranges, not treatment-effect results.

There is a protocol/metadata discrepancy to retain in the audit log: the general 2024 description lists three treatments, but the actual 2024 leaf-water export and metadata include roof_vpd as well as irrigation, roof, and irrigation_vpd in this selected week. Do not silently discard the fourth group or claim the generic campaign description fully resolves its provenance. Also, the water-potential instrument timestamp clock is not explicitly specified in the accompanying metadata.
