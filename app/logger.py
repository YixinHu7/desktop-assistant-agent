import json
import os
from datetime import datetime
from app.config import config

def log_event(event_type: str, payload: dict):
    os.makedirs(os.path.dirname(config.trace_path), exist_ok=True)

    row = {
        "ts": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "payload": payload
    }

    with open(config.trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")