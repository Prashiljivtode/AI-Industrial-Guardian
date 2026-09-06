"""Rule-guided maintenance decision agent.
It converts the ML/risk output into an auditable recommended action.
It never directly shuts down equipment; a human/PLC safety layer must approve that.
"""
from datetime import datetime

def maintenance_decision(result, trend="STABLE"):
    risk=float(result.get("risk",0)); anomaly=float(result.get("anomaly_score",0)); rul=float(result.get("rul_hours",240)); severity=float(result.get("sensor_severity",0))
    status=result.get("status","HEALTHY")
    if risk>=76 or rul<=24:
        action="CREATE_EMERGENCY_WORK_ORDER"
        urgency="IMMEDIATE"
        reason="Critical failure risk or very low estimated RUL. Inspect before continued operation."
        approval="HUMAN_APPROVAL_REQUIRED"
    elif risk>=51 or anomaly>=75 or trend=="RISING_FAST":
        action="SCHEDULE_PRIORITY_MAINTENANCE"
        urgency="URGENT"
        reason="Risk, anomaly, or rapidly worsening trend indicates elevated maintenance need."
        approval="MAINTENANCE_APPROVAL_REQUIRED"
    elif risk>=26 or anomaly>=50 or trend=="RISING":
        action="OPEN_INSPECTION_TASK"
        urgency="SCHEDULE"
        reason="Early degradation signals detected; inspect and continue monitoring."
        approval="STANDARD_WORKFLOW"
    else:
        action="CONTINUE_MONITORING"
        urgency="MONITOR"
        reason="No strong degradation signal detected."
        approval="NO_ACTION"
    return {
        "agent":"Guardian Maintenance Agent",
        "timestamp":datetime.now().isoformat(timespec="seconds"),
        "action":action,"urgency":urgency,"reason":reason,
        "approval":approval,"risk":round(risk,1),"rul_hours":int(rul),
        "anomaly_score":round(anomaly,1),"sensor_severity":round(severity,1),"trend":trend,
        "guardrail":"AI recommends; safety interlocks and human/PLC controls remain authoritative."
    }
