#!/usr/bin/env python3
"""Verify the distributed input files using only Python's standard library.

Run from any working directory: python path/to/verify_inputs.py
Checks the satellite asset inventory and the four field subset checksums.
Full-source ZIP hashes in the field manifest are historical provenance records;
those original ZIP archives are not part of this distribution.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def local_name(value: str) -> str:
    """Accept one safe filename, not a path outside the package."""
    path = PurePosixPath(str(value).replace("\\", "/"))
    if len(path.parts) != 1 or path.name in {"", ".", ".."}:
        raise ValueError(f"Expected a plain filename: {value!r}")
    return path.name


def contained(path: Path, parent: Path) -> Path:
    result = path.resolve()
    try:
        result.relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError("Input path resolves outside its packaged data folder") from exc
    return result


def satellite_path(folder: Path, row: dict) -> Path:
    """Resolve the inventory by its raw/item/filename suffix, never an old host path."""
    recorded = PurePosixPath(str(row["path"]).replace("\\", "/"))
    item = local_name(row["item"])
    filename = local_name(recorded.name)
    if ".." in recorded.parts:
        raise ValueError("Parent-directory traversal is not allowed in the inventory")
    expected_suffix = ("raw", item, filename)
    if tuple(recorded.parts[-3:]) != expected_suffix:
        raise ValueError(f"Inventory path does not match raw/item/filename: {row['path']!r}")
    return contained(folder.joinpath(*expected_suffix), folder)


def check_file(path: Path, expected_hash: str, expected_bytes, label: str, errors: list[str]) -> bool:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected_hash)):
        errors.append(f"{label}: invalid SHA-256 entry")
        return False
    if not path.is_file():
        errors.append(f"{label}: file missing")
        return False
    valid = True
    if expected_bytes is not None and path.stat().st_size != int(expected_bytes):
        errors.append(f"{label}: byte size mismatch")
        valid = False
    if digest(path) != expected_hash.lower():
        errors.append(f"{label}: SHA-256 mismatch")
        valid = False
    return valid


def verify(root: Path) -> int:
    root = root.resolve()
    satellite = root / "data" / "satellite"
    field = root / "data" / "field"
    errors: list[str] = []
    passed_satellite = passed_field = checked_metadata = historical_hashes = 0
    seen: set[Path] = set()

    try:
        with (satellite / "asset_inventory.csv").open(newline="", encoding="utf-8-sig") as stream:
            inventory = list(csv.DictReader(stream))
        if not inventory:
            errors.append("Satellite inventory is empty")
        for number, row in enumerate(inventory, 1):
            label = f"Satellite entry {number} ({row.get('item', '?')}/{row.get('asset', '?')})"
            try:
                file = satellite_path(satellite, row)
                if file in seen:
                    errors.append(f"{label}: duplicate inventory file")
                    continue
                seen.add(file)
                passed_satellite += check_file(file, row["sha256"], row.get("bytes"), label, errors)
            except (KeyError, ValueError, OSError) as exc:
                errors.append(f"{label}: {exc}")
    except (OSError, csv.Error) as exc:
        inventory = []
        errors.append(f"Cannot read satellite inventory: {exc}")

    try:
        manifest = json.loads((field / "manifest.json").read_text(encoding="utf-8"))
        datasets = manifest["datasets"]
        if not datasets:
            errors.append("Field manifest has no datasets")
        for number, dataset in enumerate(datasets, 1):
            label = f"Field subset {number} ({dataset.get('label', '?')})"
            try:
                filename = local_name(dataset["subset_file"])
                file = contained(field / filename, field)
                if file in seen:
                    errors.append(f"{label}: duplicate manifest file")
                    continue
                seen.add(file)
                passed_field += check_file(file, dataset["subset_sha256"], dataset.get("subset_bytes"), label, errors)
                metadata = contained(field / local_name(dataset["metadata_file"]), field)
                if metadata.is_file():
                    checked_metadata += 1
                else:
                    errors.append(f"{label}: metadata companion missing")
                # Historical source archives are not bundled. Do not report
                # their hashes as newly verified source ZIP checksums.
                if "source_zip_sha256" in dataset:
                    if not re.fullmatch(r"[0-9a-fA-F]{64}", dataset["source_zip_sha256"]):
                        errors.append(f"{label}: malformed historical source ZIP hash")
                    historical_hashes += 1
            except (KeyError, ValueError, OSError) as exc:
                errors.append(f"{label}: {exc}")
    except (OSError, ValueError, KeyError) as exc:
        datasets = []
        errors.append(f"Cannot read field manifest: {exc}")

    print(f"Satellite assets: {passed_satellite}/{len(inventory)} verified")
    print(f"Field subsets: {passed_field}/{len(datasets)} verified")
    print(f"Metadata companions: {checked_metadata}/{len(datasets)} present (no stored checksum)")
    print(f"Historical source ZIP hashes: {historical_hashes} provenance references; original ZIPs are not bundled")
    if errors:
        print(f"FAILED: {len(errors)} issue(s)", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"PASS: SHA-256 and size verified for all {passed_satellite + passed_field} packaged data files in these manifests")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent,
                        help="Package root; defaults to the folder containing this script")
    return verify(parser.parse_args().root)


if __name__ == "__main__":
    raise SystemExit(main())
