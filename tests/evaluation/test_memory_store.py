import json
import tempfile
import unittest
from pathlib import Path

from app.memory import MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def test_loads_default_memory_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"

            memory = MemoryStore(memory_path=str(memory_path))

            self.assertEqual(memory.data["facts"], {})
            self.assertEqual(memory.data["preferences"], {})
            self.assertEqual(memory.data["history"], [])

    def test_normalizes_malformed_memory_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"
            memory_path.write_text(
                json.dumps(
                    {
                        "facts": [],
                        "preferences": "bad",
                        "history": {},
                    }
                ),
                encoding="utf-8",
            )

            memory = MemoryStore(memory_path=str(memory_path))

            self.assertEqual(memory.data["facts"], {})
            self.assertEqual(memory.data["preferences"], {})
            self.assertEqual(memory.data["history"], [])

    def test_recovers_from_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"
            memory_path.write_text("{bad json", encoding="utf-8")

            memory = MemoryStore(memory_path=str(memory_path))

            self.assertEqual(memory.data["facts"], {})
            self.assertEqual(memory.data["preferences"], {})
            self.assertEqual(memory.data["history"], [])

    def test_set_fact_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"

            memory = MemoryStore(memory_path=str(memory_path))
            memory.set_fact("project_language", "Python")

            reloaded = MemoryStore(memory_path=str(memory_path))

            self.assertEqual(
                reloaded.get_fact("project_language"),
                "Python",
            )

    def test_set_preference_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"

            memory = MemoryStore(memory_path=str(memory_path))
            memory.set_preference("answer_style", "concise")

            reloaded = MemoryStore(memory_path=str(memory_path))

            self.assertEqual(
                reloaded.get_preference("answer_style"),
                "concise",
            )

    def test_add_history_truncates_to_max_history_messages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"

            memory = MemoryStore(
                memory_path=str(memory_path),
                max_history_messages=3,
            )

            for index in range(5):
                memory.add_history(
                    role="user",
                    content=f"message {index}",
                )

        self.assertEqual(len(memory.data["history"]), 3)
        self.assertEqual(
            [item["content"] for item in memory.data["history"]],
            ["message 2", "message 3", "message 4"],
        )

    def test_context_text_contains_facts_and_preferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"

            memory = MemoryStore(memory_path=str(memory_path))
            memory.set_fact("project_language", "Python")
            memory.set_preference("answer_style", "concise")

            context = memory.get_context_text()

            self.assertIn("Facts:", context)
            self.assertIn("Preferences:", context)
            self.assertIn("project_language", context)
            self.assertIn("Python", context)
            self.assertIn("answer_style", context)
            self.assertIn("concise", context)


if __name__ == "__main__":
    unittest.main()