# AI Industrial Guardian — BEST V8

AI-powered predictive maintenance and industrial intelligence demo.

## V8 highlights
- Explainable ML risk + RUL + anomaly + sensor-fusion supervisor
- AI Maintenance Copilot with machine-specific explanations and comparisons
- Progressive failure scenario mode and automated stress sweep
- Autonomous maintenance decision and structured work-order generation
- Business impact / preventive-vs-breakdown ROI view
- Executive AI briefing generated locally from fleet evidence
- Digital Twin, machine passport, CSV onboarding, simulation and IoT/FastAPI integration
- Demo-safe guardrails: AI recommends; authorized humans/PLC safety systems remain authoritative

## Run
```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Backend:
```bat
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Telemetry is synthetic unless a real IoT/PLC/ESP32 source is connected.
