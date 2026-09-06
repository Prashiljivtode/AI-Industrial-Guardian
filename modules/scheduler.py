
def priority_score(m):
    urgency = max(0, 100 - min(100, m["rul_hours"] / 2.4))
    sensor = m.get("sensor_severity", 0) * 100
    return round(0.55*m["risk"] + 0.30*urgency + 0.15*sensor, 1)


def generate_schedule(machines):
    order = {"IMMEDIATE": 0, "URGENT": 1, "SCHEDULE": 2, "MONITOR": 3}
    rows = []
    for m in machines:
        score = priority_score(m)
        rows.append({
            "Machine": m["machine_id"],
            "Priority": m["priority"],
            "Priority Score": score,
            "Risk": f'{m["risk"]}%',
            "RUL": f'{m["rul_hours"]} hrs',
            "Health": f'{m["health_score"]}/100',
            "Action": m["recommendation"],
            "Reason": m["root_cause"],
        })
    return sorted(rows, key=lambda x: (order[x["Priority"]], -x["Priority Score"]))
