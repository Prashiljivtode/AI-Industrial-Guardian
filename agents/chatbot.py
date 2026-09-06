import re
from difflib import get_close_matches


def _num(v, default=0):
    try: return float(v)
    except Exception: return default


def _find_machines(query, machines):
    ids = {str(x.get('machine_id','')).upper(): x for x in machines}
    found=[]
    for mid in re.findall(r'\b(?:machine\s*)?(m\d+)\b', query.lower()):
        key=mid.upper()
        if key in ids and key not in [x.get('machine_id') for x in found]: found.append(ids[key])
    return found


def _card(title, body): return f"### {title}\n\n{body}"


def _fleet_stats(machines):
    risks=[_num(m.get('risk')) for m in machines]
    return sum(risks)/len(risks), sum(r>=76 for r in risks), sum(51<=r<76 for r in risks), sum(r<26 for r in risks)


def chatbot_response(query, machines):
    q=(query or '').lower().strip()
    if not machines: return _card('No telemetry', 'No machine telemetry is available yet. Upload a CSV or enable simulation/IoT data first.')

    ranked=sorted(machines,key=lambda x:_num(x.get('risk')) ,reverse=True)
    by_id={str(m.get('machine_id','')).upper():m for m in machines}
    selected_list=_find_machines(q,machines)
    selected=selected_list[0] if selected_list else None
    avg,critical_count,warning_count,healthy_count=_fleet_stats(machines)

    # Greetings / identity
    if re.search(r'\b(hi|hello|hey|namaste|hii|helo)\b', q):
        return _card('Guardian AI', 'Hello! 👋 Main your industrial maintenance copilot hoon. Aap machine risk, failure reason, RUL, trends, maintenance, cost, comparison ya CSV data ke baare me pooch sakte ho.')
    if any(x in q for x in ['tum kya kar','what can you do','help','kya kar sakte']):
        return _card('What I can do', '- Machine health/risk explain karna\n- Highest-risk machine identify karna\n- Failure/RUL outlook dena\n- Sensor trends aur anomalies explain karna\n- Machines compare karna\n- Maintenance priority aur action suggest karna\n- Preventive maintenance ka estimated cost/avoided loss batana')

    # Explicit machine health/status
    if selected and any(k in q for k in ['health','status','condition','haal','kaisa','kesi','kitna risk','risk kitna','rul','remaining']):
        m=selected
        return _card(f"{m['machine_id']} health report",
            f"**Status:** {m.get('status','UNKNOWN')}\n\n**Failure risk:** {m.get('risk',0)}%  · **Health:** {m.get('health_score',0)}/100  · **RUL:** {m.get('rul_hours',0)} h\n\n**Sensors:** Temperature **{m.get('temp','-')}°C** · Vibration **{m.get('vibration','-')}** · Pressure **{m.get('pressure','-')} bar**\n\n**AI diagnosis:** {m.get('root_cause','Review telemetry.')}\n\n**Recommended action:** {m.get('recommendation','Inspect sensor trends.')}" )

    # Why / cause / explanation
    if any(k in q for k in ['why','kyun','kyu','reason','cause','problem','issue','problem kya','reason kya']):
        m=selected or ranked[0]
        return _card(f"Why {m['machine_id']} is at {m.get('risk',0)}% risk",
            f"**Primary diagnosis:** {m.get('root_cause','Sensor conditions require review.')}\n\n**Temperature:** {m.get('temp','-')}°C\n\n**Vibration:** {m.get('vibration','-')}\n\n**Pressure:** {m.get('pressure','-')} bar\n\n**Anomaly score:** {m.get('anomaly_score',0)}/100\n\nThe prediction combines temperature, vibration and pressure; machine ID itself is not used as a sensor signal.")

    # Compare, including Hindi
    if any(k in q for k in ['compare','comparison','tulna','compare karo','difference','farak']) or len(selected_list)>=2:
        if len(selected_list)>=2:
            a,b=selected_list[:2]
        elif len(ranked)>=2:
            a,b=ranked[:2]
        else:
            return _card('Comparison','At least two machines are needed for comparison.')
        winner=a if _num(a.get('risk'))>=_num(b.get('risk')) else b
        return _card('Machine comparison',
            f"**{a['machine_id']}** → Risk **{a.get('risk',0)}%**, Health **{a.get('health_score',0)}/100**, RUL **{a.get('rul_hours',0)} h**\n\n**{b['machine_id']}** → Risk **{b.get('risk',0)}%**, Health **{b.get('health_score',0)}/100**, RUL **{b.get('rul_hours',0)} h**\n\n**Higher priority:** {winner['machine_id']} because its current risk is higher.")

    # Highest / first repair
    if any(k in q for k in ['highest risk','top risk','most risky','riskiest','dangerous','repair first','fix first','pehle','pahle','sabse risky','sabse dangerous','priority','urgent']):
        m=ranked[0]
        return _card('Priority recommendation',f"**{m['machine_id']}** should be reviewed first.\n\nRisk **{m.get('risk',0)}%** · Health **{m.get('health_score',0)}/100** · RUL **{m.get('rul_hours',0)} h**\n\n**Diagnosis:** {m.get('root_cause','Review telemetry.')}\n\n**Action:** {m.get('recommendation','Inspect the machine and review sensor trends.')}")

    # Lowest health
    if any(k in q for k in ['lowest health','least healthy','worst health','low health','sabse kam health','lowest score']):
        m=min(machines,key=lambda x:_num(x.get('health_score'),100))
        return _card('Lowest health score',f"**{m['machine_id']} — {m.get('health_score',0)}/100**\n\nFailure risk: **{m.get('risk',0)}%** · RUL: **{m.get('rul_hours',0)} h**.")

    # Fleet summary / counts
    if ('fleet' in q or 'all machine' in q or 'sab machine' in q or 'overall' in q or 'total' in q) and any(k in q for k in ['summary','health','status','count','kitni','kitne','overall']):
        return _card('Fleet health summary',f"**Machines:** {len(machines)} · **Average risk:** {avg:.0f}% · **Critical:** {critical_count} · **Warning:** {warning_count} · **Healthy:** {healthy_count}\n\nHighest-risk asset: **{ranked[0]['machine_id']}** at **{ranked[0].get('risk',0)}%**.")

    # Critical / warning
    if any(k in q for k in ['critical','criticals','red alert','danger zone']):
        crit=[m for m in ranked if _num(m.get('risk'))>=76]
        return _card('Critical machines', 'No machine is currently in the CRITICAL band.' if not crit else '\n'.join(f"- **{m['machine_id']}** — {m.get('risk',0)}% risk, RUL {m.get('rul_hours',0)} h" for m in crit))
    if 'warning' in q or 'caution' in q:
        warn=[m for m in ranked if 51<=_num(m.get('risk'))<76]
        return _card('Warning machines', 'No machine is currently in the WARNING band.' if not warn else '\n'.join(f"- **{m['machine_id']}** — {m.get('risk',0)}% risk" for m in warn))

    # 24 hour outlook
    if ('24' in q or 'next 24' in q or 'agale 24' in q) and any(k in q for k in ['fail','failure','maintenance','hour','risk','next']):
        urgent=[m for m in machines if _num(m.get('rul_hours'),999)<24]
        if not urgent: return _card('24-hour outlook','No machine currently has an estimated RUL below 24 hours.')
        return _card('24-hour outlook','\n'.join(f"- **{m['machine_id']}** — {m.get('risk',0)}% risk, RUL **{m.get('rul_hours',0)} h**" for m in sorted(urgent,key=lambda x:_num(x.get('rul_hours'),999))))

    # Cost / ROI
    if any(k in q for k in ['cost','loss','avoid','saving','paise','paisa','rupee','₹','kharcha','bachat','kitna loss']):
        total=sum(_num(m.get('costs',{}).get('loss_avoided')) for m in machines)
        top=ranked[0]
        return _card('Business impact',f"Estimated potential loss avoided across the monitored fleet: **₹{total:,.0f}**.\n\nHighest-risk machine: **{top['machine_id']}**. Preventive maintenance is generally prioritized when the modeled avoided loss exceeds the maintenance cost.\n\n*These are demo/model estimates, not guaranteed financial outcomes.*")

    # Trend / anomaly / sensors
    if any(k in q for k in ['trend','sensor','temperature','temp','vibration','pressure','anomaly','abnormal','unusual']):
        m=selected or ranked[0]
        return _card(f"Sensor analysis · {m['machine_id']}",f"Temperature **{m.get('temp','-')}°C** · Vibration **{m.get('vibration','-')}** · Pressure **{m.get('pressure','-')} bar**\n\nAnomaly score: **{m.get('anomaly_score',0)}/100**.\n\nCurrent risk: **{m.get('risk',0)}%**. Diagnosis: **{m.get('root_cause','Review telemetry.')}**\n\nFor historical direction, open the machine's sensor trend chart in Command Center/CSV history.")

    # Maintenance / action / repair
    if any(k in q for k in ['maintenance','repair','fix','action','what should','kya karu','kya kare','kya karna','service','maintain']):
        m=selected or ranked[0]
        return _card(f"Recommended maintenance · {m['machine_id']}",f"**Priority:** {m.get('priority','REVIEW')}\n\n**Action:** {m.get('recommendation','Inspect the machine and review sensor trends.')}\n\n**Reason:** {m.get('root_cause','Sensor anomaly detected.')}\n\n**RUL:** {m.get('rul_hours',0)} h")

    # RUL only
    if any(k in q for k in ['rul','remaining useful','kitne ghante','kab fail','when fail','failure kab']):
        m=selected or ranked[0]
        return _card(f"RUL outlook · {m['machine_id']}",f"Estimated Remaining Useful Life: **{m.get('rul_hours',0)} hours** ({m.get('rul_urgency','review')}).\n\nCurrent risk: **{m.get('risk',0)}%**. This is a model estimate and should be validated against real maintenance observations.")

    # Generic machine mention should still be useful
    if selected:
        m=selected
        return _card(f"{m['machine_id']} snapshot",f"Risk **{m.get('risk',0)}%** · Health **{m.get('health_score',0)}/100** · RUL **{m.get('rul_hours',0)} h** · Status **{m.get('status','UNKNOWN')}**\n\nDiagnosis: **{m.get('root_cause','Review telemetry.')}**\n\nAsk **why**, **maintenance kya karna hai**, **trend**, or **compare** for a deeper answer.")

    return _card('Guardian AI', 'Mujhe samajh nahi aaya — aap inme se kuch pooch sakte ho:\n\n- **M1 risky kyun hai?**\n- **M1 ka health aur RUL kya hai?**\n- **Kaunsi machine pehle repair karu?**\n- **M1 aur M2 compare karo**\n- **24 hours me kaunsi machine risky hai?**\n- **Sensor trend/anomaly batao**\n- **Maintenance ka kya action hai?**\n- **Potential loss/saving kitni hai?**')
