EnviDat Resource Descriptions – Canopy Temperature
==================================================

pfynwald_vpdrought_canopy_temperature_<AGGREGATION>_<YEAR>.txt
--------------------------------------------------------------
Canopy temperature measurements from the Pfynwald VPDrought site. Data are exported by year and include timestamps, values, and quality information. Join to metadata via messvar_id.

Columns:
  messvar_id     - Unique measurement variable identifier
  aggregation    - Temporal resolution (for this file typically 10 min)
  messtime       - Timestamp (YYYY-MM-DD HH:MM:SS)
  messval        - Measured canopy temperature value
  valtype        - Value type (e.g. observed)
  quality_flag   - Quality flag


pfynwald_vpdrought_canopy_temperature_metadata_<YEAR>.txt
---------------------------------------------------------
Metadata for canopy temperature measurement variables at the Pfynwald VPDrought site. Includes variable, sensor, treatment, and tree context. Join to data via messvar_id.

Columns:
  messvar_id          - Unique measurement variable identifier
  installation_name   - Measurement installation/plot name
  variable_id         - Variable type identifier
  varname_name        - Variable name description
  varunit_symbol      - Measurement unit symbol
  varvpos             - Sensor vertical position (m)
  scaffold            - Scaffold identifier
  treatment           - Experimental treatment
  tree_id             - Tree identifier (if available)
  species             - Tree species (if available)
  dbh                 - Diameter at breast height (cm, if available)
  height              - Tree height (m, if available)
  sensor_id           - Sensor hardware identifier
  imp_name            - Internal import name
