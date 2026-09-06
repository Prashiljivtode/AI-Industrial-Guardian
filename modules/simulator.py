
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "data" / "sensor_history.csv"

BASE_MACHINES = [
    {"machine_id":"M1", "temp":90.0, "vibration":1.20, "pressure":45.0},
    {"machine_id":"M2", "temp":61.0, "vibration":0.22, "pressure":30.0},
    {"machine_id":"M3", "temp":86.0, "vibration":0.95, "pressure":42.0},
    {"machine_id":"M4", "temp":55.0, "vibration":0.15, "pressure":27.0},
    {"machine_id":"M5", "temp":96.0, "vibration":1.30, "pressure":47.0},
    {"machine_id":"M6", "temp":68.0, "vibration":0.38, "pressure":31.0},
    {"machine_id":"M7", "temp":78.0, "vibration":0.65, "pressure":37.0},
    {"machine_id":"M8", "temp":58.0, "vibration":0.20, "pressure":29.0},
]


def next_snapshot(machines, seed=None, critical_event=False):
    rng = np.random.default_rng(seed)
    out = []
    for m in machines:
        temp = m["temp"] + rng.normal(0, 1.3)
        vib = m["vibration"] + rng.normal(0, 0.045)
        pressure = m["pressure"] + rng.normal(0, 0.7)
        if critical_event and m["machine_id"] == "M5":
            temp += 5.5
            vib += 0.12
            pressure += 1.5
        out.append({
            **m,
            "temp": round(float(np.clip(temp, 35, 115)), 1),
            "vibration": round(float(np.clip(vib, 0.02, 2.3)), 2),
            "pressure": round(float(np.clip(pressure, 15, 58)), 1),
        })
    return out


def append_history(results):
    HISTORY_PATH.parent.mkdir(exist_ok=True)
    rows = []
    ts = pd.Timestamp.now().floor("min")
    for m in results:
        rows.append({
            "timestamp": ts,
            "machine_id": m["machine_id"],
            "temp": m["temp"],
            "vibration": m["vibration"],
            "pressure": m["pressure"],
            "risk": m["risk"],
            "health_score": m["health_score"],
        })
    new = pd.DataFrame(rows)
    if HISTORY_PATH.exists():
        old = pd.read_csv(HISTORY_PATH)
        df = pd.concat([old, new], ignore_index=True).tail(2000)
    else:
        df = new
    df.to_csv(HISTORY_PATH, index=False)


def load_history(machine_id, points=48):
    if not HISTORY_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(HISTORY_PATH, parse_dates=["timestamp"])
    df = df[df.machine_id == machine_id].tail(points)
    return df
