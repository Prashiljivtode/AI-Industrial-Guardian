import numpy as np

def sensor_severity(temp,vibration,pressure):
    t=np.clip((float(temp)-70)/35,0,1); v=np.clip((float(vibration)-0.45)/1.35,0,1); p=np.clip((float(pressure)-34)/20,0,1)
    return int(round(100*(0.45*t+0.4*v+0.15*p)))

def maintenance_costs(risk,rul_hours,status):
    risk=float(risk); rul=float(rul_hours)
    preventive=12000 + 10000*(risk/100)
    failure=50000 + 95000*(risk/100)
    downtime=1.5 + 5.5*(risk/100)
    urgency=1.35 if status=="CRITICAL" else 1.1 if status=="WARNING" else 1.0
    preventive*=urgency
    return {"preventive_cost":round(preventive),"failure_cost":round(failure),"loss_avoided":round(max(0,failure-preventive)),"downtime_hours":round(downtime,1)}
