"""Process bundled native DN crops without any network access.

Run from the package root: python scripts/process_satellite.py
Output statistics describe a 500 m landscape buffer, not VPDrought plots.
"""
from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from pyproj import Transformer
from scipy.ndimage import binary_dilation, distance_transform_edt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.colors import ListedColormap, BoundaryNorm

ROOT = Path(__file__).resolve().parents[1]

def read_raster(path):
    with rasterio.open(path) as ds:
        return ds.read(1), ds.profile.copy()

def warp_array(array, source, target, method=Resampling.nearest):
    dest = np.full((target['height'], target['width']), np.nan, np.float32)
    reproject(array.astype(np.float32), dest,
              src_transform=source['transform'], src_crs=source['crs'],
              src_nodata=np.nan, dst_transform=target['transform'],
              dst_crs=target['crs'], dst_nodata=np.nan, resampling=method)
    return dest

def load_warp(path, target, method=Resampling.nearest, nodata=None):
    a, p = read_raster(path)
    a = a.astype(np.float32)
    if nodata is not None:
        a[a == nodata] = np.nan
    return warp_array(a, p, target, method)

def save_raster(path, array, profile, label):
    p = profile.copy()
    p.update(driver='GTiff', count=1, dtype='float32', nodata=-9999,
             compress='deflate', tiled=False)
    for key in ['blockxsize', 'blockysize']:
        p.pop(key, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', **p) as ds:
        ds.write(np.where(np.isfinite(array), array, -9999).astype(np.float32), 1)
        ds.set_band_description(1, label)
        ds.update_tags(analysis_scope='Pfynwald landscape vicinity, not experimental plots')

def spatial_masks(wc_path, profile, cfg):
    wc, wp = read_raster(wc_path)
    tree = np.where(wc == 0, np.nan, (wc == 10).astype(np.float32))
    frac = warp_array(tree, wp, profile, Resampling.average)
    forest = np.isfinite(frac) & (frac >= cfg['forest_fraction_min'])
    cx, cy = Transformer.from_crs(4326, profile['crs'], always_xy=True).transform(
        cfg['site_lon'], cfg['site_lat'])
    rr, cc = np.indices((profile['height'], profile['width']))
    t = profile['transform']
    xx = t.c + (cc + .5) * t.a + (rr + .5) * t.b
    yy = t.f + (cc + .5) * t.d + (rr + .5) * t.e
    core = (xx-cx)**2 + (yy-cy)**2 <= cfg['core_radius_m']**2
    return frac, forest, core, (cx, cy)

def stats(a, mask):
    v = a[mask & np.isfinite(a)]
    if not len(v):
        return {'n': 0, 'median': np.nan, 'q25': np.nan, 'q75': np.nan}
    return {'n': int(len(v)), 'median': float(np.median(v)),
            'q25': float(np.quantile(v, .25)), 'q75': float(np.quantile(v, .75))}

def index(a, b):
    total = a+b
    return np.divide(a-b, total, out=np.full_like(a, np.nan), where=total > 1e-6)

def extent_relative(profile, center):
    t = profile['transform']; cx, cy = center
    return [(t.c-cx)/1000, (t.c+t.a*profile['width']-cx)/1000,
            (t.f+t.e*profile['height']-cy)/1000, (t.f-cy)/1000]

def annotate_map(ax, ext, cfg):
    ax.add_patch(Circle((0, 0), cfg['core_radius_m']/1000,
                        edgecolor='white', facecolor='none', linewidth=1.3))
    ax.scatter([0], [0], marker='+', c='white', s=38, linewidths=1.4)
    ax.set_xlabel('East of reference point (km)')
    ax.set_ylabel('North of reference point (km)')
    ax.set_xlim(ext[:2]); ax.set_ylim(ext[2:])

def s2_process(data, manifest, out, cfg, wc_path):
    records = sorted((x for x in manifest['items'] if x['collection']=='sentinel-2-l2a'),
                     key=lambda x:x['datetime'])
    _, grid = read_raster(data / records[0]['assets']['B8A']['path'])
    if not np.isclose(abs(grid['transform'].a), cfg['s2_grid_m']):
        raise ValueError('Expected a native 20 m B8A grid.')
    frac, forest, core, center = spatial_masks(wc_path, grid, cfg)
    support = forest & core
    save_raster(out/'rasters/s2_forest_fraction_20m.tif', frac, grid,
                '2021 WorldCover class 10 fraction in 20 m grid cells')
    save_raster(out/'rasters/s2_core_forest_mask_20m.tif', support.astype(float), grid,
                '500 m buffer and tree-cover fraction at least 0.8')
    frames=[]; summary=[]
    for rec in records:
        band={}
        for b in ['B02','B03','B04','B05','B08','B8A','B11']:
            raw=load_warp(data/rec['assets'][b]['path'],grid,Resampling.average,nodata=0)
            sc=rec['reflectance_scaling'][b]
            band[b]=raw*sc['scale']+sc['offset']
        scl=load_warp(data/rec['assets']['SCL']['path'],grid)
        cloud=np.isin(scl,[3,8,9,10])
        n_buffer=cfg['s2_cloud_buffer_pixels']
        if not isinstance(n_buffer,int) or n_buffer<0:
            raise ValueError('s2_cloud_buffer_pixels must be a non-negative integer.')
        cloudy=cloud.copy() if n_buffer==0 else binary_dilation(cloud,iterations=n_buffer)
        spectral_ok=np.ones_like(support)
        for b in ['B04','B08','B05','B8A','B11']:
            spectral_ok &= np.isfinite(band[b]) & (band[b]>=0) & (band[b]<=1)
        valid=np.isin(scl,[4,5]) & ~cloudy & spectral_ok
        metrics={'NDVI':index(band['B08'],band['B04']),
                 'NDMI':index(band['B8A'],band['B11']),
                 'NDRE':index(band['B8A'],band['B05'])}
        masked=valid & support
        n=int(masked.sum()); denominator=int(support.sum())
        valid_fraction=n/denominator if denominator else 0
        row={'date':rec['datetime'][:10],'datetime_utc':rec['datetime'],
             'scene_id':rec['id'],'tile_cloud_pct':rec['properties'].get('eo:cloud_cover'),
             'core_forest_pixels':denominator,'valid_forest_pixels':n,
             'valid_forest_fraction':valid_fraction,
             'accepted':valid_fraction>=cfg['scene_min_valid_fraction'] and n>=cfg['scene_min_pixels']}
        for name, a in metrics.items():
            row.update({name+'_'+k:v for k,v in stats(a,masked).items()})
            save_raster(out/f'rasters/S2_{row["date"]}_{name}_20m.tif',
                        np.where(valid & forest,a,np.nan),grid,name+' in screened tree-cover pixels')
        save_raster(out/f'rasters/S2_{row["date"]}_valid_20m.tif',valid.astype(float),grid,'S2 clear and plausible reflectance')
        summary.append(row)
        frames.append(dict(rec=rec,metrics=metrics,mask=masked,valid=valid,
                           band=band,scl=scl,row=row))
    table=pd.DataFrame(summary)
    table.to_csv(out/'tables/S2_scene_summary.csv',index=False)
    accepted=[f for f in frames if f['row']['accepted']]
    fixed=np.logical_and.reduce([f['mask'] for f in accepted]) if accepted else np.zeros_like(support)
    fixed_rows=[]
    for f in accepted:
        r={'date':f['row']['date'],'scene_id':f['row']['scene_id'],'common_pixels':int(fixed.sum())}
        for name,a in f['metrics'].items():
            r.update({name+'_'+k:v for k,v in stats(a,fixed).items()})
        fixed_rows.append(r)
    fixed_table=pd.DataFrame(fixed_rows)
    fixed_table.to_csv(out/'tables/S2_fixed_support_summary.csv',index=False)
    save_raster(out/'rasters/S2_common_support_20m.tif',fixed.astype(float),grid,
                'Same valid pixels across all accepted selected S2 scenes')
    # Required sensitivity to source point uncertainty and arbitrary landscape radius.
    sensitivity=[]
    rr,cc=np.indices(support.shape);t=grid['transform']
    xx=t.c+(cc+.5)*t.a; yy=t.f+(rr+.5)*t.e
    transformer=Transformer.from_crs(4326,grid['crs'],always_xy=True)
    for label,lon,lat in [('paper_reference',cfg['site_lon'],cfg['site_lat']),
                           ('EnviDat_subset_approximate',7.612,46.302),
                           ('EnviDat_catalog_rounded',7.612,46.303)]:
        cx,cy=transformer.transform(lon,lat)
        for radius in [250,500,750]:
            region=((xx-cx)**2+(yy-cy)**2<=radius**2)&forest
            for f in frames:
                r={'date':f['row']['date'],'center':label,'radius_m':radius}
                r.update(stats(f['metrics']['NDMI'],region&f['valid']))
                sensitivity.append(r)
    pd.DataFrame(sensitivity).to_csv(out/'tables/S2_spatial_support_sensitivity.csv',index=False)
    s2_figures(frames,fixed_table,grid,center,frac,out,cfg)
    return table, fixed_table, frames

def s2_figures(frames,fixed,grid,center,frac,out,cfg):
    f=next(x for x in frames if x['row']['date']=='2024-07-19')
    ext=extent_relative(grid,center)
    fig,axs=plt.subplots(2,2,figsize=(11,9),constrained_layout=True)
    rgb=np.dstack([f['band'][b] for b in ['B04','B03','B02']])
    rgb=np.clip(rgb/0.3,0,1)**(1/1.3)
    axs[0,0].imshow(np.nan_to_num(rgb),extent=ext)
    axs[0,0].set_title('July 19 2024 | True colour (20 m display)')
    palette=['black','magenta','#555555','#964b00','#3c9a5f','#d7ba7d',
             '#247ab5','#999999','#cccccc','#ffffff','#99dfff','#e9a9e9']
    im=axs[0,1].imshow(f['scl'],extent=ext,cmap=ListedColormap(palette),
        norm=BoundaryNorm(np.arange(-.5,12.5,1),12))
    axs[0,1].set_title('SCL classes | Pixel QA before screening')
    fig.colorbar(im,ax=axs[0,1],ticks=range(12),shrink=.8,label='SCL class')
    for ax,name in [(axs[1,0],'NDMI'),(axs[1,1],'NDRE')]:
        im=ax.imshow(np.where(f['valid']&(frac>=cfg['forest_fraction_min']),
                             f['metrics'][name],np.nan),extent=ext,cmap='YlGnBu',vmin=0,vmax=.6)
        ax.set_facecolor('#ededed'); ax.set_title(name+' | Clear tree-cover pixels')
        fig.colorbar(im,ax=ax,shrink=.8,label=name+' (unitless)')
    for ax in axs.flat: annotate_map(ax,ext,cfg)
    fig.suptitle('White circle: 500 m landscape buffer, not experimental plot boundary',fontsize=12)
    fig.savefig(out/'figures/01_Sentinel2_QA_and_indices.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(10,6),sharex=True,constrained_layout=True)
    for ax,name in zip(axs,['NDMI','NDRE']):
        for frame in frames:
            row=frame['row'];day=pd.to_datetime(row['date']); med=row[name+'_median']
            if np.isfinite(med):
                ax.errorbar(day,med,yerr=[[med-row[name+'_q25']],[row[name+'_q75']-med]],
                    fmt='o' if row['accepted'] else 'x',color='#54736a' if row['accepted'] else '#b86a50',
                    capsize=3,alpha=.8)
            else:
                ax.plot(day,0,marker='x',color='#b86a50',transform=ax.get_xaxis_transform())
        if len(fixed):
            ax.plot(pd.to_datetime(fixed['date']),fixed[name+'_median'],'s--',color='#1d5076',
                    label=f'Fixed common pixels (n={int(fixed.iloc[0]["common_pixels"])})')
        ax.set_ylabel(name);ax.grid(alpha=.2);ax.legend(loc='best',fontsize=8)
    axs[0].set_title('Selected acquisitions | Bars are spatial IQR, not confidence intervals\nCircles: coverage accepted; crosses: rejected/absent; squares: fixed support')
    axs[1].set_xlabel('Acquisition date in 2024 (irregular selected examples)')
    fig.savefig(out/'figures/02_Sentinel2_selected_dates.png',dpi=180);plt.close(fig)

def ls_process(data,manifest,out,cfg,wc_path):
    records=sorted((x for x in manifest['items'] if x['collection']=='landsat-c2-l2'),
                   key=lambda x:x['datetime'])
    frames=[];summary=[];sens=[];context_rows=[]
    for rec in records:
        dn,grid=read_raster(data/rec['assets']['lwir11']['path'])
        frac,forest,core,center=spatial_masks(wc_path,grid,cfg)
        arrays={b:load_warp(data/rec['assets'][b]['path'],grid) for b in ['qa_pixel','qa_radsat','qa','cdist']}
        qa=arrays['qa_pixel'].astype(np.uint16)
        base=((qa&63)==0)&((qa&128)==0)&(arrays['qa_radsat']==0)&(dn>0)
        # USGS C2 L2 product factors; ST_QA is estimated temperature uncertainty.
        temp=dn.astype(np.float64)*.00341802+149.0-273.15
        uncertainty=arrays['qa']*.01
        cdist=arrays['cdist']*.01
        interior=distance_transform_edt(forest,sampling=(abs(grid['transform'].e),abs(grid['transform'].a)))
        support=core & forest & (interior>=cfg['landsat_forest_interior_m'])
        context_mask=base&support&(uncertainty>=0)
        context_row={'date':rec['datetime'][:10],'datetime_utc':rec['datetime'],'scene_id':rec['id'],
            'potential_interior_forest_pixels':int(support.sum()),
            'base_QA_valid_pixels':int(context_mask.sum()),
            'base_QA_valid_fraction':float(context_mask.sum()/support.sum()) if support.any() else 0.,
            'strict_uncertainty_pass_pixels':int((context_mask&(uncertainty<=cfg['landsat_st_qa_max_k'])).sum()),
            'strict_cloud_distance_pass_pixels':int((context_mask&(cdist>=cfg['landsat_cloud_distance_min_km'])).sum()),
            'interpretation':'Context only; no ST_QA or cloud-distance threshold applied'}
        context_row.update({'LST_C_'+k:v for k,v in stats(temp,context_mask).items()})
        context_row.update({'ST_QA_K_'+k:v for k,v in stats(uncertainty,context_mask).items()})
        context_rows.append(context_row)
        good=base&(uncertainty>=0)&(uncertainty<=cfg['landsat_st_qa_max_k'])&(cdist>=cfg['landsat_cloud_distance_min_km'])
        mask=good&support;n=int(mask.sum());denom=int(support.sum())
        row={'date':rec['datetime'][:10],'datetime_utc':rec['datetime'],
             'scene_id':rec['id'],'tile_cloud_pct':rec['properties'].get('eo:cloud_cover'),
             'potential_interior_forest_pixels':denom,'valid_pixels':n,
             'valid_fraction':n/denom if denom else 0,
             'native_thermal_support_m':100,'output_grid_m':abs(grid['transform'].a)}
        row['accepted']=(row['valid_fraction']>=cfg['scene_min_valid_fraction'] and n>=cfg['scene_min_pixels'])
        row.update({'LST_C_'+k:v for k,v in stats(temp,mask).items()})
        row.update({'ST_QA_K_'+k:v for k,v in stats(uncertainty,mask).items()})
        summary.append(row)
        save_raster(out/f'rasters/Landsat_{row["date"]}_LST_C_30m.tif',
            np.where(good&forest&(interior>=cfg['landsat_forest_interior_m']),temp,np.nan),grid,
            'Screened land surface temperature Celsius; native thermal support about 100 m')
        save_raster(out/f'rasters/Landsat_{row["date"]}_valid_30m.tif',good.astype(float),grid,'Landsat quality mask')
        save_raster(out/f'rasters/Landsat_{row["date"]}_baseQA_CONTEXT_LST_C_30m.tif',
                    np.where(base&forest&(interior>=cfg['landsat_forest_interior_m']),temp,np.nan),grid,
                    'CONTEXT ONLY base QA surface temperature; strict uncertainty screen not applied')
        save_raster(out/f'rasters/Landsat_{row["date"]}_ST_QA_K_30m.tif',
                    np.where(base,uncertainty,np.nan),grid,'USGS estimated surface temperature uncertainty K')
        for uq in [1.,2.,3.]:
            for dist in [.3,1.,2.]:
                m=base&support&(uncertainty>=0)&(uncertainty<=uq)&(cdist>=dist)
                r={'date':row['date'],'ST_QA_max_K':uq,'min_cloud_distance_km':dist}
                r.update(stats(temp,m));sens.append(r)
        frames.append(dict(row=row,temp=temp,good=good,mask=mask,support=support,base=base,
                           context_mask=context_mask,context_row=context_row,
                           grid=grid,center=center,uncertainty=uncertainty))
    table=pd.DataFrame(summary);table.to_csv(out/'tables/Landsat_scene_summary.csv',index=False)
    pd.DataFrame(context_rows).to_csv(out/'tables/Landsat_baseQA_CONTEXT_summary.csv',index=False)
    pd.DataFrame(sens).to_csv(out/'tables/Landsat_QA_sensitivity.csv',index=False)
    accepted=[f for f in frames if f['row']['accepted']]
    fixed_rows=[]
    if accepted:
        reference=accepted[0]['grid']
        common=np.logical_and.reduce([load_mask_to_grid(f['mask'],f['grid'],reference) for f in accepted])
        for f in accepted:
            a=warp_array(f['temp'],f['grid'],reference,Resampling.nearest)
            r={'date':f['row']['date'],'common_pixels':int(common.sum())}
            r.update({'LST_C_'+k:v for k,v in stats(a,common).items()});fixed_rows.append(r)
        save_raster(out/'rasters/Landsat_common_support_30m.tif',common.astype(float),reference,
                    'Same screened pixels across accepted selected Landsat scenes')
    pd.DataFrame(fixed_rows).to_csv(out/'tables/Landsat_fixed_support_summary.csv',index=False)
    # Separate diagnostic context: this does not change the predeclared strict screen.
    context_frames=[f for f in frames if f['context_row']['base_QA_valid_fraction']>=cfg['scene_min_valid_fraction']
                    and f['context_row']['base_QA_valid_pixels']>=cfg['scene_min_pixels']]
    context_fixed_rows=[]
    if context_frames:
        reference=context_frames[0]['grid']
        common=np.logical_and.reduce([load_mask_to_grid(f['context_mask'],f['grid'],reference) for f in context_frames])
        for f in context_frames:
            aa=warp_array(f['temp'],f['grid'],reference)
            rr={'date':f['row']['date'],'common_pixels':int(common.sum()),'status':'base QA context only'}
            rr.update({'LST_C_'+k:v for k,v in stats(aa,common).items()});context_fixed_rows.append(rr)
    pd.DataFrame(context_fixed_rows).to_csv(out/'tables/Landsat_baseQA_CONTEXT_fixed_support.csv',index=False)
    ls_figures(frames,out,cfg)
    return table,frames

def load_mask_to_grid(mask,source,target):
    a=warp_array(mask.astype(float),source,target,Resampling.nearest)
    return np.isfinite(a)&(a>.5)

def ls_figures(frames,out,cfg):
    # Map the scene with greatest valid support; dates are never selected by temperature.
    f=max(frames,key=lambda x:x['context_row']['base_QA_valid_pixels'])
    ext=extent_relative(f['grid'],f['center'])
    fig,axs=plt.subplots(1,2,figsize=(11,4.8),constrained_layout=True)
    for ax,a,title,cmap,vmin,vmax,label in [
         (axs[0],f['temp'],'Temperature after base QA only','magma',20,40,'Land surface temperature (C)'),
         (axs[1],f['uncertainty'],'Product-estimated temperature uncertainty','viridis',0,5,'ST_QA uncertainty (K)')]:
        im=ax.imshow(np.where(f['context_mask'],a,np.nan),extent=ext,cmap=cmap,vmin=vmin,vmax=vmax)
        ax.set_facecolor('#ededed');ax.set_title(title,fontsize=10);annotate_map(ax,ext,cfg)
        fig.colorbar(im,ax=ax,shrink=.8,label=label)
    fig.suptitle('Landsat '+f['row']['date']+' | Diagnostic context, strict uncertainty screen NOT applied\n30 m grid; about 100 m thermal support; forest-interior mask is a heuristic',fontsize=12)
    fig.savefig(out/'figures/03_Landsat_temperature_and_support.png',dpi=180);plt.close(fig)
    fig,(ax,axn)=plt.subplots(2,1,figsize=(10,6.5),sharex=True,constrained_layout=True,
                             gridspec_kw={'height_ratios':[2,1]})
    for f in frames:
        r=f['context_row'];med=r['LST_C_median'];day=pd.to_datetime(r['date'])
        if np.isfinite(med):
            ax.errorbar(day,med,yerr=[[med-r['LST_C_q25']],[r['LST_C_q75']-med]],
                        fmt='o' if r['base_QA_valid_fraction']>=cfg['scene_min_valid_fraction'] else 'x',color='#864742',capsize=3)
            ax.annotate(str(r['base_QA_valid_pixels']), (day,med),xytext=(0,9),textcoords='offset points',
                        ha='center',fontsize=8)
        axn.plot(day,r['base_QA_valid_pixels'],'o',color='#864742')
        axn.plot(day,f['row']['valid_pixels'],'x',color='#1d5076')
    fixed_file=out/'tables/Landsat_baseQA_CONTEXT_fixed_support.csv'
    if fixed_file.exists() and fixed_file.stat().st_size>2:
        fixed=pd.read_csv(fixed_file)
        if len(fixed):
            ax.plot(pd.to_datetime(fixed.date),fixed.LST_C_median,'s--',color='#1d5076',
                    label=f'Base-QA fixed common pixels (n={int(fixed.iloc[0]["common_pixels"])})')
            ax.legend(fontsize=8)
    ax.set_title('Diagnostic context only | Strict 2 K screen is NOT relaxed\nBars: spatial IQR; numbers: base-QA 30 m output cells, not independent thermal observations')
    ax.set_ylabel('Base-QA context LST (C)');axn.set_xlabel('2024 acquisition date')
    axn.set_ylabel('Retained cells');axn.set_title('Brown circles: base QA | Blue crosses: strict ST_QA and cloud-distance screen',fontsize=9)
    ax.grid(alpha=.2);axn.grid(alpha=.2)
    fig.savefig(out/'figures/04_Landsat_selected_dates.png',dpi=180);plt.close(fig)

def run(data,out,config):
    cfg=json.loads(config.read_text()); manifest=json.loads((data/'manifest.json').read_text())
    for p in ['rasters','tables','figures']: (out/p).mkdir(parents=True,exist_ok=True)
    wc=[x for x in manifest['items'] if x['collection']=='esa-worldcover']
    if len(wc)!=1: raise ValueError('Expected one verified WorldCover crop.')
    wc_path=data/wc[0]['assets']['map']['path']
    s2,fixed,_=s2_process(data,manifest,out,cfg,wc_path)
    ls,_=ls_process(data,manifest,out,cfg,wc_path)
    audit={'S2_selected_scenes':len(s2),'S2_coverage_accepted':int(s2.accepted.sum()),
           'S2_common_support_pixels':int(fixed.iloc[0].common_pixels) if len(fixed) else 0,
           'Landsat_selected_scenes':len(ls),'Landsat_coverage_accepted':int(ls.accepted.sum()),
           'config':cfg,'forest_mask':'ESA WorldCover 2021 v200 class10, approximate historical mask',
           'inference':'Descriptive selected-date pilot; no validated drought, treatment effect or prediction model'}
    (out/'satellite_audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps({k:v for k,v in audit.items() if k!='config'},indent=2))
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data/satellite')
    p.add_argument('--out',type=Path,default=ROOT/'outputs')
    p.add_argument('--config',type=Path,default=ROOT/'config.json')
    a=p.parse_args();run(a.data,a.out,a.config)
