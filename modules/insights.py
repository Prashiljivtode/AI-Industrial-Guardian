from datetime import datetime
import pandas as pd

def data_quality(df):
    required={"machine_id","temp","vibration","pressure"}
    missing=required-set(df.columns)
    issues=[]
    if missing: issues.append("Missing columns: "+", ".join(sorted(missing)))
    for c in ["temp","vibration","pressure"]:
        if c in df:
            if df[c].isna().any(): issues.append(f"{c}: missing values")
            if (~pd.to_numeric(df[c], errors="coerce").notna()).any(): issues.append(f"{c}: non-numeric values")
    return {"valid":not issues,"issues":issues}

def what_if_predict(predict_fn, temp, vibration, pressure):
    return predict_fn(temp,vibration,pressure)

def trend_direction(hist):
    if hist is None or len(hist)<3: return "Insufficient history"
    h=hist.tail(min(12,len(hist)))
    risk_delta=float(h.risk.iloc[-1]-h.risk.iloc[0]) if "risk" in h else 0
    health_delta=float(h.health_score.iloc[-1]-h.health_score.iloc[0]) if "health_score" in h else 0
    if risk_delta>5 or health_delta<-5: return "Deteriorating"
    if risk_delta<-5 or health_delta>5: return "Improving"
    return "Stable"

def report_markdown(row, trend="Stable"):
    c=row.get("costs",{})
    return f'''# AI Machine Health Report — {row["machine_id"]}

**Generated:** {datetime.now().astimezone().strftime("%d %b %Y %H:%M")}  
**Machine type:** {row.get("machine_type","Industrial Machine")}  
**Status:** {row["status"]}

## AI Assessment
- Failure risk: **{row["risk"]}%**
- Health score: **{row["health_score"]}/100**
- Estimated RUL: **{row["rul_hours"]} hours**
- Risk trend: **{trend}**
- Sensor severity: **{row["sensor_severity"]}/100**

## Diagnosis
{row["root_cause"]}

## Recommended action
{row["recommendation"]}

## Business impact (demo estimates)
- Preventive maintenance: ₹{c.get("preventive_cost",0):,.0f}
- Potential failure cost: ₹{c.get("failure_cost",0):,.0f}
- Potential loss avoided: ₹{c.get("loss_avoided",0):,.0f}
- Estimated downtime: {c.get("downtime_hours",0):.1f} hours

> This report uses simulated/demo telemetry and estimates; it is not an industrial safety certification.
'''
