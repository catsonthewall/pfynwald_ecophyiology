"""Reproduce the supplied experiment entirely offline after package installation."""
from pathlib import Path
import importlib.metadata
import json
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from process_satellite import run as satellite
from process_field_data import process_fields
from plot_field import run as field_figures
from build_collocations import run as collocations

def main():
    cfg=json.loads((ROOT/'config.json').read_text())
    print('1/3 Satellite reflectance, masks, temperature and descriptive summaries')
    satellite(ROOT/'data/satellite',ROOT/'outputs',ROOT/'config.json')
    print('2/3 Field quality flags, units, aggregation and clock sensitivity')
    process_fields(ROOT/'data/field',ROOT/'outputs/field',window_minutes=cfg['field_window_minutes'])
    print('3/3 Field diagnostic figures')
    field_figures(ROOT/'outputs/field',ROOT/'outputs/figures')
    collocations(ROOT)
    versions={m:importlib.metadata.version(m) for m in ['numpy','pandas','matplotlib','rasterio','pyproj','scipy']}
    (ROOT/'outputs/software_versions.json').write_text(json.dumps(versions,indent=2))
    print('Done. Open outputs/figures, outputs/tables and docs/START_HERE.html.')

if __name__=='__main__': main()
