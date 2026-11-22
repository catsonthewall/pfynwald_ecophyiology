"""Reproducible anonymous PC STAC/COG crops for a Pfynwald feasibility exercise.

Run: python acquire_satellite.py --out satellite_data
Only reads public cloud data. Crops retain native DN, CRS, affine and source IDs.
No signed URLs are written to disk. Run again to resume existing crops.
This is a 2 km landscape context ROI, NOT a digitised experimental plot boundary.
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
from pathlib import Path
import time
import threading
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform_bounds
from pyproj import Transformer
from http_range_reader import HTTPRangeReader

API = 'https://planetarycomputer.microsoft.com/api/stac/v1'
LON, LAT = 7 + 36/60 + 40/3600, 46 + 18/60 + 7/3600
S2_DATES = ['2024-07-04','2024-07-14','2024-07-19','2024-07-29','2024-08-06','2024-08-23']
S2_BANDS = ['B02','B03','B04','B05','B08','B8A','B11','SCL']
LS_BANDS = ['red','nir08','swir16','lwir11','qa_pixel','qa_radsat','qa','cdist']
_SAS_CACHE = {}
_SAS_LOCK = threading.Lock()

def get_bytes(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as exc:
            if attempt == 2:
                raise
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                delay = int(exc.headers.get('Retry-After', '30'))
                if delay > 60:
                    raise RuntimeError(f'Rate limited: retry after {delay}s') from exc
                time.sleep(max(1, delay))
            else:
                time.sleep(1 + attempt)

def get_json(url):
    return json.loads(get_bytes(url))

def sign(href):
    # Anonymous access tokens are short lived: acquire fresh tokens each run.
    parsed = urllib.parse.urlsplit(href)
    key = (parsed.netloc, parsed.path.split('/')[1])
    with _SAS_LOCK:
        if key in _SAS_CACHE:
            return urllib.parse.urlunsplit(parsed._replace(query=_SAS_CACHE[key]))
        signed = get_json('https://planetarycomputer.microsoft.com/api/sas/v1/sign?' +
                         urllib.parse.urlencode({'href': href}))['href']
        signed_parts = urllib.parse.urlsplit(signed)
        # PC grants container-scoped read tokens; cache only when scope is explicit.
        if urllib.parse.parse_qs(signed_parts.query).get('sr') == ['c']:
            _SAS_CACHE[key] = signed_parts.query
        return signed

def catalog(collection, start, end, bbox, out):
    dest = out / (collection + '_catalog.json')
    if dest.exists():
        return json.loads(dest.read_text())
    query = dict(collections=collection, bbox=','.join(map(str,bbox)),
                 datetime=start+'/'+end, limit=100)
    data = get_json(API+'/search?'+urllib.parse.urlencode(query))
    # Limit is comfortably above this bounded two-month, one-location query.
    if any(x.get('rel') == 'next' for x in data.get('links', [])):
        raise RuntimeError('Catalog is paginated; narrow query or implement paging.')
    dest.write_text(json.dumps(data, indent=2))
    return data

def crop_asset(item, asset_name, bounds_utm, out):
    folder = out / 'raw' / item['id']
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (asset_name+'.tif')
    if dest.exists():
        return str(dest.relative_to(out))
    href = item['assets'][asset_name]['href']
    signed = sign(href)
    options = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                   GDAL_HTTP_MAX_RETRY=3, GDAL_HTTP_RETRY_DELAY=1,
                   GDAL_HTTP_TIMEOUT=60, CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif,.TIF')
    # Honour the environment's trusted CA bundle without disabling TLS checks.
    ca_bundle = os.environ.get('CURL_CA_BUNDLE') or os.environ.get('SSL_CERT_FILE')
    if ca_bundle:
        options['CURL_CA_BUNDLE'] = ca_bundle
    extra = {}
    target = signed
    if os.environ.get('PFYN_HTTP_RANGE') == '1':
        reader = HTTPRangeReader(signed)
        target = 'source.tif'
        def opener(path, mode='rb'):
            if path != target:
                raise FileNotFoundError(path)
            reader.seek(0)
            return reader
        extra['opener'] = opener
    with rasterio.Env(**options):
        with rasterio.open(target, **extra) as src:
            b = transform_bounds('EPSG:32632',src.crs,*bounds_utm,densify_pts=21)
            w = from_bounds(*b,transform=src.transform)
            c0, r0 = math.floor(w.col_off)-2, math.floor(w.row_off)-2
            c1, r1 = math.ceil(w.col_off+w.width)+2, math.ceil(w.row_off+w.height)+2
            w = Window(c0,r0,c1-c0,r1-r0)
            w = w.intersection(Window(0,0,src.width,src.height))
            arr=src.read(window=w)
            profile=src.profile.copy()
            profile.update(width=arr.shape[-1],height=arr.shape[-2],
                           transform=src.window_transform(w),compress='deflate',
                           tiled=False)
            for k in ['blockxsize','blockysize']:
                profile.pop(k,None)
            with rasterio.open(dest,'w',**profile) as dst:
                dst.write(arr)
                dst.update_tags(source_item=item['id'],source_asset=asset_name,
                                source_href=href,stored_units='native source DN')
    return str(dest.relative_to(out))

def s2_metadata(item,out):
    folder=out/'raw'/item['id']; folder.mkdir(parents=True,exist_ok=True)
    xml_path=folder/'MTD_MSIL2A.xml'
    if not xml_path.exists():
        xml_path.write_bytes(get_bytes(sign(item['assets']['product-metadata']['href'])))
    root=ET.fromstring(xml_path.read_bytes())
    quant=[float(x.text) for x in root.iter() if x.tag.split('}')[-1]=='BOA_QUANTIFICATION_VALUE']
    offsets={x.attrib['band_id']:float(x.text) for x in root.iter()
             if x.tag.split('}')[-1]=='BOA_ADD_OFFSET'}
    ids={'B02':'1','B03':'2','B04':'3','B05':'4','B08':'7','B8A':'8','B11':'11'}
    if len(quant)!=1 or any(v not in offsets for v in ids.values()):
        raise ValueError('Expected BOA scaling missing from product XML; do not guess.')
    return {b:dict(scale=1/quant[0],offset=offsets[i]/quant[0],nodata=0)
            for b,i in ids.items()}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'satellite_data')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--urllib-range',action='store_true',
                        help='Use verified urllib HTTP ranges instead of GDAL/libcurl')
    args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    if args.urllib_range:
        os.environ['PFYN_HTTP_RANGE']='1'
    cx,cy=Transformer.from_crs(4326,32632,always_xy=True).transform(LON,LAT)
    bounds=(cx-1000,cy-1000,cx+1000,cy+1000)
    bbox=transform_bounds('EPSG:32632','EPSG:4326',*bounds)
    s2=catalog('sentinel-2-l2a','2024-07-01T00:00:00Z','2024-09-01T00:00:00Z',bbox,out)
    ls=catalog('landsat-c2-l2','2024-07-01T00:00:00Z','2024-09-01T00:00:00Z',bbox,out)
    wc=catalog('esa-worldcover','2021-01-01T00:00:00Z','2021-12-31T23:59:59Z',bbox,out)
    chosen_s2=[f for f in s2['features'] if f['properties']['datetime'][:10] in S2_DATES]
    # Restrict to known tile covering the point, avoiding duplicate overlapping tiles.
    chosen_s2=[f for f in chosen_s2 if f['properties']['s2:mgrs_tile']=='32TLS']
    chosen_ls=[f for f in ls['features'] if f['properties'].get('landsat:correction')=='L2SP']
    if len(chosen_s2)!=len(S2_DATES):
        raise ValueError('Expected exactly six pre-specified Sentinel2 scenes.')
    chosen_s2.sort(key=lambda f:(f['properties']['datetime'][:10]!='2024-07-19',f['properties']['datetime']))
    selected=[('esa-worldcover',f,['map']) for f in wc['features']]
    selected += [('sentinel-2-l2a',f,S2_BANDS) for f in chosen_s2]
    selected += [('landsat-c2-l2',f,LS_BANDS) for f in chosen_ls]
    manifest=dict(site_point_wgs84=[LON,LAT], site_coordinate_source=
      'https://doi.org/10.1111/nph.71661', bounds_utm32632=list(bounds),
      roi_note='2 km square landscape context; core radius500m; no experimental polygons supplied',
      period='2024-07-01/2024-08-31',items=[])
    tasks=[]
    for coll,item,bands in selected:
        record=dict(collection=coll,id=item['id'],datetime=item['properties'].get('datetime'),
                    properties=item['properties'],assets={})
        if coll=='sentinel-2-l2a':
            record['reflectance_scaling']=s2_metadata(item,out)
        for b in bands:
            record['assets'][b]=dict(source_href=item['assets'][b]['href'],
                path=str(Path('raw')/item['id']/(b+'.tif')),
                raster_bands=item['assets'][b].get('raster:bands'))
            tasks.append((item,b))
        manifest['items'].append(record)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    errors=[]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(crop_asset,item,b,bounds,out):(item['id'],b) for item,b in tasks}
        for i,fut in enumerate(cf.as_completed(futures),1):
            key=futures[fut]
            try:
                print(f'{i}/{len(tasks)} OK {fut.result()}',flush=True)
            except Exception as exc:
                errors.append(dict(item=key[0],asset=key[1],error=str(exc)))
                print(f'{i}/{len(tasks)} FAILED {key} {exc}',flush=True)
    (out/'download_errors.json').write_text(json.dumps(errors,indent=2))
    if errors:
        raise RuntimeError(f'{len(errors)} assets failed; rerun to resume.')
    print('COMPLETE',len(selected),'items',len(tasks),'native cropped assets',flush=True)

if __name__=='__main__':
    main()
