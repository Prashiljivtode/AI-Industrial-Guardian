"""Lightweight trend forecasting from the local sensor history. Demo-safe, no external service."""
import numpy as np

def forecast_risk(history, current_risk, horizon=6):
    if history is None or len(history)<3: slope=0.0
    else:
        y=history["risk"].astype(float).tail(12).to_numpy(); x=np.arange(len(y)); slope=float(np.polyfit(x,y,1)[0]) if len(y)>1 else 0.0
    rows=[]
    for step in range(1,horizon+1):
        r=max(0,min(100,current_risk+slope*step))
        rows.append({"step":step,"forecast_risk":round(r,1),"hours_ahead":step,"band":"CRITICAL" if r>=76 else "WARNING" if r>=51 else "WATCH" if r>=26 else "HEALTHY"})
    return rows, round(slope,2)
