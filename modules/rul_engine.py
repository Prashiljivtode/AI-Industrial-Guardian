
def rul_label(hours):
    if hours > 168:
        return "LOW URGENCY"
    if hours >= 72:
        return "MONITOR"
    if hours >= 24:
        return "PLAN MAINTENANCE"
    return "URGENT"
