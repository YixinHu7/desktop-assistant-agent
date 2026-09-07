import json
import os
from copy import deepcopy
from typing import Any

from app.config import config

DEFAULT_MEMORY_DATA = {
    "facts": {},
    "preferences": {},
    "history": [],
}


class MemoryStore:
    def __init__(
        self,
        memory_path: str | None = None,
        max_history_messages: int | None = None,
    ):
        self.memory_path = memory_path or config.memory_path
        self.max_history_messages = (
            max_history_messages
            if max_history_messages is not None
            else config.max_history_messages
        )

        memory_dir = os.path.dirname(self.memory_path)

        if memory_dir:
            os.makedirs(memory_dir, exist_ok=True)

        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not os.path.exists(self.memory_path):
            return self._default_data()

        try:
            with open(self.memory_path, "r", encoding="utf-8") as handle:
                raw_data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return self._default_data()

        return self._normalize_data(raw_data)

    def save(self) -> None:
        memory_dir = os.path.dirname(self.memory_path)

        if memory_dir:
            os.makedirs(memory_dir, exist_ok=True)

        with open(self.memory_path, "w", encoding="utf-8") as handle:
            json.dump(
                self.data,
                handle,
                indent=2,
                ensure_ascii=False,
            )

    def set_fact(self, key: str, value: Any) -> None:
        normalized_key = self._normalize_key(key)

        if not normalized_key:
            return

        self.data["facts"][normalized_key] = value
        self.save()

    def set_preference(self, key: str, value: Any) -> None:
        normalized_key = self._normalize_key(key)

        if not normalized_key:
            return

        self.data["preferences"][normalized_key] = value
        self.save()

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.data["facts"].get(
            self._normalize_key(key),
            default,
        )

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.data["preferences"].get(
            self._normalize_key(key),
            default,
        )

    def add_history(self, role: str, content: str) -> None:
        if not isinstance(self.data.get("history"), list):
            self.data["history"] = []

        self.data["history"].append(
            {
                "role": str(role),
                "content": str(content),
            }
        )
        self.data["history"] = self.data["history"][-self.max_history_messages :]
        self.save()

    def get_recent_history(self) -> list[dict[str, str]]:
        history = self.data.get("history", [])

        if not isinstance(history, list):
            return []

        return history[-6:]

    def get_context_text(self) -> str:
        facts = json.dumps(
            self.data.get("facts", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
        preferences = json.dumps(
            self.data.get("preferences", {}),
            ensure_ascii=False,
            sort_keys=True,
        )

        return f"Facts: {facts}\nPreferences: {preferences}"

    @staticmethod
    def _default_data() -> dict[str, Any]:
        return deepcopy(DEFAULT_MEMORY_DATA)

    @classmethod
    def _normalize_data(cls, raw_data: Any) -> dict[str, Any]:
        data = cls._default_data()

        if not isinstance(raw_data, dict):
            return data

        facts = raw_data.get("facts", {})
        preferences = raw_data.get("preferences", {})
        history = raw_data.get("history", [])

        data["facts"] = facts if isinstance(facts, dict) else {}
        data["preferences"] = preferences if isinstance(preferences, dict) else {}
        data["history"] = history if isinstance(history, list) else []

        return data

    @staticmethod
    def _normalize_key(key: str) -> str:
        return str(key).strip()
