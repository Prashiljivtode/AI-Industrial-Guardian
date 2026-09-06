"""Sensor-fusion health score and model/rule agreement indicators."""
def fusion_score(result):
    risk=float(result.get("risk",0)); anomaly=float(result.get("anomaly_score",0)); severity=float(result.get("sensor_severity",0))
    score=round(0.55*risk+0.25*anomaly+0.20*severity,1)
    agreement=round(100-abs(risk-anomaly)*0.65-abs(risk-severity)*0.35,1)
    return max(0,min(100,score)),max(0,min(100,agreement))
