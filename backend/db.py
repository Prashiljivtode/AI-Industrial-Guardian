from pathlib import Path
import sqlite3
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "industrial_guardian.db"

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS machines (
            machine_id TEXT PRIMARY KEY, machine_type TEXT NOT NULL,
            temp REAL NOT NULL, vibration REAL NOT NULL, pressure REAL NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
            temp REAL NOT NULL, vibration REAL NOT NULL, pressure REAL NOT NULL,
            risk REAL, health_score REAL, rul_hours REAL, status TEXT,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
            issue TEXT NOT NULL, action TEXT NOT NULL, team TEXT NOT NULL,
            cost REAL NOT NULL, status TEXT NOT NULL, timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL,
            severity TEXT NOT NULL, message TEXT NOT NULL, acknowledged INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );
        """)

def now(): return datetime.now(timezone.utc).isoformat()
