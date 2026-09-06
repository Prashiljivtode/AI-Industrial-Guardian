import pandas as pd

REQUIRED = ["machine_id", "temp", "vibration", "pressure"]
ALIASES = {
    "temperature": "temp", "temperature_c": "temp", "temp_c": "temp",
    "machine": "machine_id", "id": "machine_id",
    "vibration_mm_s": "vibration", "vibration_rms": "vibration",
    "pressure_bar": "pressure", "time": "timestamp", "datetime": "timestamp"
}

def load_csv(file, allow_history=True):
    """Validate a machine snapshot or telemetry-history CSV.

    Required: machine_id, temp, vibration, pressure.
    Optional: machine_type, timestamp. Duplicate machine IDs are allowed when
    timestamp/history data is supplied; the latest row per machine becomes the
    fleet snapshot.
    """
    df = file.copy() if isinstance(file, pd.DataFrame) else pd.read_csv(file)
    df = df.rename(columns={c: ALIASES.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns})
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    df["machine_id"] = df["machine_id"].astype(str).str.strip().str.upper()
    for c in REQUIRED[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[REQUIRED[1:]].isna().any().any():
        raise ValueError("Temperature, vibration and pressure must be numeric with no blanks.")
    if not df["machine_id"].str.match(r"^[A-Z0-9_-]+$").all():
        raise ValueError("Machine IDs may contain only letters, numbers, _ and -.")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    elif allow_history and df["machine_id"].duplicated().any():
        # Repeated IDs are treated as telemetry history even without timestamps.
        df["timestamp"] = pd.RangeIndex(len(df))
    return df

def latest_snapshot(df):
    """Return one latest telemetry row per machine for fleet analysis."""
    work = df.copy()
    if "timestamp" in work.columns:
        work = work.sort_values("timestamp")
    return work.groupby("machine_id", as_index=False).tail(1).reset_index(drop=True)
