"""Failure scenario and maintenance impact engine for demo-safe what-if analysis."""
from modules.predictor import predict_machine


def scenario_steps(base, steps=6):
    """Generate a progressive deterioration scenario from a machine snapshot."""
    t0, v0, p0 = float(base["temp"]), float(base["vibration"]), float(base["pressure"])
    rows=[]
    for i in range(steps):
        f=i/(steps-1) if steps>1 else 0
        temp=t0 + 18*f
        vib=v0 + max(0.35, v0*0.75)*f
        pressure=p0 + 8*f
        pred=predict_machine(temp,vib,pressure)
        rows.append({"step":i+1,"phase":("Current" if i==0 else "Stress +%d"%round(f*100)),"temp":round(temp,1),"vibration":round(vib,2),"pressure":round(pressure,1),**pred})
    return rows


def maintenance_impact(result):
    risk=float(result.get("risk",0)); costs=result.get("costs",{}) or {}
    preventive=float(costs.get("preventive_cost",18000))
    failure=float(costs.get("failure_cost",100000))
    avoided=max(0,failure-preventive)
    return {"preventive_cost":round(preventive),"failure_cost":round(failure),"potential_saving":round(avoided),"roi_pct":round((avoided/preventive*100) if preventive else 0)}
