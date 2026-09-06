from __future__ import annotations
import pandas as pd
import numpy as np

def benchmark(df):
    if df.empty: return pd.DataFrame()
    x=df.copy()
    x['fleet_percentile'] = x['risk'].rank(pct=True, method='average').mul(100).round(0).astype(int)
    x['attention_index'] = (0.5*x['risk'] + 0.3*x['anomaly_score'] + 0.2*(100-x['health_score'])).round(0).astype(int)
    x['fleet_rank'] = x['attention_index'].rank(ascending=False, method='min').astype(int)
    return x.sort_values(['fleet_rank','machine_id'])

def portfolio_stats(df):
    if df.empty: return {'risk':0,'health':0,'anomaly':0,'critical':0,'warning':0,'watch':0}
    return {'risk':round(float(df.risk.mean()),1),'health':round(float(df.health_score.mean()),1),'anomaly':round(float(df.anomaly_score.mean()),1),
            'critical':int((df.risk>=76).sum()),'warning':int((df.risk>=51).sum()),'watch':int(((df.risk>=26)&(df.risk<51)).sum())}

def scenario_sweep(base, steps=7):
    rows=[]
    for factor in np.linspace(0.75,1.25,steps):
        temp=float(base.temp)*factor
        vib=float(base.vibration)*factor
        pressure=float(base.pressure)*(1 + (factor-1)*0.35)
        rows.append({'factor':round(factor,2),'temp':round(temp,2),'vibration':round(vib,3),'pressure':round(pressure,2)})
    return pd.DataFrame(rows)
