from pathlib import Path
from datetime import datetime, timedelta
import io, json, time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.predictor import predict_machine, model_metadata
from modules.scheduler import priority_score
from modules.risk_engine import sensor_severity, maintenance_costs
from modules.rul_engine import rul_label
from modules.simulator import BASE_MACHINES, next_snapshot, append_history, load_history
from agents.chatbot import chatbot_response
from agents.root_cause import root_cause, contribution_scores
from agents.self_learning_agent import retrain
from modules.machine_registry import load_machines, add_machine, remove_machine, save_machines
from modules.analytics import anomaly_score
from modules.csv_importer import load_csv, latest_snapshot
from modules.insights import trend_direction, report_markdown
from modules.fleet_intelligence import benchmark, portfolio_stats, scenario_sweep
from agents.autonomous_agent import maintenance_decision
from agents.supervisor_agent import supervisor_decision
from modules.forecast import forecast_risk
from modules.work_orders import create_work_order
from modules.fusion import fusion_score
from modules.scenario_engine import scenario_steps, maintenance_impact
from agents.executive_agent import executive_brief
from dashboard.digital_twin import factory_view

try:
    from streamlit_mic_recorder import mic_recorder
except Exception:
    mic_recorder = None
from modules.voice_assistant import transcribe, speak

ROOT = Path(__file__).resolve().parent
MAINT_PATH = ROOT / "data" / "maintenance_history.csv"
HISTORY_PATH = ROOT / "data" / "sensor_history.csv"

st.set_page_config(
    page_title="AI Industrial Guardian",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1rem; max-width: 1550px;}
.hero {padding: 26px; border: 1px solid #293142; border-radius: 20px;
       background: linear-gradient(135deg,#0d1522,#182233); margin-bottom: 18px;}
.hero h1 {margin: 0; font-size: 2.35rem;}
.hero p {color:#94a3b8; margin:.4rem 0 0;}
.card {padding:18px; border:1px solid #293142; border-radius:14px; background:#111722;}
.small-note {color:#94a3b8; font-size:.88rem;}
.status-card {padding:14px 16px; border-radius:12px; border:1px solid #293142; background:#111722;}
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
if "machines" not in st.session_state:
    st.session_state.machines = load_machines(BASE_MACHINES)
if "live" not in st.session_state:
    st.session_state.live = False
if "critical_event" not in st.session_state:
    st.session_state.critical_event = False
if "csv_preview" not in st.session_state:
    st.session_state.csv_preview = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scenario_running" not in st.session_state:
    st.session_state.scenario_running = False
if "generated_wo" not in st.session_state:
    st.session_state.generated_wo = None
if "history_seeded" not in st.session_state:
    st.session_state.history_seeded = False
if "last_history_write" not in st.session_state:
    st.session_state.last_history_write = 0.0


def build_results(raw):
    results = []
    for m in raw:
        try:
            p = predict_machine(m["temp"], m["vibration"], m["pressure"])
            sev = sensor_severity(m["temp"], m["vibration"], m["pressure"])
            costs = maintenance_costs(p["risk"], p["rul_hours"], p["status"])
            item = {
                **m,
                "machine_id": str(m.get("machine_id", "UNKNOWN")).upper(),
                "machine_type": m.get("machine_type", "Industrial Machine"),
                **p,
                "root_cause": root_cause(m["temp"], m["vibration"], m["pressure"], p["risk"]),
                "sensor_severity": sev,
                "rul_urgency": rul_label(p["rul_hours"]),
                "costs": costs,
                "priority_score": priority_score({**m, **p, "sensor_severity": sev}),
                "anomaly_score": anomaly_score(m["temp"], m["vibration"], m["pressure"]),
            }
            results.append(item)
        except Exception as exc:
            results.append({
                **m,
                "machine_id": str(m.get("machine_id", "UNKNOWN")).upper(),
                "machine_type": m.get("machine_type", "Industrial Machine"),
                "risk": 0, "status": "HEALTHY", "priority": "MONITOR",
                "rul_hours": 240, "health_score": 100,
                "recommendation": "Check model configuration",
                "root_cause": str(exc), "sensor_severity": 0,
                "rul_urgency": "LOW URGENCY",
                "costs": maintenance_costs(0, 240, "HEALTHY"),
                "priority_score": 0, "anomaly_score": 0,
            })
    return results


def persist_fleet():
    save_machines(st.session_state.machines)


def add_records(rows):
    existing = {str(m["machine_id"]).upper() for m in st.session_state.machines}
    added = 0
    for r in rows:
        mid = str(r["machine_id"]).upper()
        if mid in existing:
            continue
        st.session_state.machines.append({
            "machine_id": mid,
            "machine_type": r.get("machine_type", "Industrial Machine"),
            "temp": round(float(r["temp"]), 1),
            "vibration": round(float(r["vibration"]), 2),
            "pressure": round(float(r["pressure"]), 1),
        })
        existing.add(mid)
        added += 1
    persist_fleet()
    return added


def ensure_demo_history(results):
    """Ensure every machine has enough visible history points for trend charts."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.DataFrame()
    if HISTORY_PATH.exists():
        try:
            existing = pd.read_csv(HISTORY_PATH, parse_dates=["timestamp"])
        except Exception:
            existing = pd.DataFrame()

    rows = []
    rng = np.random.default_rng(17)
    now = pd.Timestamp.now().floor("min")
    for r in results:
        mid = str(r["machine_id"])
        have = existing[existing.get("machine_id", pd.Series(dtype=str)).astype(str) == mid] if not existing.empty and "machine_id" in existing.columns else pd.DataFrame()
        if len(have) >= 3:
            continue
        for i in range(12 - len(have)):
            frac = i / max(1, 11 - len(have))
            rows.append({
                "timestamp": now - pd.Timedelta(minutes=(11 - i) * 5),
                "machine_id": mid,
                "temp": round(max(35, r["temp"] + rng.normal(0, 1.4) - (1-frac) * 1.2), 1),
                "vibration": round(max(0.02, r["vibration"] + rng.normal(0, 0.045) - (1-frac) * 0.04), 2),
                "pressure": round(max(15, r["pressure"] + rng.normal(0, 0.65) - (1-frac) * 0.5), 1),
                "risk": round(max(0, min(100, r["risk"] + rng.normal(0, 2.5) - (1-frac) * 2.0)), 1),
                "health_score": round(max(0, min(100, r["health_score"] + rng.normal(0, 2.0) + (1-frac) * 2.0)), 1),
            })
    if rows:
        merged = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True) if not existing.empty else pd.DataFrame(rows)
        merged = merged.sort_values("timestamp").tail(2500)
        merged.to_csv(HISTORY_PATH, index=False)
    st.session_state.history_seeded = True


def write_history_once(results):
    # Avoid adding the same snapshot on every Streamlit rerun.
    now = time.time()
    if now - st.session_state.last_history_write < 45:
        return
    append_history(results)
    st.session_state.last_history_write = now


def history_frame(machine_id, points=72):
    h = load_history(str(machine_id), points)
    if h.empty:
        return h
    h = h.copy()
    h["timestamp"] = pd.to_datetime(h["timestamp"], errors="coerce")
    for c in ["temp", "vibration", "pressure", "risk", "health_score"]:
        if c in h.columns:
            h[c] = pd.to_numeric(h[c], errors="coerce")
    return h.dropna(subset=["timestamp"])


def trend_chart(history, y, title, y_title=None):
    fig = go.Figure()
    if history.empty or y not in history.columns:
        fig.add_annotation(text="No telemetry history available yet", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
    else:
        clean = history.dropna(subset=[y]).sort_values("timestamp")
        fig.add_trace(go.Scatter(
            x=clean["timestamp"], y=clean[y], mode="lines+markers",
            name=y, line=dict(width=3), marker=dict(size=6),
        ))
    fig.update_layout(title=title, height=300, margin=dict(l=10, r=10, t=48, b=10),
                      xaxis_title="Time", yaxis_title=y_title or y, hovermode="x unified")
    return fig


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## ⚙️ Control Center")
    role = st.selectbox("Role", ["Plant Manager", "Maintenance Engineer", "Analyst"])
    source = st.radio("Data Source", ["Simulation", "CSV Upload", "Live IoT/API"], index=0)
    st.session_state.live = st.toggle("⚡ Live sensor simulation", st.session_state.live)
    speed = st.select_slider("Simulation intensity", ["Low", "Normal", "High"], value="Normal")

    if st.button("🔄 Refresh Sensors", use_container_width=True):
        st.session_state.machines = next_snapshot(
            st.session_state.machines, int(time.time()), st.session_state.critical_event
        )
        persist_fleet()
        st.session_state.last_history_write = 0
        st.rerun()
    if st.button("🚨 Simulate Critical Event", use_container_width=True):
        st.session_state.critical_event = True
        st.session_state.machines = next_snapshot(st.session_state.machines, 42, True)
        persist_fleet()
        st.session_state.last_history_write = 0
        st.rerun()
    if st.button("↩ Reset Simulation", use_container_width=True):
        st.session_state.critical_event = False
        st.session_state.machines = load_machines(BASE_MACHINES)
        persist_fleet()
        st.session_state.history_seeded = False
        st.session_state.last_history_write = 0
        st.rerun()

    st.divider()
    st.success("● AI Engine Online")
    if source == "Live IoT/API":
        st.warning("● Waiting for IoT telemetry")
    else:
        st.success("● Backend Ready")
    st.caption("Demo estimates are clearly labeled. Real values require connected external telemetry.")

# Simulation changes only happen in Simulation mode.
if source == "Simulation" and st.session_state.live:
    divisor = 1 if speed == "High" else 2 if speed == "Normal" else 4
    st.session_state.machines = next_snapshot(
        st.session_state.machines, int(time.time()) // divisor, st.session_state.critical_event
    )
    persist_fleet()

results = build_results(st.session_state.machines)
df = pd.DataFrame(results)
ensure_demo_history(results)
if source == "Simulation":
    write_history_once(results)

critical = int((df.risk >= 76).sum())
warning = int((df.risk >= 51).sum())
watch = int(((df.risk >= 26) & (df.risk < 51)).sum())
healthy = int((df.risk < 26).sum())
avg_risk = float(df.risk.mean()) if not df.empty else 0

# ---------- Header ----------
st.markdown(
    '<div class="hero"><h1>🏭 AI Industrial Guardian</h1>'
    '<p>AI-Powered Predictive Maintenance & Industrial Intelligence · Full-Stack Edition</p></div>',
    unsafe_allow_html=True,
)

ks = st.columns(6)
ks[0].metric("Machines", len(df))
ks[1].metric("Critical", critical)
ks[2].metric("Warning", warning)
ks[3].metric("Healthy", healthy)
ks[4].metric("Avg Risk", f"{avg_risk:.0f}%")
ks[5].metric("Needs Attention", critical + warning)

if critical:
    st.error(f"🚨 {critical} critical machine(s) need immediate inspection.")
elif warning:
    st.warning(f"⚠️ {warning} machine(s) are in the warning band.")
else:
    st.success("✓ Fleet operating without critical alerts.")

if source == "Simulation":
    st.info("DATA SOURCE: SIMULATION · Synthetic industrial telemetry for demonstration")
elif source == "CSV Upload":
    st.info("DATA SOURCE: CSV · Upload telemetry, review AI analysis, then approve machines")
else:
    st.info("DATA SOURCE: LIVE IoT/API · Waiting for external telemetry; no device command is issued by this UI")

# ---------- Navigation ----------
sections = [
    "🏭 Command Center",
    "🤖 AI Copilot",
    "🔬 Machine Analysis",
    "🔮 Simulation Lab",
    "🛠️ Maintenance & Work Orders",
    "📡 Data, IoT & Reports",
]
section = st.sidebar.radio("Navigation", sections, key="main_navigation")
st.sidebar.caption("Six focused views · deployment-ready demo mode")

# ---------- Command Center ----------
if section == "🏭 Command Center":
    st.subheader("Fleet Intelligence")
    st.caption("One screen for fleet health, risk ranking, alerts and the machine digital passport.")

    stats = portfolio_stats(df)
    a, b, c, d, e = st.columns(5)
    a.metric("Fleet Risk", f"{stats['risk']}%")
    b.metric("Fleet Health", f"{stats['health']}/100")
    c.metric("Anomaly Index", f"{stats['anomaly']}/100")
    d.metric("Critical", stats["critical"])
    e.metric("Warning", stats["warning"])

    bench = benchmark(df)
    view = bench[["fleet_rank", "machine_id", "machine_type", "risk", "health_score", "anomaly_score", "rul_hours", "attention_index"]].copy()
    view.columns = ["Rank", "Machine", "Type", "Risk %", "Health", "Anomaly", "RUL h", "Attention"]
    st.dataframe(view, use_container_width=True, hide_index=True, height=310)

    selected = st.selectbox("🔍 Select machine", df.machine_id.tolist(), index=int(df.risk.argmax()), key="command_machine")
    row = df[df.machine_id == selected].iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Risk", f"{row.risk}%")
    c2.metric("Health", f"{row.health_score}/100")
    c3.metric("RUL", f"{row.rul_hours} h")
    c4.metric("Temp", f"{row.temp} °C")
    c5.metric("Vibration", f"{row.vibration}")
    c6.metric("Anomaly", f"{row.anomaly_score}/100")

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### 🧠 AI Diagnosis")
        st.markdown(f'<div class="card"><b>{row.root_cause}</b><br><br>'
                    f'<span class="small-note">Risk {row.risk}% · RUL {row.rul_hours} h · Trend {trend_direction(history_frame(selected))}</span></div>',
                    unsafe_allow_html=True)
        st.markdown("### 🔧 Recommended Action")
        if row.risk >= 51:
            st.warning(row.recommendation)
        else:
            st.info(row.recommendation)
    with right:
        st.markdown("### 🪪 Machine Digital Passport")
        st.write(f"**Machine:** {row.machine_id}")
        st.write(f"**Type:** {row.machine_type}")
        st.write(f"**Priority:** {row.priority}")
        st.write(f"**Sensor severity:** {row.sensor_severity}/100")
        st.write(f"**RUL urgency:** {row.rul_urgency}")
        passport = row.to_dict()
        st.download_button("⬇️ Export Passport", json.dumps(passport, indent=2, default=str),
                           f"{row.machine_id}_digital_passport.json", "application/json")

# ---------- AI Copilot ----------
elif section == "🤖 AI Copilot":
    st.subheader("🧠 Guardian AI Copilot")
    st.caption("Ask questions about the current fleet. Answers are grounded in the project's telemetry and AI results.")

    quick = [
        "Which machine should I repair first?",
        "Why is M1 risky?",
        "M1 ka health aur RUL kya hai?",
        "Which machines are critical?",
        "Compare M1 and M2",
        "What is the fleet overall status?",
        "What maintenance action is needed?",
        "How much potential loss could preventive maintenance avoid?",
    ]
    q = st.selectbox("Quick question", quick)
    manual = st.text_input("Or ask your own question", placeholder="e.g. Why is M5 risky? Compare M1 and M3.")
    query = manual.strip() or q
    if st.button("🤖 Ask Guardian AI", use_container_width=True):
        answer = chatbot_response(query, results)
        st.session_state.chat_history.append((query, answer))

    if st.session_state.chat_history:
        question, answer = st.session_state.chat_history[-1]
        st.markdown(f'<div class="card"><b>👤 You:</b> {question}<br><br><b>🤖 Guardian AI:</b><br>{answer}</div>', unsafe_allow_html=True)
        with st.expander("Conversation history"):
            for old_q, old_a in reversed(st.session_state.chat_history[-8:]):
                st.markdown(f"**You:** {old_q}\n\n{old_a}\n\n---")
    else:
        st.info("Try asking: **Why is M1 risky?** or **Which machine should I repair first?**")

    st.divider()
    st.markdown("### 🎙️ Voice AI")
    st.caption("Speak or upload a WAV question. It uses the same fleet-aware assistant.")
    audio = st.file_uploader("Upload WAV recording", type=["wav"], key="voice_upload")
    mic_audio = mic_recorder(start_prompt="🎤 Start speaking", stop_prompt="⏹ Stop", just_once=True, key="guardian_mic") if mic_recorder else None
    if mic_audio and st.button("🧠 Analyze Microphone", key="analyze_mic"):
        class AudioBlob:
            def __init__(self, data): self._data = data
            def getvalue(self): return self._data
        text = transcribe(AudioBlob(mic_audio.get("bytes", b"")))
        if text and not text.startswith("VOICE_ERROR"):
            st.success(text)
            st.info(chatbot_response(text, results))
    if audio and st.button("🎤 Transcribe Uploaded Voice"):
        text = transcribe(audio)
        if text:
            st.write(f"**Transcript:** {text}")
            if not text.startswith("VOICE_ERROR"):
                response = chatbot_response(text, results)
                st.success(response)
                try:
                    voice_path = speak(response)
                    if voice_path:
                        with open(voice_path, "rb") as f:
                            st.audio(f.read(), format="audio/wav")
                except Exception:
                    pass

# ---------- Machine Analysis ----------
elif section == "🔬 Machine Analysis":
    st.subheader("🔬 Machine Analysis & Digital Twin")
    machine = st.selectbox("Select machine", df.machine_id.tolist(), key="analysis_machine")
    row = df[df.machine_id == machine].iloc[0]
    hist = history_frame(machine)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", row.status)
    c2.metric("Risk", f"{row.risk}%")
    c3.metric("RUL", f"{row.rul_hours} h")
    c4.metric("Health", f"{row.health_score}/100")

    st.markdown("### 📈 Sensor & Risk Trends")
    if len(hist) >= 2:
        cols = st.columns(2)
        cols[0].plotly_chart(trend_chart(hist, "temp", "Temperature Trend", "°C"), use_container_width=True)
        cols[1].plotly_chart(trend_chart(hist, "vibration", "Vibration Trend", "Vibration"), use_container_width=True)
        cols = st.columns(2)
        cols[0].plotly_chart(trend_chart(hist, "pressure", "Pressure Trend", "bar"), use_container_width=True)
        cols[1].plotly_chart(trend_chart(hist, "risk", "AI Risk Trend", "%"), use_container_width=True)
        st.caption(f"Trend status: **{trend_direction(hist)}** · {len(hist)} telemetry points")
    else:
        st.info("Collecting telemetry history. Refresh sensors or upload CSV history to populate the charts.")

    contrib = contribution_scores(row.temp, row.vibration, row.pressure)
    cf = pd.DataFrame({"Sensor": list(contrib.keys()), "Contribution": list(contrib.values())})
    st.plotly_chart(px.bar(cf, x="Sensor", y="Contribution", range_y=[0, 100], title="Explainable AI · Sensor contribution"), use_container_width=True)

    st.markdown("### 🧬 Digital Twin")
    st.plotly_chart(factory_view(results, machine), use_container_width=True)

    st.markdown("### 🧠 AI Supervisor")
    trend = trend_direction(hist)
    fusion, agreement = fusion_score(row.to_dict())
    sup = supervisor_decision(row.to_dict(), trend)
    a, b, c, d = st.columns(4)
    a.metric("Fusion Risk", f"{fusion}%")
    b.metric("Signal Agreement", f"{agreement}%")
    c.metric("Confidence", f"{sup['confidence']}%")
    d.metric("Verdict", sup["verdict"])
    st.write("**Evidence:** " + " · ".join(sup["evidence_votes"]))

    forecast, slope = forecast_risk(hist, row.risk, 8)
    st.plotly_chart(px.line(pd.DataFrame(forecast), x="hours_ahead", y="forecast_risk", markers=True,
                            title=f"Short-horizon risk forecast · slope {slope:+.2f}/step"), use_container_width=True)
    with st.expander("🔧 Technical supervisor details"):
        st.json(sup)

# ---------- Simulation ----------
elif section == "🔮 Simulation Lab":
    st.subheader("🔮 What-If & Failure Simulation")
    base_id = st.selectbox("Base machine", df.machine_id.tolist(), key="whatif_machine")
    base = df[df.machine_id == base_id].iloc[0]

    c1, c2, c3 = st.columns(3)
    wt = c1.slider("Temperature °C", 35.0, 120.0, float(base.temp), 0.5)
    wv = c2.slider("Vibration", 0.0, 2.5, float(base.vibration), 0.01)
    wp = c3.slider("Pressure bar", 15.0, 60.0, float(base.pressure), 0.5)
    simulated = predict_machine(wt, wv, wp)
    delta = float(simulated["risk"]) - float(base.risk)
    impact = maintenance_impact({**simulated, "costs": maintenance_costs(simulated["risk"], simulated["rul_hours"], simulated["status"])})

    a, b, c, d = st.columns(4)
    a.metric("Scenario Risk", f"{simulated['risk']}%", f"{delta:+.0f} pts")
    b.metric("Status", simulated["status"])
    c.metric("RUL", f"{simulated['rul_hours']} h")
    d.metric("Health", f"{simulated['health_score']}/100")
    st.info(f"**{base_id}:** {base.status} / {base.risk}% → {simulated['status']} / {simulated['risk']}%. The simulator never sends a machine command.")

    x, y, z = st.columns(3)
    x.metric("Preventive cost", f"₹{impact['preventive_cost']:,}")
    y.metric("Modeled failure cost", f"₹{impact['failure_cost']:,}")
    z.metric("Potential saving", f"₹{impact['potential_saving']:,}")

    st.markdown("### 🎬 Failure Scenario Mode")
    if st.button("▶ Run Failure Scenario", use_container_width=True):
        st.session_state.scenario_running = True
    if st.session_state.scenario_running:
        steps = scenario_steps(base.to_dict(), 6)
        live_df = pd.DataFrame(steps)
        st.plotly_chart(px.line(live_df, x="step", y="risk", markers=True,
                                title=f"{base_id} · Healthy → Critical progression"), use_container_width=True)
        for item in steps:
            icon = "🟢" if item["status"] == "HEALTHY" else "🟡" if item["status"] == "WATCH" else "🟠" if item["status"] == "WARNING" else "🔴"
            st.markdown(f"**Step {item['step']} · {icon} {item['status']}** — Risk {item['risk']}% · RUL {item['rul_hours']} h · Temp {item['temp']}°C · Vibration {item['vibration']}")
        final = steps[-1]
        if final["risk"] >= 51:
            st.error(f"🤖 Guardian reaction: **{final['status']}** — {final['recommendation']}")

    st.markdown("### 📉 Automated Stress Sweep")
    sweep = scenario_sweep(base)
    sweep_rows = []
    for _, sr in sweep.iterrows():
        p = predict_machine(sr.temp, sr.vibration, sr.pressure)
        sweep_rows.append({**sr.to_dict(), "risk": p["risk"], "status": p["status"], "rul_hours": p["rul_hours"]})
    sdf = pd.DataFrame(sweep_rows)
    st.plotly_chart(px.line(sdf, x="factor", y="risk", markers=True, title="Risk under progressive sensor stress"), use_container_width=True)

# ---------- Maintenance ----------
elif section == "🛠️ Maintenance & Work Orders":
    st.subheader("🛠️ Maintenance Planner & AI Work Orders")
    plan = df.sort_values("priority_score", ascending=False).copy()
    plan["Priority"] = ["IMMEDIATE" if x >= 76 else "URGENT" if x >= 51 else "SCHEDULE" if x >= 26 else "MONITOR" for x in plan.risk]

    st.markdown("### Priority Queue")
    compact = plan[["machine_id", "Priority", "risk", "rul_hours", "health_score", "root_cause", "recommendation"]].copy()
    compact.columns = ["Machine", "Priority", "Risk %", "RUL h", "Health", "Reason", "Action"]
    st.dataframe(compact, use_container_width=True, hide_index=True, height=300)

    total_pre = sum(r["costs"]["preventive_cost"] for r in results)
    total_loss = sum(r["costs"]["failure_cost"] for r in results)
    st.metric("Potential fleet loss avoided", f"₹{max(0, total_loss - total_pre):,.0f}")
    st.caption("Business values are modeled demo estimates, not guaranteed savings.")

    st.divider()
    wo_machine = st.selectbox("Generate work order for", df.machine_id.tolist(), key="wo_machine")
    wm = df[df.machine_id == wo_machine].iloc[0]
    decision = maintenance_decision(wm.to_dict(), trend_direction(history_frame(wo_machine)))
    wo = create_work_order(wm.to_dict(), decision)

    a, b, c, d = st.columns(4)
    a.metric("Priority", wo["priority"])
    b.metric("Risk", f"{wo['risk_pct']}%")
    c.metric("RUL", f"{wo['rul_hours']} h")
    d.metric("Approval", "REQUIRED")

    st.markdown(f'<div class="card"><h3>🧾 {wo["work_order_id"]} · {wo["machine_id"]}</h3>'
                f'<p><b>Issue:</b> {wo["reason"]}</p>'
                f'<p><b>Recommended action:</b> {wo["recommended_action"]}</p>'
                f'<p><b>Agent verdict:</b> {wo["agent_action"]}</p></div>', unsafe_allow_html=True)

    st.markdown("#### 👷 Technician Checklist")
    for i, item in enumerate(wo["checklist"]):
        st.checkbox(item, key=f"wo_check_{wo_machine}_{i}")

    impact = maintenance_impact(wm.to_dict())
    x, y, z = st.columns(3)
    x.metric("Preventive cost", f"₹{impact['preventive_cost']:,}")
    y.metric("Modeled failure cost", f"₹{impact['failure_cost']:,}")
    z.metric("Potential saving", f"₹{impact['potential_saving']:,}")

    with st.expander("🔧 Technical Work Order JSON"):
        st.json(wo)
    st.download_button("📄 Download Draft Work Order", json.dumps(wo, indent=2, default=str),
                       f"{wo_machine}_work_order.json", "application/json")

    st.divider()
    st.markdown("### 🗂️ Maintenance History")
    if MAINT_PATH.exists():
        st.dataframe(pd.read_csv(MAINT_PATH).tail(20), use_container_width=True, hide_index=True)
    mc = st.columns(4)
    mm = mc[0].selectbox("Machine", df.machine_id.tolist(), key="maint_machine")
    issue = mc[1].text_input("Issue", "Bearing inspection")
    action = mc[2].text_input("Action", "Inspect and lubricate")
    cost = mc[3].number_input("Cost ₹", 0.0, 1_000_000.0, 15_000.0)
    if st.button("💾 Save Maintenance Record"):
        rec = {"machine_id": mm, "date": datetime.now().strftime("%Y-%m-%d"), "issue": issue,
               "action": action, "technician": "Maintenance Team", "cost": cost, "status": "PLANNED"}
        old = pd.read_csv(MAINT_PATH) if MAINT_PATH.exists() else pd.DataFrame()
        pd.concat([old, pd.DataFrame([rec])], ignore_index=True).to_csv(MAINT_PATH, index=False)
        st.success("Maintenance record saved.")

# ---------- Data / IoT / Reports ----------
elif section == "📡 Data, IoT & Reports":
    st.subheader("📡 Data, IoT, CSV, Model & Reports")

    tabs = st.tabs(["📂 CSV", "📊 Reports", "🧠 Model", "🚨 Alerts", "🔌 IoT/API"])

    with tabs[0]:
        st.markdown("### CSV Analyzer → AI Review → Fleet")
        template = pd.DataFrame([{
            "machine_id": "M9", "machine_type": "Industrial Motor", "temp": 72.5,
            "vibration": 0.45, "pressure": 32.1, "timestamp": "2026-09-06 10:00"
        }])
        st.download_button("⬇️ Download CSV Template", template.to_csv(index=False), "machine_template.csv", "text/csv")
        upload = st.file_uploader("Upload machine telemetry CSV", type=["csv"], key="machine_csv")
        if upload:
            try:
                cdf = load_csv(upload)
                snapshot = latest_snapshot(cdf)
                st.success(f"{len(cdf)} telemetry row(s) validated · {len(snapshot)} machine(s) ready for AI analysis.")
                if len(cdf) != len(snapshot):
                    st.info("📈 History CSV detected. Repeated machine IDs are allowed; latest telemetry becomes the current snapshot.")
                preview = build_results(snapshot.to_dict("records"))
                preview_df = pd.DataFrame(preview)[["machine_id", "machine_type", "temp", "vibration", "pressure", "risk", "status", "rul_hours", "health_score", "root_cause", "recommendation"]]
                preview_df.columns = ["Machine", "Type", "Temp °C", "Vibration", "Pressure", "Risk %", "Status", "RUL h", "Health", "AI Diagnosis", "Action"]
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                if "timestamp" in cdf.columns and len(cdf) > len(snapshot):
                    hm = st.selectbox("Uploaded history machine", snapshot.machine_id.tolist(), key="csv_history_machine")
                    h = cdf[cdf.machine_id == hm].copy().sort_values("timestamp")
                    h["timestamp"] = pd.to_datetime(h["timestamp"], errors="coerce")
                    st.plotly_chart(trend_chart(h, "temp", f"{hm} · Uploaded Temperature History", "°C"), use_container_width=True)
                    cols = st.columns(2)
                    cols[0].plotly_chart(trend_chart(h, "vibration", f"{hm} · Vibration History"), use_container_width=True)
                    cols[1].plotly_chart(trend_chart(h, "pressure", f"{hm} · Pressure History", "bar"), use_container_width=True)

                selected_csv = st.multiselect("Approve machines to add to fleet", snapshot.machine_id.tolist(), default=snapshot.machine_id.tolist())
                if st.button("🚀 Approve & Add Selected Machines"):
                    approved = [r for r in snapshot.to_dict("records") if r["machine_id"] in selected_csv]
                    added = add_records(approved)
                    st.success(f"Added {added} new machine(s) to fleet.")
                    st.rerun()
            except Exception as exc:
                st.error(f"CSV validation failed: {exc}")

        st.divider()
        st.markdown("### Manual Machine Lab")
        a, b, c, d = st.columns(4)
        mid = a.text_input("Machine ID", "M9")
        mtype = b.text_input("Machine Type", "Industrial Motor")
        temp = c.number_input("Temperature °C", 30.0, 130.0, 72.0)
        vib = d.number_input("Vibration", 0.0, 3.0, 0.45)
        pressure = st.number_input("Pressure bar", 0.0, 70.0, 32.0)
        if st.button("🔎 Analyze New Machine"):
            st.session_state.analysis_result = build_results([{
                "machine_id": mid.upper(), "machine_type": mtype, "temp": temp,
                "vibration": vib, "pressure": pressure
            }])[0]
        if st.session_state.analysis_result:
            ar = st.session_state.analysis_result
            st.markdown(f"### {ar['machine_id']} · {ar['status']}")
            a, b, c = st.columns(3)
            a.metric("Risk", f"{ar['risk']}%")
            b.metric("RUL", f"{ar['rul_hours']} h")
            c.metric("Health", f"{ar['health_score']}/100")
            st.info(ar["root_cause"])
            st.warning(ar["recommendation"] if ar["risk"] >= 51 else ar["recommendation"])
            if st.button("✅ Approve & Add to Fleet", key="approve_manual"):
                add_records([ar])
                st.success("Machine added to fleet.")
                st.session_state.analysis_result = None
                st.rerun()

        if role in ["Plant Manager", "Maintenance Engineer"] and st.session_state.machines:
            st.divider()
            rem = st.selectbox("Remove machine", [m["machine_id"] for m in st.session_state.machines], key="remove_machine")
            if st.button("🗑️ Remove Selected Machine"):
                st.session_state.machines = remove_machine(st.session_state.machines, rem)
                persist_fleet()
                st.rerun()

    with tabs[1]:
        st.markdown("### 📄 AI Reports")
        report_machine = st.selectbox("Generate report for", df.machine_id.tolist(), key="report_machine")
        rr = df[df.machine_id == report_machine].iloc[0].to_dict()
        report = report_markdown(rr, trend_direction(history_frame(report_machine)))
        st.download_button("📄 Download AI Health Report", report, f"{report_machine}_AI_Report.md", "text/markdown")
        st.download_button("📊 Export Fleet AI Report", df.to_csv(index=False), "fleet_ai_report.csv", "text/csv")
        eb = executive_brief(results)
        st.markdown(f'<div class="card"><h3>📌 {eb["headline"]}</h3>'
                    f'<p><b>Top asset:</b> {eb["top_asset"]} · <b>Risk:</b> {eb["top_risk"]}%</p></div>', unsafe_allow_html=True)
        for act in eb["actions"]:
            st.markdown(f"- {act}")
        st.download_button("⬇️ Export Executive Brief", json.dumps(eb, indent=2, default=str), "executive_ai_brief.json", "application/json")

    with tabs[2]:
        st.markdown("### 🧠 Model, Explainability & Self-Learning")
        meta = model_metadata()
        cols = st.columns(5)
        cols[0].metric("Model", meta.get("model", "Random Forest"))
        cols[1].metric("Accuracy", f"{meta.get('accuracy', 0)*100:.1f}%")
        cols[2].metric("Precision", f"{meta.get('precision', 0)*100:.1f}%")
        cols[3].metric("Recall", f"{meta.get('recall', 0)*100:.1f}%")
        cols[4].metric("F1", f"{meta.get('f1', 0)*100:.1f}%")
        with st.expander("🔧 Technical model details"):
            x, y, z = st.columns(3)
            x.metric("Training records", meta.get("training_records", "—"))
            y.metric("Validation records", meta.get("validation_records", "—"))
            z.metric("Features", ", ".join(meta.get("features", [])))
            st.caption(f"Trained at: {meta.get('trained_at', '—')}")
        if st.button("🧬 Retrain / Self-Learn Model"):
            m = retrain()
            st.success(f"Model retrained. Accuracy: {m.get('accuracy', 0):.2%}")
            st.rerun()
        st.caption("Training data is synthetic/demo telemetry. Production deployment should use labeled historical failures and maintenance outcomes.")

    with tabs[3]:
        st.markdown("### 🚨 Alert Center")
        sev_filter = st.multiselect("Severity", ["CRITICAL", "WARNING", "WATCH"], default=["CRITICAL", "WARNING", "WATCH"])
        alerts = []
        for r in results:
            sev = "CRITICAL" if r["risk"] >= 76 else "WARNING" if r["risk"] >= 51 else "WATCH" if r["risk"] >= 26 else None
            if sev and sev in sev_filter:
                alerts.append({"Machine": r["machine_id"], "Severity": sev, "Risk %": r["risk"], "RUL h": r["rul_hours"], "Message": r["root_cause"]})
        if alerts:
            st.dataframe(pd.DataFrame(alerts), use_container_width=True, hide_index=True)
        else:
            st.success("No active alerts.")

    with tabs[4]:
        st.markdown("### 🔌 IoT & Backend")
        if source == "Live IoT/API":
            st.warning("🟡 Live mode selected. The dashboard will not pretend simulated readings are real device data.")
        st.code("python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", language="bash")
        st.markdown("**Telemetry endpoint:** `/api/v1/telemetry/{machine_id}`  \n**Bulk endpoint:** `/api/v1/telemetry/bulk`  \n**Fleet analysis:** `/api/v1/fleet/analysis`  \n**AI chat:** `/api/v1/chat`")
        st.info("ESP32/PLC/IoT gateways can POST telemetry to the backend. AI recommendations remain advisory; machine safety interlocks and authorized PLC controls remain authoritative.")
        st.markdown("#### Connection status")
        if source == "Live IoT/API":
            st.write("🟡 Waiting for external device telemetry")
        else:
            st.write("🟢 Demo data stream active")

st.sidebar.divider()
st.sidebar.caption("AI Industrial Guardian · Clean Edition · AI recommends; authorized humans/PLC controls execute.")
