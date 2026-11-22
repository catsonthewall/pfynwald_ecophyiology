# Pfynwald satellite acquisition and analysis notes

## Reproducing the acquisition

The script `scripts/acquire_satellite.py` retrieves public Microsoft Planetary
Computer STAC items, product metadata and small native-grid cloud-optimized
GeoTIFF windows. The package contains real satellite observations, not
synthetic imagery. Acquisition does not require an Earth Engine account or
an API key.

The completed acquisition contains 6 Sentinel-2 scenes, 8 Landsat 8/9 L2SP
scenes and 1 ESA WorldCover 2021 item: **113 native cropped GeoTIFF assets**.
All 113 assets were opened and read successfully.
`data/satellite/asset_inventory.csv` records the SHA256 of each crop. The
source catalogs, Sentinel-2 product XML files and per-item manifest are also
included under `data/satellite/`.

Run these commands from the **package root**, after installing the supplied
dependencies. Existing crops are reused:

```bash
python scripts/acquire_satellite.py --out data/satellite --workers 4
```

An optional, verified public-data transport uses Python urllib and bounded
HTTP 206 range requests:

```bash
python scripts/acquire_satellite.py --out data/satellite --workers 4 --urllib-range
```

Keep `scripts/http_range_reader.py` beside the acquisition script. Both
transports retain TLS verification. Anonymous read tokens remain in memory;
signed URLs are not saved. The downloader reads small windows rather than
complete satellite tiles. The tested acquisition dependencies include
Python 3.12, rasterio 1.5.2, pyproj 3.8.0 and NumPy; the package dependency
file covers the complete offline analysis workflow.

## Site and selected dates

The centre is the precise VPDrought study coordinate reported in the primary
paper, https://doi.org/10.1111/nph.71661:

- 46°18′7″ N, 7°36′40″ E.
- Decimal latitude 46.3019444444, longitude 7.6111111111.

The 2 km square is a landscape-context region, not an experimental plot
boundary. Descriptive summaries use a 500 m radius core. Its pixels must not
be assigned to experimental treatments without actual treatment polygons.
The historical rounded coordinate 46.3, 7.6 is substantially displaced from
this point.

The six selected Sentinel-2 dates are 4, 14, 19 and 29 July, and 6 and
23 August 2024. This is a small teaching and feasibility selection, not an
unbiased sample of summer weather. Catalog results for all July–August
acquisitions are retained.

The eight Landsat 8/9 L2SP dates are 5, 13, 21 and 29 July, and 6, 14, 22 and
30 August 2024. Acquisition availability does not guarantee usable pixels.
A failed quality screen is retained as a result rather than replaced with a
forced temperature value.

## Units and harmonization

For these Planetary Computer Sentinel-2 products, the saved source XML
specifies `BOA_QUANTIFICATION_VALUE = 10000` and `BOA_ADD_OFFSET = -1000`.
Mask stored DN 0 before conversion. Optical surface reflectance is:

```text
reflectance = DN × 0.0001 − 0.1
```

Do not scale the scene classification layer (SCL). Per-band calibration is
recorded in `data/satellite/manifest.json`. These Planetary Computer COGs
contain raw ESA DN; their STAC assets do not provide the reflectance scale
and offset through `raster:bands`.

This convention differs from Earth Engine's
`COPERNICUS/S2_SR_HARMONIZED`, whose values have already been shifted to the
harmonized convention and require only multiplication by 0.0001. Do not
subtract 1000 a second time from that collection. Provider conventions must
be checked separately.

Official explanations:

- https://sentiwiki.copernicus.eu/web/s2-products
- https://github.com/microsoft/PlanetaryComputer/issues/134
- https://github.com/microsoft/PlanetaryComputer/issues/513

Landsat Collection 2 Level-2 calibration is recorded per asset:

| Asset | Interpretation and conversion |
|---|---|
| `red`, `nir08`, `swir16` | Surface reflectance = DN × 0.0000275 − 0.2; DN 0 is invalid. |
| `lwir11` | `ST_B10` surface temperature, not raw brightness temperature; K = DN × 0.00341802 + 149; °C = K − 273.15. DN 0 is invalid. |
| `qa` | `ST_QA` product-estimated temperature uncertainty = stored value × 0.01 K; negative fill is invalid. |
| `cdist` | `ST_CDIST` distance to cloud = stored value × 0.01 km; negative fill is invalid. |
| `qa_pixel`, `qa_radsat` | Integer bitfields; do not scale. |

USGS references:

- https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature
- https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
- https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products
- https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites

## Sentinel-2 regridding and quality screening

The analysis uses the native B8A 20 m grid as its reference. B04 and B08
10 m values are averaged to that grid before calculating indices. B05,
B8A and B11 are already 20 m bands. Affine transforms and CRS information
control alignment; arrays are not aligned by reshaping. SCL is reprojected
by nearest neighbour.

The indices are:

```text
NDVI = (B08 averaged to 20 m − B04 averaged to 20 m)
       / (B08 averaged to 20 m + B04 averaged to 20 m)
NDRE = (B8A − B05) / (B8A + B05)
NDMI = (B8A − B11) / (B8A + B11)
```

The NDMI implementation uses narrow NIR B8A. A B08-based NDMI is a different
band choice and should not be silently substituted. The implementation
checks finite reflectances in the range 0–1 for the index bands and guards
against invalid denominators. It masks failed values rather than clipping
them to a desired range.

The final optical mask combines all of the following:

1. Independent ESA WorldCover 2021 tree-cover fraction **at least 0.8**.
2. SCL class **4 or 5**.
3. Exclusion of SCL cloud/shadow classes **3, 8, 9 and 10**, expanded by
   **one neighbouring 20 m grid cell**. The implementation uses one iteration
   of the default four-connected `scipy.ndimage.binary_dilation` neighbourhood.
4. Valid calibrated index-band reflectances.

The 500 m core is then applied for the reported summaries. SCL class 4 alone
means vegetation, not specifically forest; the independent WorldCover mask
provides the tree-cover restriction. Retaining SCL class 5 does not allow
all nonvegetated land into the forest summaries because the tree-cover
fraction condition is also required. This one-cell cloud buffer cannot
ensure that every thin-cloud or adjacency effect is removed.

Whole-tile cloud percentage is not a substitute for ROI pixel QA. The
configured scene coverage gate is at least 70% of potential core forest
pixels and at least 30 retained cells. These are declared pilot-analysis
choices, not sensor specifications or validated drought thresholds.

## Landsat screening and thermal spatial support

Base pixel QA excludes `QA_PIXEL` bits 0 (fill), 1 (dilated cloud), 2 (cirrus),
3 (cloud), 4 (cloud shadow), 5 (snow) and 7 (water). It additionally requires
`QA_RADSAT == 0` and valid surface-temperature DN.

The independent WorldCover tree-cover fraction must be at least 0.8.
Thermal summaries use the 500 m core and a **60 m forest-interior distance**,
calculated from the thresholded forest mask on the Landsat grid. This edge
exclusion is a heuristic to reduce mixed pixels. It is not a measured
thermal point-spread function and does not establish pure canopy sampling.

Landsat TIRS has approximately **100 m native thermal support**, delivered
on a **30 m grid**. Output cells are therefore not independent 30 m thermal
observations. Forest classification within one 30 m cell cannot establish
that the full thermal footprint contains only forest.

Two output categories are deliberately kept distinct:

| Output category | Screening and interpretation |
|---|---|
| Strict thermal analysis | Base QA and forest/core/interior support, valid nonnegative uncertainty, **ST_QA ≤ 2 K** and **ST_CDIST ≥ 1 km**. These are the declared strict pilot thresholds. |
| `baseQA_CONTEXT` | Separately generated diagnostic LST after base QA and forest-interior screening. Context summaries use the core and require valid nonnegative ST_QA, but apply **no upper ST_QA threshold and no minimum cloud-distance threshold**. They do not qualify as accepted strict thermal observations. |

**The executed strict screen retained zero pixels in all eight Landsat
acquisitions.** The 2 K uncertainty rule was not relaxed to obtain a thermal
result. The separately named `baseQA_CONTEXT` maps and tables illustrate
the available temperature patterns and their uncertainty; they must remain
labelled as diagnostic context. They are not substitutes for successful
strict screening or ground validation.

The sensitivity table records how alternative uncertainty and cloud-distance
choices change coverage. These alternatives are analysis choices, not
universal USGS requirements. `ST_QA` is a product uncertainty estimate, not
an observed error against a field sensor. **July 21 provides no usable core
thermal context even under base QA**, because its core pixels are cloud
flagged.

## WorldCover interpretation and attribution

The source item is `ESA_WorldCover_10m_2021_v200_N45E006`, asset `map`;
class 10 denotes tree cover. For categorical display, use nearest-neighbour
reprojection. For the satellite-pixel tree-cover fraction, convert class 10
to a binary mask and area-average it to the target grid. The implemented
threshold is a fraction of at least 0.8.

This is a 2021 land-cover classification, not validated 2024 forest cover,
species identification, crown delineation or canopy closure. A fraction of
0.8 means that at least 80% of the underlying mapped area is classified as
tree cover; it does not mean measured canopy closure is 80%.

References:

- https://esa-worldcover.org/en/data-access
- https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200

Attribution: © ESA WorldCover project 2021 / Contains modified Copernicus
Sentinel data (2021) processed by ESA WorldCover consortium. Copernicus
Sentinel data (2024); Landsat data courtesy of USGS; accessed via Microsoft
Planetary Computer. WorldCover 2021 is CC BY 4.0. Preserve the original
notices supplied with the data.

## Alignment to field measurements

The actual Sentinel-2 July 19 timestamp is
`2024-07-19T10:20:21.024Z`. The Landsat July 21 timestamp is
`2024-07-21T10:16:29.731228Z`.

The EnviDat `messtime` values are timezone-naive, and the available source
READMEs do not specify the clock convention. UTC, CET or CEST cannot be
selected by assumption. The implementation therefore evaluates three
provisional source-clock scenarios: UTC + 0, + 1 and + 2 hours.

For each scenario, the matching window is **±15 minutes** around the
corresponding source-clock overpass time. The aggregation is:

1. Calculate each available scaffold's mean from the accepted field bins
   within its overpass window.
2. Calculate the treatment-group mean with **equal weight for the available
   scaffold-window means**.
3. Retain the scaffold counts and accepted-bin information so that missing
   coverage remains visible.

These overpass summaries are means, not ±30-minute medians or a pooled
average that gives a scaffold more weight merely because it has more rows.
The clock scenarios are a matching-sensitivity exercise, not observations
of a temporal trend. The source clock and sensor footprint remain
unverified; the results are explicitly provisional.

No numerical satellite-versus-ground validation claim should use an
unverified clock or footprint. July 21 also fails satellite cloud QA, so no
thermal satellite-field bias or RMSE is calculated for it. Nearly
simultaneous Sentinel-2 and Landsat acquisitions exist on July 29, but that
date lies outside the supplied July 15–21 field subset.

## Observed checks and practical limits

Before applying the independent WorldCover mask, the July 19 Sentinel-2
500 m core contains 1,962 native 20 m SCL pixels: 1,744 in class 4 and 218
in class 5. No cloud, shadow or snow class occurs in that core, despite
approximately 18.43% whole-tile cloud metadata.

For July 21 Landsat 8, all 874 delivered 30 m core pixels have
`QA_PIXEL = 55052` and fail the clear-land mask. Zero clear core pixels
remain before forest masking, so neither a strict thermal result nor a
usable base-QA core context is available.

Across the full August 30 Landsat 9 crop, before the forest-only core
restriction, the 5th, 50th and 95th percentiles of ST_QA are 2.97, 3.39 and
4.5245 K. Corresponding ST_CDIST percentiles are 0.31, 1.06 and 1.7245 km.
These values explain why reporting uncertainty and coverage is essential;
they do not justify changing the declared strict rule after inspecting the
results.

Six optical scenes and eight thermal acquisitions are insufficient for a
train/test machine-learning model of forest vulnerability or for causal
drought attribution. The useful result is an auditable preprocessing
pipeline, an explicit quality and coverage assessment, exploratory spectral
indicators and separately labelled thermal context. Field canopy infrared
measurements and satellite land-surface temperature have different physical
sampling supports and are not interchangeable.
