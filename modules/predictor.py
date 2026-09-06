
from pathlib import Path
import json
import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "failure_model.pkl"
META_PATH = ROOT / "models" / "model_metadata.json"
FEATURES = ["temp", "vibration", "pressure"]


def ensure_model():
    if not MODEL_PATH.exists():
        from modules.train_model import train_model
        train_model()
    return joblib.load(MODEL_PATH)


def _risk_category(risk):
    if risk >= 76:
        return "CRITICAL", "IMMEDIATE"
    if risk >= 51:
        return "WARNING", "URGENT"
    if risk >= 26:
        return "WATCH", "SCHEDULE"
    return "HEALTHY", "MONITOR"


def _rul_hours(risk, temp, vibration, pressure):
    severity = (
        0.50 * np.clip((temp - 70) / 40, 0, 1)
        + 0.35 * np.clip((vibration - 0.45) / 1.4, 0, 1)
        + 0.15 * np.clip((pressure - 34) / 22, 0, 1)
    )
    base = 240 * (1 - risk / 100)
    return max(8, int(round(base * (1 - 0.38 * severity))))


def predict_machine(temp, vibration, pressure):
    model = ensure_model()
    import pandas as pd
    x = pd.DataFrame([[float(temp), float(vibration), float(pressure)]], columns=FEATURES)
    probability = float(model.predict_proba(x)[0][1])
    risk = int(np.clip(round(probability * 100), 0, 100))
    status, priority = _risk_category(risk)
    rul = _rul_hours(risk, float(temp), float(vibration), float(pressure))

    if status == "CRITICAL":
        recommendation = "Immediate inspection; isolate machine if operating limits are exceeded"
    elif status == "WARNING":
        recommendation = "Schedule preventive maintenance and inspect bearings/cooling"
    elif status == "WATCH":
        recommendation = "Continue monitoring and review the sensor trend"
    else:
        recommendation = "No immediate action required; keep routine inspection"

    health = int(np.clip(100 - risk, 0, 100))
    return {
        "failure_probability": probability,
        "risk": risk,
        "status": status,
        "priority": priority,
        "rul_hours": rul,
        "health_score": health,
        "recommendation": recommendation,
    }


def predict_failure(temp, vibration, pressure):
    return int(predict_machine(temp, vibration, pressure)["risk"] >= 51)


def model_metadata():
    if not META_PATH.exists():
        from modules.train_model import train_model
        train_model()
    try:
        return json.loads(META_PATH.read_text())
    except Exception:
        return {}
