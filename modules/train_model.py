
from pathlib import Path
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "sensor_data.csv"
MODEL_PATH = ROOT / "models" / "failure_model.pkl"
META_PATH = ROOT / "models" / "model_metadata.json"
FEATURES = ["temp", "vibration", "pressure"]


def build_dataset(n=2400, seed=42):
    """Create deterministic synthetic industrial sensor data with causal-ish rules."""
    rng = np.random.default_rng(seed)
    temp = rng.normal(72, 13, n).clip(40, 112)
    vibration = rng.normal(0.58, 0.34, n).clip(0.03, 2.2)
    pressure = rng.normal(35, 6.5, n).clip(18, 56)

    # Smooth risk signal; labels are sampled from it rather than purely random.
    z = (
        -4.0
        + 0.075 * (temp - 70)
        + 2.8 * (vibration - 0.45)
        + 0.055 * (pressure - 34)
        + 0.045 * np.maximum(temp - 88, 0) * np.maximum(vibration - 0.8, 0)
        + 0.9 * ((temp > 92) & (vibration > 1.0))
        + 0.7 * ((vibration > 1.15) & (pressure > 43))
    )
    failure_prob = 1 / (1 + np.exp(-z))
    failure = (rng.random(n) < failure_prob).astype(int)

    return pd.DataFrame({
        "machine_id": [f"SIM{i+1:04d}" for i in range(n)],
        "temp": temp.round(2),
        "vibration": vibration.round(3),
        "pressure": pressure.round(2),
        "failure": failure,
    })


def train_model():
    data = build_dataset()
    DATA_PATH.parent.mkdir(exist_ok=True)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    data.to_csv(DATA_PATH, index=False)

    X = data[FEATURES]
    y = data["failure"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    meta = {
        "model": "Random Forest",
        "features": FEATURES,
        "training_records": int(len(data)),
        "validation_records": int(len(X_test)),
        "accuracy": float(acc),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "trained_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    joblib.dump(model, MODEL_PATH)
    META_PATH.write_text(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    m = train_model()
    print(f"Model trained. Validation accuracy: {m['accuracy']:.2%}")
