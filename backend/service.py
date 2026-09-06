from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from modules.predictor import predict_machine, model_metadata
from modules.risk_engine import sensor_severity, maintenance_costs
from modules.scheduler import priority_score
from agents.root_cause import root_cause
from agents.chatbot import chatbot_response
from modules.rul_engine import rul_label
from .db import get_conn, now

def analyze(m):
    p=predict_machine(m.temp,m.vibration,m.pressure)
    sev=sensor_severity(m.temp,m.vibration,m.pressure)
    costs=maintenance_costs(p["risk"],p["rul_hours"],p["status"])
    return {**m.model_dump(), **p, "root_cause":root_cause(m.temp,m.vibration,m.pressure,p["risk"]), "sensor_severity":sev, "rul_urgency":rul_label(p["rul_hours"]), "costs":costs, "priority_score":priority_score({**m.model_dump(),**p,"sensor_severity":sev})}

def seed_from_json():
    with get_conn() as c:
        if c.execute("SELECT COUNT(*) n FROM machines").fetchone()["n"]: return
        f=ROOT/"data"/"machines.json"
        if f.exists():
            data=json.loads(f.read_text(encoding="utf-8"))
            for m in data:
                c.execute("INSERT OR IGNORE INTO machines VALUES (?,?,?,?,?,?,?)", (m["machine_id"],m.get("machine_type","Industrial Motor"),m["temp"],m["vibration"],m["pressure"],now(),now()))

def list_machines():
    with get_conn() as c: rows=[dict(r) for r in c.execute("SELECT * FROM machines ORDER BY machine_id")]
    return rows

def save_machine(m):
    with get_conn() as c:
        c.execute("INSERT INTO machines VALUES (?,?,?,?,?,?,?)",(m.machine_id,m.machine_type,m.temp,m.vibration,m.pressure,now(),now()))
    return analyze(m)

def delete_machine(mid):
    with get_conn() as c:
        cur=c.execute("DELETE FROM machines WHERE machine_id=?",(mid,))
        return cur.rowcount>0

def fleet_analysis():
    from .schemas import MachineIn
    return [analyze(MachineIn(machine_id=m["machine_id"], machine_type=m["machine_type"], temp=m["temp"], vibration=m["vibration"], pressure=m["pressure"])) for m in list_machines()]

def record_telemetry(result):
    with get_conn() as c:
        c.execute("INSERT INTO telemetry(machine_id,temp,vibration,pressure,risk,health_score,rul_hours,status,timestamp) VALUES (?,?,?,?,?,?,?,?,?)",(result["machine_id"],result["temp"],result["vibration"],result["pressure"],result["risk"],result["health_score"],result["rul_hours"],result["status"],now()))

def recent_telemetry(mid,limit=100):
    with get_conn() as c: return [dict(r) for r in c.execute("SELECT * FROM telemetry WHERE machine_id=? ORDER BY id DESC LIMIT ?",(mid,limit))]
