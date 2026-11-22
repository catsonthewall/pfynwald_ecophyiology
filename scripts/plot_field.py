"""Field plots are diagnostic; source timezone and source-clock agreement are unresolved."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'control':'#354b70','irrigation':'#2b8c69','irrigation_vpd':'#6dba9b',
        'roof':'#a25443','roof_vpd':'#d3a364'}

def run(field_dir, output_dir):
    output_dir.mkdir(parents=True,exist_ok=True)
    field=pd.read_csv(field_dir/'field_10min.csv',parse_dates=['source_time_naive'])
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True,constrained_layout=True)
    for treatment,g in field.groupby('treatment'):
        by_time=g.groupby('source_time_naive').Tcan_C.median()
        axs[0].plot(by_time.index,by_time.values,label=treatment,color=COLORS[treatment],lw=.9)
    met=pd.read_csv(field_dir/'meteorology_10min.csv',parse_dates=['source_time_naive']).rename(
        columns={'met_TA_oc':'Tair_above_C','met_VPD_oc':'VPD_above_reported_kPa',
                 'met_GlobalRad_oc':'global_radiation_W_m2'})
    axs[1].plot(met.source_time_naive,met.Tair_above_C,color='#444444',label='Single above-canopy station')
    axs[1].plot(met.source_time_naive,met.met_TA_ic_amb,color='#4f926e',alpha=.8,label='Within-canopy ambient aggregate')
    axs[1].plot(met.source_time_naive,met.met_TA_ic_manip,color='#c29148',alpha=.8,label='Within-canopy manipulated aggregate')
    axs[2].plot(met.source_time_naive,met.VPD_above_reported_kPa,color='#7e4a7c',label='Reported above-canopy VPD')
    axr=axs[2].twinx();axr.fill_between(met.source_time_naive,0,met.global_radiation_W_m2,color='#d9bb65',alpha=.18)
    axr.set_ylabel('Global radiation (W m-2)',color='#8e7534')
    for ax,label in zip(axs,['Canopy temperature (C)','Air temperature (C)','VPD (kPa)']):
        ax.set_ylabel(label);ax.grid(alpha=.18);ax.legend(fontsize=7,ncol=3,loc='upper left')
    axs[0].set_title('Pfynwald public subset | July 15-21 2024\nDescriptive source-clock alignment; treatment curves are medians of available sensors')
    axs[2].set_xlabel('Source clock (timezone unresolved; not asserted to be UTC)')
    fig.savefig(output_dir/'05_Field_week_diagnostics.png',dpi=180);plt.close(fig)
    t=pd.read_csv(field_dir/'overpass_clock_sensitivity_by_treatment.csv')
    s=t[t.event.eq('Sentinel2_20240719')]
    fig,axs=plt.subplots(1,2,figsize=(10,4.8),constrained_layout=True)
    for tr,g in s.groupby('treatment'):
        g=g.sort_values('assumed_field_clock_utc_offset_h')
        x=g.assumed_field_clock_utc_offset_h
        axs[0].plot(x,g.Tcan_C_mean,'o-',label=tr,color=COLORS[tr])
        axs[1].plot(x,g.deltaT_within_group_C_mean,'o-',color=COLORS[tr])
    for ax in axs:
        ax.set_xticks([0,1,2],['UTC','UTC+1','UTC+2']);ax.grid(alpha=.2)
        ax.set_xlabel('Assumed common field clock (unverified alternatives)')
    axs[0].set_ylabel('Window mean canopy temperature (C)');axs[0].legend(fontsize=8)
    axs[1].set_ylabel('Canopy minus group air temperature (C)')
    fig.suptitle('July 19 Sentinel-2 overpass | +/-15 minute windows\nNo timezone is selected; lines show matching sensitivity, not temporal change',fontsize=12)
    fig.savefig(output_dir/'06_Clock_assumption_sensitivity.png',dpi=180);plt.close(fig)
    day=field[field.global_radiation_W_m2>200].copy()
    means=day.groupby(['treatment','scaffold_id'])[['deltaT_above_C','deltaT_within_group_C']].mean()
    trmeans=means.groupby('treatment').mean().reindex(list(COLORS))
    fig,ax=plt.subplots(figsize=(10,4.5),constrained_layout=True)
    xx=np.arange(len(trmeans));w=.35
    ax.bar(xx-w/2,trmeans.deltaT_above_C,width=w,color='#4c6d89',label='Subtract above-canopy station air')
    ax.bar(xx+w/2,trmeans.deltaT_within_group_C,width=w,color='#b28745',label='Subtract ambient/manipulated group air')
    ax.set_xticks(xx,trmeans.index,rotation=12);ax.axhline(0,color='black',lw=.6)
    ax.set_ylabel('Mean canopy-air temperature difference (C)')
    ax.set_title('Choice of air reference changes interpretation\nJuly 15-21; radiation >200 W m-2; equal weight per scaffold; descriptive only')
    ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.savefig(output_dir/'07_Air_reference_sensitivity.png',dpi=180);plt.close(fig)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    run(root/'outputs/field',root/'outputs/figures')
