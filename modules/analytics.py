import numpy as np

def anomaly_score(temp, vibration, pressure):
    # Demo operating envelopes; higher means more abnormal.
    t = abs(float(temp) - 68.0) / 35.0
    v = abs(float(vibration) - 0.35) / 1.15
    p = abs(float(pressure) - 32.0) / 20.0
    return int(np.clip(round(100 * (0.45*t + 0.4*v + 0.15*p)), 0, 100))

def health_band(score):
    if score >= 75: return "NORMAL"
    if score >= 50: return "ELEVATED"
    if score >= 25: return "ANOMALOUS"
    return "SEVERE ANOMALY"

def fleet_insight(df):
    if df.empty: return "No telemetry available."
    top = df.sort_values("risk", ascending=False).iloc[0]
    critical = int((df.risk >= 76).sum())
    if critical:
        return f"{critical} critical machine(s) detected. {top.machine_id} is currently the highest-risk asset at {int(top.risk)}%."
    if top.risk >= 51:
        return f"The fleet is stable overall, but {top.machine_id} needs attention at {int(top.risk)}% risk."
    return "Fleet health is currently stable with no machine above the warning threshold."
