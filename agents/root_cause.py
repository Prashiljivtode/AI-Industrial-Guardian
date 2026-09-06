
import numpy as np

NORMALS = {"temp": (45, 85), "vibration": (0.05, 0.90), "pressure": (18, 42)}

def root_cause(temp, vibration, pressure, risk=0):
    factors = contribution_scores(temp, vibration, pressure)
    ordered = sorted(factors.items(), key=lambda x: x[1], reverse=True)
    active = [(k, v) for k, v in ordered if v > 0.08]
    if not active:
        return "Sensor values are within the normal operating range."
    labels = {
        "Temperature": "overheating / lubrication stress",
        "Vibration": "bearing or shaft wear",
        "Pressure": "pressure-system load",
    }
    return "; ".join(f"{labels[k]} ({round(v*100)}% contribution)" for k, v in active[:2]) + "."


def contribution_scores(temp, vibration, pressure):
    t = float(np.clip((temp - 75) / 35, 0, 1))
    v = float(np.clip((vibration - 0.45) / 1.45, 0, 1))
    p = float(np.clip((pressure - 35) / 21, 0, 1))
    vals = np.array([t, v, p], dtype=float)
    if vals.sum() == 0:
        return {"Temperature": 0.0, "Vibration": 0.0, "Pressure": 0.0}
    vals = vals / vals.sum()
    return dict(zip(["Temperature", "Vibration", "Pressure"], vals))
