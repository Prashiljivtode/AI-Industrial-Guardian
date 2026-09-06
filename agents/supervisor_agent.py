"""Guardian Supervisor: combines prediction, anomaly, trend and rules into one auditable decision."""
from datetime import datetime

def supervisor_decision(result, trend="STABLE"):
    risk=float(result.get("risk",0)); anomaly=float(result.get("anomaly_score",0)); rul=float(result.get("rul_hours",240)); sev=float(result.get("sensor_severity",0))
    votes=[]
    votes.append("FAILURE_RISK_HIGH" if risk>=76 else "FAILURE_RISK_ELEVATED" if risk>=51 else "FAILURE_RISK_LOW")
    votes.append("ANOMALY_HIGH" if anomaly>=75 else "ANOMALY_ELEVATED" if anomaly>=50 else "ANOMALY_LOW")
    votes.append("TREND_FAST" if trend=="RISING_FAST" else "TREND_RISING" if trend=="RISING" else "TREND_STABLE")
    votes.append("SENSOR_STRESS_HIGH" if sev>=75 else "SENSOR_STRESS_ELEVATED" if sev>=50 else "SENSOR_STRESS_NORMAL")
    high=sum(v in {"FAILURE_RISK_HIGH","ANOMALY_HIGH","TREND_FAST","SENSOR_STRESS_HIGH"} for v in votes)
    confidence=min(99, round(55 + high*9 + max(risk,anomaly)*0.12,1))
    if risk>=76 or rul<=24 or high>=3: verdict="IMMEDIATE_INSPECTION"
    elif risk>=51 or anomaly>=75 or trend=="RISING_FAST": verdict="PRIORITY_MAINTENANCE"
    elif risk>=26 or anomaly>=50 or trend=="RISING": verdict="SCHEDULE_INSPECTION"
    else: verdict="CONTINUE_MONITORING"
    return {"agent":"Guardian Supervisor","timestamp":datetime.now().isoformat(timespec="seconds"),"verdict":verdict,"confidence":confidence,"evidence_votes":votes,"high_signal_count":high,"risk":round(risk,1),"anomaly":round(anomaly,1),"rul_hours":int(rul),"trend":trend,"safety_note":"Decision support only. Human/PLC safety controls remain authoritative."}
