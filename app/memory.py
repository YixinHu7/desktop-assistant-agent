import json
import os
from app.config import config


class MemoryStore:
    def __init__(self, memory_path: str = config.memory_path):
        self.memory_path = memory_path
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "facts": {},
            "preferences": {},
            "history": []
        }
    
    def save(self):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        
    def add_history(self, role: str, content: str):
        self.data["history"].append({"role": role, "content": content})
        self.data["history"] = self.data["history"][-config.max_history_messages:]
        self.save()
    
    def get_recent_history(self):
        return self.data["history"][-6:]
    
    def get_context_text(self) -> str:
        facts = json.dumps(self.data["facts"], ensure_ascii=False)
        prefs = json.dumps(self.data["preferences"], ensure_ascii=False)
        return f"Facts: {facts}\nPreferences: {prefs}"