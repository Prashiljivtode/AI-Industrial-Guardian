from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd, io
from .db import init_db, get_conn, now
from .schemas import MachineIn, MaintenanceIn, ChatIn, TelemetryIn, BulkTelemetryIn
from .service import seed_from_json, list_machines, save_machine, delete_machine, analyze, fleet_analysis, record_telemetry, recent_telemetry, chatbot_response, model_metadata
from modules.csv_importer import load_csv

app=FastAPI(title="AI Industrial Guardian API",version="4.0.0",description="AI predictive-maintenance backend with telemetry, CSV ingestion, analytics, alerts, maintenance and assistant APIs.")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def startup(): init_db(); seed_from_json()
@app.get("/")
def root(): return {"name":"AI Industrial Guardian API","status":"online","version":"4.0.0"}
@app.get("/health")
def health(): return {"status":"healthy","database":"sqlite","ml":"online"}
@app.get("/api/v1/machines")
def machines():
    data=list_machines(); return {"count":len(data),"machines":data}
@app.post("/api/v1/machines/analyze")
def analyze_machine(machine:MachineIn): return analyze(machine)
@app.post("/api/v1/machines")
def add_machine(machine:MachineIn):
    if any(x["machine_id"].upper()==machine.machine_id.upper() for x in list_machines()): raise HTTPException(409,"Machine ID already exists")
    return save_machine(machine)
@app.post("/api/v1/machines/bulk")
def bulk_add(payload:list[MachineIn]):
    added=[]; errors=[]
    existing={x["machine_id"].upper() for x in list_machines()}
    for m in payload:
        if m.machine_id.upper() in existing: errors.append({"machine_id":m.machine_id,"error":"already exists"}); continue
        try: added.append(save_machine(m)); existing.add(m.machine_id.upper())
        except Exception as e: errors.append({"machine_id":m.machine_id,"error":str(e)})
    return {"added":added,"errors":errors}
@app.post("/api/v1/machines/csv")
async def csv_import(file:UploadFile=File(...)):
    if not file.filename.lower().endswith('.csv'): raise HTTPException(400,"Upload a CSV file")
    try: df=load_csv(io.BytesIO(await file.read()))
    except Exception as e: raise HTTPException(400,str(e))
    preview=[]
    for r in df.to_dict("records"):
        m=MachineIn(machine_id=r["machine_id"],machine_type=r.get("machine_type","Industrial Machine"),temp=r["temp"],vibration=r["vibration"],pressure=r["pressure"]); preview.append(analyze(m))
    return {"count":len(preview),"analysis":preview}
@app.delete("/api/v1/machines/{machine_id}")
def remove(machine_id:str):
    if not delete_machine(machine_id): raise HTTPException(404,"Machine not found")
    return {"deleted":machine_id}
@app.get("/api/v1/fleet/analysis")
def fleet(): return {"machines":fleet_analysis()}
@app.post("/api/v1/telemetry/{machine_id}")
def telemetry(machine_id:str, body:TelemetryIn):
    from .schemas import MachineIn
    m=next((x for x in list_machines() if x["machine_id"]==machine_id),None)
    if not m: raise HTTPException(404,"Machine not found")
    result=analyze(MachineIn(machine_id=machine_id,machine_type=m["machine_type"],temp=body.temp,vibration=body.vibration,pressure=body.pressure)); record_telemetry(result); return result
@app.get("/api/v1/telemetry/{machine_id}")
def telemetry_history(machine_id:str,limit:int=100): return {"machine_id":machine_id,"telemetry":recent_telemetry(machine_id,max(1,min(limit,500)))}
@app.post("/api/v1/chat")
def chat(body:ChatIn): return {"query":body.query,"answer":chatbot_response(body.query,fleet_analysis())}
@app.post("/api/v1/agent/decision/{machine_id}")
def agent_decision(machine_id:str):
    from agents.autonomous_agent import maintenance_decision
    from .schemas import MachineIn
    m=next((x for x in list_machines() if x["machine_id"]==machine_id),None)
    if not m: raise HTTPException(404,"Machine not found")
    result=analyze(MachineIn(machine_id=machine_id,machine_type=m["machine_type"],temp=m["temp"],vibration=m["vibration"],pressure=m["pressure"]))
    return maintenance_decision(result)

@app.post("/api/v1/telemetry/bulk")
def telemetry_bulk(payload:list[BulkTelemetryIn]):
    out=[]
    for body in payload:
        m=next((x for x in list_machines() if x["machine_id"]==body.machine_id),None)
        if not m: continue
        result=analyze(MachineIn(machine_id=body.machine_id,machine_type=m["machine_type"],temp=body.temp,vibration=body.vibration,pressure=body.pressure))
        record_telemetry(result); out.append(result)
    return {"count":len(out),"results":out}

@app.get("/api/v1/iot/status")
def iot_status():
    rows=fleet_analysis(); return {"gateway":"API ONLINE","machines":len(rows),"telemetry_endpoint":"POST /api/v1/telemetry/{machine_id}","agent_endpoint":"POST /api/v1/agent/decision/{machine_id}","safety":"AI recommendation only; no autonomous shutdown"}

@app.get("/api/v1/model")
def model(): return model_metadata()
@app.post("/api/v1/maintenance")
def maintenance(body:MaintenanceIn):
    with get_conn() as c:
        cur=c.execute("INSERT INTO maintenance(machine_id,issue,action,team,cost,status,timestamp) VALUES(?,?,?,?,?,?,?)",(body.machine_id,body.issue,body.action,body.team,body.cost,body.status,now()))
    return {"id":cur.lastrowid,"saved":True}
@app.get("/api/v1/maintenance")
def maintenance_history():
    with get_conn() as c: return {"records":[dict(r) for r in c.execute("SELECT * FROM maintenance ORDER BY id DESC")]}
@app.get("/api/v1/alerts")
def alerts():
    rows=[]
    for r in fleet_analysis():
        if r["risk"]>=76: rows.append({"machine_id":r["machine_id"],"severity":"CRITICAL","message":f'{r["machine_id"]} has {r["risk"]}% failure risk'})
        elif r["risk"]>=51: rows.append({"machine_id":r["machine_id"],"severity":"WARNING","message":f'{r["machine_id"]} requires maintenance planning'})
    return {"alerts":rows}
