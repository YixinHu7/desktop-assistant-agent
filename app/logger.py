import json
import os
from datetime import datetime

TRACE_PATH = "data/traces.jsonl"

def log_event(event_type: str, payload: dict):
    os.makedirs("data", exist_ok=True)

    row = {
        "ts": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "payload": payload
    }

    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")