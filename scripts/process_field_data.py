#!/usr/bin/env python3
"""Audit and normalize the supplied Pfynwald public learning subset.

No timestamp timezone is inferred. All field timestamps remain naive source
clocks. Satellite matching is explicitly a sensitivity exercise under three
alternative, unverified common-clock assumptions.

Example:
    python process_field_data.py --input data/field --output outputs/field
Requires Python >=3.10, pandas and numpy. No online services are needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


AIR_CONDITION = {
    "control": "amb", "irrigation": "amb", "roof": "amb",
    "irrigation_vpd": "manip", "roof_vpd": "manip",
}
EXPECTED_UNITS = {
    "TA_oc": "degC", "RH_oc": "%", "VPD_oc": "kPa",
    "WS_oc": "m/s", "WD_oc": "deg", "GlobalRad_oc": "W/m2",
    "PAR_oc": "µmol/s/m2", "RaineH3_amount_dif": "mm",
    "TA_ic_amb": "degC", "TA_ic_manip": "degC",
    "RH_ic_amb": "%", "RH_ic_manip": "%",
    "VPD_ic_amb": "kPa", "VPD_ic_manip": "kPa",
    "WS_ic": "m/s", "WD_ic": "deg", "OPERATION_STATUS": "number",
}
SATELLITE_EVENTS = {
    "Sentinel2_20240719": "2024-07-19T10:20:21.024000Z",
    "Landsat8_20240721": "2024-07-21T10:16:29.731228Z",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def read_stream(folder: Path, prefix: str, key: str = "messvar_id"):
    candidates = list(folder.glob(f"{prefix}_20*.csv"))
    if len(candidates) != 1:
        raise ValueError(f"Expected one dated {prefix} CSV, found {candidates}")
    file = candidates[0]
    raw = pd.read_csv(file)
    metadata = pd.read_csv(folder / f"{prefix}_metadata.csv")
    if metadata[key].duplicated().any():
        raise ValueError(f"Duplicate metadata key in {prefix}")
    if raw.duplicated([key, "messtime"]).any():
        raise ValueError(f"Duplicate measurement key and timestamp in {prefix}")
    raw["source_time_naive"] = pd.to_datetime(raw["messtime"], errors="raise")
    if raw["source_time_naive"].dt.tz is not None:
        raise ValueError("This subset workflow expects source-naive timestamps")
    missing_ids = set(raw[key]) - set(metadata[key])
    if missing_ids:
        raise ValueError(f"Unmapped measurement IDs in {prefix}: {missing_ids}")
    joined = raw.merge(metadata, on=key, validate="many_to_one", suffixes=("", "_metadata"))
    return file, raw, metadata, joined


def source_quality(raw: pd.DataFrame) -> dict:
    return {
        "rows": int(len(raw)),
        "quality_flags": raw.get("quality_flag", pd.Series("not_provided", index=raw.index)).astype(str).value_counts().to_dict(),
        "value_types": raw["valtype"].value_counts().to_dict(),
        "first_source_timestamp": str(raw["source_time_naive"].min()),
        "last_source_timestamp": str(raw["source_time_naive"].max()),
    }


def circular_mean_deg(series: pd.Series) -> float:
    angles = np.deg2rad(series.to_numpy(float))
    x, y = np.mean(np.cos(angles)), np.mean(np.sin(angles))
    if np.hypot(x, y) < 1e-10:
        return np.nan
    return float(np.rad2deg(np.arctan2(y, x)) % 360)


def aggregate_meteorology(joined: pd.DataFrame, min_minutes: int):
    for name, group in joined.groupby("imp_name"):
        observed_units = set(group["varunit_symbol"].dropna())
        if name not in EXPECTED_UNITS or observed_units != {EXPECTED_UNITS[name]}:
            raise ValueError(f"Unexpected units for {name}: {observed_units}")
    # corrected radiation values and derived in-canopy spatial aggregates are
    # retained. Gap-filled estimates are excluded from the primary comparison.
    valid = joined.loc[
        (joined["quality_flag"] == 1)
        & joined["valtype"].isin(["observed", "corrected", "derived"])
        & joined["messval"].notna()
    ].copy()
    valid["source_bin"] = valid["source_time_naive"].dt.floor("10min")
    rows = []
    for (name, time), group in valid.groupby(["imp_name", "source_bin"], sort=True):
        count = int(group["source_time_naive"].nunique())
        values = group["messval"]
        if name.startswith("WD_"):
            value = circular_mean_deg(values)
        elif name == "RaineH3_amount_dif":
            value = float(values.sum())
        else:
            value = float(values.mean())
        rows.append({"source_time_naive": time, "imp_name": name,
                     "value": value if count >= min_minutes else np.nan,
                     "accepted_minutes": count})
    aggregate = pd.DataFrame(rows)
    values = aggregate.pivot(index="source_time_naive", columns="imp_name", values="value")
    counts = aggregate.pivot(index="source_time_naive", columns="imp_name", values="accepted_minutes")
    values = values.add_prefix("met_")
    counts = counts.add_prefix("accepted_minutes_")
    table = values.join(counts).reset_index()
    quality_table = joined.groupby(["imp_name", "quality_flag", "valtype"], dropna=False).size().rename("rows").reset_index()
    audit = {"quality_by_variable": as_records(quality_table),
             "accepted_source_rows": int(len(valid)),
             "rejected_source_rows": int(len(joined)-len(valid)),
             "incomplete_variable_bins": int((aggregate["accepted_minutes"] < min_minutes).sum())}
    return table, audit


def vpd_from_t_rh(temperature_c, relative_humidity_pct):
    """FAO-56 saturation-vapour-pressure equation; returns kPa."""
    return 0.6108 * np.exp(17.27 * temperature_c / (temperature_c + 237.3)) * (1 - relative_humidity_pct / 100)


def scaffold_summaries(field: pd.DataFrame, radiation_threshold: float):
    key = ["treatment", "scaffold_id", "messvar_id"]
    metrics = ["Tcan_C", "Tair_above_C", "Tair_within_group_C",
               "deltaT_above_C", "deltaT_within_group_C",
               "VPD_above_reported_kPa", "VPD_within_group_reported_kPa",
               "global_radiation_W_m2", "wind_above_m_s"]
    subsets = {"all_times": field,
               f"radiation_gt_{radiation_threshold:g}_W_m2": field.loc[field["global_radiation_W_m2"] > radiation_threshold]}
    daily, weekly = [], []
    for name, frame in subsets.items():
        frame = frame.copy()
        frame["source_date"] = frame["source_time_naive"].dt.strftime("%Y-%m-%d")
        for groupkeys, target in [(key+["source_date"], daily), (key, weekly)]:
            means = frame.groupby(groupkeys)[metrics].mean().add_suffix("_mean")
            counts = frame.groupby(groupkeys).agg(n_canopy_observations=("Tcan_C", "size"),
                                                   n_source_dates=("source_date", "nunique"))
            out = means.join(counts).reset_index()
            out.insert(0, "time_filter", name)
            target.append(out)
    return pd.concat(daily, ignore_index=True), pd.concat(weekly, ignore_index=True)


def overpass_sensitivity(field: pd.DataFrame, window_minutes: int):
    rows = []
    metrics = ["Tcan_C", "Tair_above_C", "Tair_within_group_C",
               "deltaT_above_C", "deltaT_within_group_C", "VPD_above_reported_kPa",
               "VPD_within_group_reported_kPa", "global_radiation_W_m2",
               "wind_above_m_s", "operation_fraction"]
    for event, utc_text in SATELLITE_EVENTS.items():
        utc = pd.Timestamp(utc_text)
        for assumed_offset_h in [0, 1, 2]:
            center = utc.tz_convert("UTC").tz_localize(None) + pd.Timedelta(hours=assumed_offset_h)
            mask = field["source_time_naive"].between(center-pd.Timedelta(minutes=window_minutes), center+pd.Timedelta(minutes=window_minutes))
            subset = field.loc[mask]
            for (treatment, scaffold, sensor), group in subset.groupby(["treatment", "scaffold_id", "messvar_id"]):
                row = {"event": event, "overpass_utc": utc.isoformat(),
                       "assumed_field_clock_utc_offset_h": assumed_offset_h,
                       "source_window_center_naive": str(center),
                       "window_half_width_minutes": window_minutes,
                       "treatment": treatment, "scaffold_id": scaffold,
                       "messvar_id": sensor, "accepted_canopy_bins": int(len(group)),
                       "match_status": "provisional_unverified_clock_and_footprint"}
                row.update({f"{m}_mean": float(group[m].mean()) for m in metrics})
                rows.append(row)
    by_scaffold = pd.DataFrame(rows)
    keys = ["event", "overpass_utc", "assumed_field_clock_utc_offset_h", "treatment"]
    means = by_scaffold.groupby(keys)[[f"{m}_mean" for m in metrics]].mean()
    counts = by_scaffold.groupby(keys).agg(n_scaffolds=("scaffold_id", "nunique"),
                                           min_accepted_bins=("accepted_canopy_bins", "min"))
    by_treatment = means.join(counts).reset_index()
    by_treatment["weighting"] = "equal_weight_of_available_scaffold_window_means"
    by_treatment["match_status"] = "provisional_unverified_clock_and_footprint"
    return by_scaffold, by_treatment


def process_fields(data_dir: Path, output_dir: Path, min_minutes=8, window_minutes=15, radiation_threshold=200.):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = data_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    hash_checks = []
    for dataset in manifest.get("datasets", []):
        file = data_dir / dataset["subset_file"]
        digest = sha256(file)
        match = digest == dataset["subset_sha256"]
        hash_checks.append({"file": file.name, "sha256": digest, "matches_bundled_manifest": match})
        if not match:
            raise ValueError(f"Bundled subset checksum mismatch: {file.name}")

    canopy_file, canopy_raw, canopy_meta, canopy = read_stream(data_dir, "canopy")
    above_file, above_raw, above_meta, above = read_stream(data_dir, "meteo_above")
    inside_file, inside_raw, inside_meta, inside = read_stream(data_dir, "meteo_inside")
    if set(canopy_meta["varunit_symbol"]) != {"degC"}:
        raise ValueError("Canopy units must be degrees Celsius")
    if set(canopy_meta["treatment"]) != set(AIR_CONDITION):
        raise ValueError("Treatment labels changed; update documented mapping first")
    if canopy_meta["scaffold"].duplicated().any():
        raise ValueError("This starter expects one canopy measurement variable per scaffold")

    above_10, above_audit = aggregate_meteorology(above, min_minutes)
    inside_10, inside_audit = aggregate_meteorology(inside, min_minutes)
    met = above_10.merge(inside_10, on="source_time_naive", how="outer", validate="one_to_one")
    field = canopy.loc[(canopy["quality_flag"] == "good") & canopy["messval"].notna()].copy()
    field = field.rename(columns={"messval": "Tcan_C", "scaffold": "scaffold_id", "tree_id": "tree_id_metadata"})
    field = field.merge(met, on="source_time_naive", how="left", validate="many_to_one")
    field["air_reference_condition"] = field["treatment"].map(AIR_CONDITION)
    manipulated = field["air_reference_condition"] == "manip"
    rename = {"met_TA_oc": "Tair_above_C", "met_RH_oc": "RH_above_pct",
              "met_VPD_oc": "VPD_above_reported_kPa", "met_GlobalRad_oc": "global_radiation_W_m2",
              "met_PAR_oc": "PAR_umol_m2_s", "met_WS_oc": "wind_above_m_s",
              "met_WS_ic": "wind_within_m_s", "met_RaineH3_amount_dif": "rain_10min_mm",
              "met_OPERATION_STATUS": "operation_fraction"}
    field = field.rename(columns=rename)
    for original, name in [("TA", "Tair_within_group_C"), ("RH", "RH_within_group_pct"), ("VPD", "VPD_within_group_reported_kPa")]:
        field[name] = np.where(manipulated, field[f"met_{original}_ic_manip"], field[f"met_{original}_ic_amb"])
    field["deltaT_above_C"] = field["Tcan_C"] - field["Tair_above_C"]
    field["deltaT_within_group_C"] = field["Tcan_C"] - field["Tair_within_group_C"]
    for name, temp, rh in [("above", "Tair_above_C", "RH_above_pct"),
                           ("within_group", "Tair_within_group_C", "RH_within_group_pct")]:
        field[f"VPD_{name}_FAO_from_10min_means_kPa"] = vpd_from_t_rh(field[temp], field[rh])
        field[f"VPD_{name}_reported_minus_FAO_kPa"] = field[f"VPD_{name}_reported_kPa"] - field[f"VPD_{name}_FAO_from_10min_means_kPa"]
    field["clock_status"] = "source_clock_unresolved_same_clock_join_assumed"
    field["air_reference_status"] = "group_aggregate_within_and_single_station_above_not_crown_paired"
    field = field.sort_values(["source_time_naive", "scaffold_id"])
    field.to_csv(output_dir / "field_10min.csv", index=False)
    met.to_csv(output_dir / "meteorology_10min.csv", index=False)

    daily, weekly = scaffold_summaries(field, radiation_threshold)
    daily.to_csv(output_dir / "field_scaffold_daily.csv", index=False)
    weekly.to_csv(output_dir / "field_scaffold_week.csv", index=False)
    windows, treatment_windows = overpass_sensitivity(field, window_minutes)
    windows.to_csv(output_dir / "overpass_clock_sensitivity_by_scaffold.csv", index=False)
    treatment_windows.to_csv(output_dir / "overpass_clock_sensitivity_by_treatment.csv", index=False)

    # Keep optional physiology as its own table. A common scaffold is not proof
    # that the sampled foliage equals the radiometer footprint.
    leaf_file, leaf_raw, leaf_meta, leaf = read_stream(data_dir, "leaf_water_optional", key="meas_id")
    if set(leaf["varunit_symbol"]) != {"bar"}:
        raise ValueError("This subset's leaf water potential should be in bar")
    leaf["water_potential_MPa"] = leaf["messval"] * 0.1
    leaf["quality_status"] = "quality_flag_not_supplied"
    leaf["clock_status"] = "source_clock_unresolved"
    leaf.to_csv(output_dir / "leaf_water_optional_MPa.csv", index=False)

    input_files = sorted(data_dir.glob("*.csv"))
    input_info = [{"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in input_files]
    quality_by_sensor = canopy_raw.groupby(["messvar_id", "quality_flag"], dropna=False).size().rename("rows").reset_index()
    dictionary = []
    for label, meta in [("canopy", canopy_meta), ("meteo_above", above_meta), ("meteo_inside", inside_meta)]:
        for row in as_records(meta):
            dictionary.append({"stream": label, **row})
    pd.DataFrame(dictionary).to_csv(output_dir / "measurement_dictionary.csv", index=False)
    audit = {
        "purpose": "Reproducible exploratory processing, not a validated drought-effect experiment",
        "subset_hash_checks": hash_checks,
        "input_files": input_info,
        "sources": {"canopy": "https://doi.org/10.16904/envidat.776",
                    "meteorology": "https://doi.org/10.16904/envidat.798",
                    "leaf": "https://doi.org/10.16904/envidat.799"},
        "license": "CC-BY-4.0; original authors and original subset manifest retained",
        "software": {"pandas": pd.__version__, "numpy": np.__version__},
        "raw_quality": {"canopy": source_quality(canopy_raw), "meteo_above": source_quality(above_raw),
                        "meteo_inside": source_quality(inside_raw), "leaf": source_quality(leaf_raw)},
        "canopy_quality_by_measurement": as_records(quality_by_sensor),
        "meteorology_processing": {"above": above_audit, "inside": inside_audit},
        "rules": {
            "canopy": "Keep quality_flag good only. Raw outlier/bad rows remain in input files. No interpolation.",
            "meteorology": "Keep quality_flag 1 and observed/corrected/derived values; exclude estimates. Mean TA/RH/VPD/radiation/wind speed; sum rainfall; circular mean wind direction; mean operation status is an operating fraction.",
            "minimum_minutes_per_10min_bin": min_minutes,
            "bin_convention": "Floor 1-minute meteorology to left-labelled 10-minute source-clock bins. Canopy export interval convention unresolved; temporal alignment is provisional.",
            "source_clock": "Naive source time preserved. Same-clock joining is an assumption. Do not label UTC or Europe/Zurich without confirmation.",
            "within_air_mapping": AIR_CONDITION,
            "spatial_air_reference": "Inside air variables are spatially aggregated amb/manip groups, not per-crown measurements. Above-canopy station is Pfynwald TW8; metadata irrigation_stop is station context, not an extra treatment replicate.",
            "joins": "Canopy many-to-one by source_time_naive to unique meteorology bins; canopy metadata many-to-one by messvar_id. No scaffold cross-join and no invented plot ID.",
            "VPD_comparison": "Reported VPD is retained. FAO estimate uses aggregated 10-minute TA and RH; nonlinear averaging and the source calculation method may explain small differences.",
            "radiation_filter_W_m2": radiation_threshold,
            "radiation_filter_status": "Analyst-selected illustrative threshold, not a universal daylight or drought boundary.",
            "satellite_windows": {"events_utc": SATELLITE_EVENTS, "assumed_common_field_clock_offsets_hours": [0,1,2], "half_width_minutes": window_minutes,
                                  "meaning": "Alternative hypotheses only. They neither establish the timezone nor validate the satellite pixel. Crown footprints and treatment polygons are unavailable."},
            "physiology": "Only water-potential variables exist in supplied 2024 export. Convert bar to MPa by multiplying by0.1; preserve sign. Do not call this gas-exchange or stomatal-conductance data."},
        "limitations": [
            "15 radiometers/scaffolds are repeated measurement units, not15 independent plot-level treatment replicates. Each radiometer views one or two crowns.",
            "No verified crown coordinates, footprints, plot-level hierarchy, or treatment polygons supplied.",
            "No soil water measurements supplied; treatment label is not measured soil moisture.",
            "Leaf export includes roof_vpd although generic2024 protocol lists only three treatments; preserve discrepancy.",
            "The seven-day interval was chosen before treatment-effect analysis; it cannot establish seasonal drought vulnerability.",
            "Satellite cloud contamination, spatial support mismatch and unresolved clocks preclude a formal validation claim."],
        "outputs": {"good_canopy_rows": int(len(field)), "n_canopy_measurement_variables": int(field["messvar_id"].nunique()),
                    "n_scaffolds": int(field["scaffold_id"].nunique()), "n_treatments": int(field["treatment"].nunique()),
                    "n_dates": int(field["source_time_naive"].dt.date.nunique()),
                    "overpass_scaffold_scenario_rows": int(len(windows)), "leaf_rows": int(len(leaf))},
        "leaf_variables": sorted(leaf["varname_name"].unique().tolist()),
        "leaf_treatments": sorted(leaf["treatment"].unique().tolist()),
    }
    (output_dir / "field_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps(audit["outputs"], ensure_ascii=False, indent=2))
    return field, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Folder containing starter CSVs and original manifest")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-minutes", type=int, default=8)
    parser.add_argument("--window-minutes", type=int, default=15)
    parser.add_argument("--radiation-threshold", type=float, default=200.)
    args = parser.parse_args()
    if not 1 <= args.min_minutes <= 10:
        parser.error("--min-minutes must be between1 and10")
    if args.window_minutes <= 0:
        parser.error("--window-minutes must be positive")
    process_fields(args.input, args.output, args.min_minutes, args.window_minutes, args.radiation_threshold)


if __name__ == "__main__":
    main()
