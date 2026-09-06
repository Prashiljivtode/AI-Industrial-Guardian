"""Generate structured maintenance work orders from AI evidence."""
from datetime import datetime

def create_work_order(result, decision):
    risk=float(result.get("risk",0)); priority="P1" if risk>=76 else "P2" if risk>=51 else "P3" if risk>=26 else "P4"
    return {"work_order_id":f"WO-{datetime.now().strftime('%Y%m%d-%H%M%S')}","created_at":datetime.now().isoformat(timespec="seconds"),"machine_id":result.get("machine_id"),"priority":priority,"status":"DRAFT","reason":result.get("root_cause"),"recommended_action":result.get("recommendation"),"agent_action":decision.get("verdict",decision.get("action")),"risk_pct":result.get("risk"),"rul_hours":result.get("rul_hours"),"approval":"MAINTENANCE_TEAM_APPROVAL_REQUIRED","checklist":["Verify sensor readings","Inspect suspected component","Record findings and parts used","Re-run AI assessment after maintenance"],"safety_note":"AI creates a draft only; authorized personnel must approve and execute work."}
