from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "machines.json"

def load_machines(defaults):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        save_machines(defaults)
        return [dict(x) for x in defaults]
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return [dict(x) for x in data]
    except Exception:
        pass
    save_machines(defaults)
    return [dict(x) for x in defaults]

def save_machines(machines):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(machines, indent=2), encoding="utf-8")

def add_machine(machines, machine_id, temp, vibration, pressure, machine_type="Industrial Machine"):
    machine_id = machine_id.strip().upper()
    if not machine_id:
        raise ValueError("Machine ID is required")
    if any(m.get("machine_id", "").upper() == machine_id for m in machines):
        raise ValueError(f"Machine {machine_id} already exists")
    item = {
        "machine_id": machine_id,
        "temp": round(float(temp), 1),
        "vibration": round(float(vibration), 2),
        "pressure": round(float(pressure), 1),
        "machine_type": machine_type,
    }
    machines = [dict(m) for m in machines] + [item]
    save_machines(machines)
    return machines

def remove_machine(machines, machine_id):
    remaining = [dict(m) for m in machines if m.get("machine_id") != machine_id]
    if not remaining:
        raise ValueError("At least one machine must remain in the fleet")
    save_machines(remaining)
    return remaining
