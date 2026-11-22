# Dataset Metadata — VPDrought Pfynwald leaf gas exchange and water potential

---

## 1. Title

**Title:** Leaf gas exchange and water potential data, Pfynwald irrigation experiment (VPDrought), 2024–2025

---

## 2. Keywords

- VPDrought
- Pfynwald
- Ecophysiology
- Drought
- Leaf gas exchange
- Assimilation (A)
- Stomatal conductance (gs)
- Leaf water potential (Ψleaf)

---

## 3. Description

### Dataset content

Data were collected in one-week measurement campaigns each month, from May to September, in both 2024
and 2025. The measurement protocol changed slightly between the two years:

- **2024:** n = 2 scaffolds per treatment, treatments *irrigation-ambient VPD*, *irrigation-reduced VPD*,
  *roof-ambient VPD*. Diurnal dynamics were followed hourly from pre-dawn (~5:00) to late afternoon
  (~17:00). Leaf gas exchange (CO₂ assimilation A, leaf transpiration E, stomatal conductance gs) was
  measured with a portable photosynthesis system (LI-6800, Li-Cor), using locally measured ambient
  light, temperature, and relative humidity set in the cuvette; each measurement followed a 5–15 minute
  adaptation period. Every hour, a branchlet (1- and 2-year-old needles) was collected to measure leaf
  water potential.
- **2025:** n = 3 scaffolds per treatment, treatments *irrigation-ambient VPD*, *irrigation-reduced VPD*,
  *roof-ambient VPD*, *control*. Leaf gas exchange was measured twice a day under ambient temperature and
  relative humidity with saturated light conditions. Leaf water potential was measured at pre-dawn,
  midday, and late afternoon.

### Processing steps

1. Raw retrieval from the LWF database (`ada.v_messvar`) and from campaign data files, joined by
   `tree_id` and variable name.
2. Installation/scaffold/treatment context attached via `ada.v_messvar`; for a subset of trees not
   linked to an installation record in the database, scaffold/treatment were filled from a manually
   supplied mapping confirmed by the data owner (see `gas_waterpotential_metadata.R`).
3. Tree attributes (species, DBH, height) joined from `tre.v_tree_info`.
4. No gap filling or value correction applied — all `valtype` = `observed`.

### Limitations

- `installation_id`/`installation_name` remain `NA` for some trees where the raw campaign data did not
  carry a database installation link; `scaffold`/`treatment` for these trees are supplied via the manual
  override rather than derived from an installation record.
- `height` is missing for a subset of trees (not recorded / not available in `tre.v_tree_info`).
- Measurement protocol differs between 2024 and 2025 (frequency, number of scaffolds per treatment,
  treatments covered, and water-potential sampling times) — see Dataset content above before comparing
  years directly.

### Methods

- Instrumentation: portable photosynthesis system LI-6800 (Li-Cor) for gas exchange; pressure chamber
  for leaf water potential (branchlet sampling).
- Database query and join: R, `rLWFpg`, `collapse`, `dplyr`
- See processing script: `gas_waterpotential_metadata.R`

---

## 4. Authors

| # | First name | Last name | Email | Affiliation | ORCID |
|---|------------|-----------|-------|-------------|-------|
| 1 | Giovanni | Bortolami | | WSL — Forest and Soil Ecology / EPFL — Plant Ecology Research Laboratory (PERL) | 0000-0001-7528-9644 |
| 2 | Arianna | Milano | | WSL — Forest and Soil Ecology / EPFL — Plant Ecology Research Laboratory (PERL) | 0009-0002-2424-4408 |
| 3 | Charlotte | Grossiord | | WSL — Forest and Soil Ecology / EPFL — Plant Ecology Research Laboratory (PERL) | 0000-0002-9113-3671 |

*Affiliation (both authors' institutions): Forest and Soil Ecology, WSL — Swiss Federal Institute for
Forest, Snow and Landscape Research, CH-8903 Birmensdorf, Switzerland; Plant Ecology Research Laboratory
(PERL), School of Architecture, Civil and Environmental Engineering (ENAC), EPFL, CH-1015 Lausanne,
Switzerland.*

*Emails not supplied — fill in before submission.*

---

## 5. Geospatial information

- **Site:** Pfynwald, Valais, Switzerland
- **Latitude / Longitude:** 46.302°N, 7.612°E (approximate centroid)
- **Elevation:** ~615 m a.s.l.

---

## 6. Time information

| Type | Start | End |
|------|-------|-----|
| **Collected / Processing period** | 2024-05-01 | 2025-09-30 |
| **Processing date** | last checked June 2026 | |

---

## 7. Processing & provenance

- **Source data:** LWF database, `ada.v_messvar`, Pfynwald VPDrought gas exchange/water potential
  campaigns — full traceability via `meas_id` in each file's metadata companion.
- **Script / repository:** `gas_waterpotential_metadata.R` — <add repository URL or zip location>
- **Software & version:** R (>= 4.4), `rLWFpg`, `collapse`, `readr`, `dplyr`
- **Aggregation:** none — raw hourly (2024) / twice-daily (2025) measurements
- **QC criteria / gap filling:** none applied; all values `observed`
- **Manual overrides:** scaffold/treatment for 8 trees not linked to an installation in the DB
  (tree_id 39, 239, 467, 604, 680, 754, 798, 1040), supplied directly by the data owner

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
| `pfynwald_vpdrought_gas_waterpotential_<YEAR>.txt` | TXT | Gas exchange & water potential measurements |
| `pfynwald_vpdrought_gas_waterpotential_metadata_<YEAR>.txt` | TXT | Metadata for measurement variables |
| `metadata_VPDrought_Pfynwald_gas_waterpotential.md` | MD | This document |
