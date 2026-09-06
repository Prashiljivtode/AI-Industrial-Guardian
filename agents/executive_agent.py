"""Deterministic executive briefing agent: auditable and local-data driven."""
from datetime import datetime

def executive_brief(results):
    if not results:
        return {"headline":"No telemetry available","actions":[],"timestamp":datetime.now().isoformat(timespec="seconds")}
    ranked=sorted(results,key=lambda x: float(x.get("risk",0)),reverse=True)
    critical=[r for r in results if float(r.get("risk",0))>=76]
    warning=[r for r in results if 51<=float(r.get("risk",0))<76]
    actions=[]
    for r in ranked[:3]:
        risk=float(r.get("risk",0))
        if risk>=51:
            actions.append(f"Prioritize {r['machine_id']} ({risk:.0f}% risk): {r.get('recommendation','inspect telemetry')}")
    avg=sum(float(r.get("risk",0)) for r in results)/len(results)
    return {"agent":"Guardian Executive Agent","timestamp":datetime.now().isoformat(timespec="seconds"),"headline":f"Fleet average risk is {avg:.0f}%. {len(critical)} critical and {len(warning)} warning assets require attention.","top_asset":ranked[0]["machine_id"],"top_risk":round(float(ranked[0].get("risk",0)),1),"actions":actions or ["Continue monitoring fleet telemetry."],"safety_note":"Decision support only; authorized personnel and plant safety systems remain authoritative."}
