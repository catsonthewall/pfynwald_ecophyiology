"""Join context summaries to clock scenarios without asserting independent replication."""
from pathlib import Path
import pandas as pd

def run(root):
    field=pd.read_csv(root/'outputs/field/overpass_clock_sensitivity_by_treatment.csv')
    optical=pd.read_csv(root/'outputs/tables/S2_scene_summary.csv')
    thermal=pd.read_csv(root/'outputs/tables/Landsat_scene_summary.csv')
    context=pd.read_csv(root/'outputs/tables/Landsat_baseQA_CONTEXT_summary.csv')
    rows=[]
    for _,f in field.iterrows():
        date=f.overpass_utc[:10];r=f.to_dict()
        r['independent_satellite_dates_for_this_sensor_in_field_subset']=1
        r['spatial_match']='landscape context only; no crown or instrument footprint supplied'
        if f.event.startswith('Sentinel2'):
            s=optical.loc[optical.date.eq(date)].iloc[0]
            r.update(satellite_sensor='Sentinel-2 optical',
                     satellite_valid_pixels=int(s.valid_forest_pixels),
                     NDMI_landscape_median=s.NDMI_median,NDRE_landscape_median=s.NDRE_median,
                     match_status='provisional optical context; clock and footprint unverified')
        else:
            s=thermal.loc[thermal.date.eq(date)].iloc[0]
            c=context.loc[context.date.eq(date)].iloc[0]
            r.update(satellite_sensor='Landsat thermal',
                     satellite_valid_pixels=int(s.valid_pixels),
                     base_QA_valid_pixels=int(c.base_QA_valid_pixels),
                     LST_C_strict_median=s.LST_C_median,
                     match_status='rejected thermal match: cloud-covered ROI; no validation pair')
        rows.append(r)
    pd.DataFrame(rows).to_csv(root/'outputs/tables/candidate_collocations_NOT_training_data.csv',index=False)

if __name__=='__main__':run(Path(__file__).resolve().parents[1])
