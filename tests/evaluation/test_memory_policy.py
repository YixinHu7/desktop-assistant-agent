import unittest

from app.memory_policy import (
    MemoryDecision,
    _normalize_memory_key,
    sanitize_memory_decision,
)


class MemoryPolicyTests(unittest.TestCase):
    def test_normalizes_memory_key(self):
        self.assertEqual(
            _normalize_memory_key("Project Language"),
            "project_language",
        )
        self.assertEqual(
            _normalize_memory_key("project-language!"),
            "project_language",
        )

    def test_allows_explicit_memory_write(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key="Project Language",
                value="Python",
                reason="The user explicitly asked to remember durable project information.",
            ),
            user_input="Remember that the project language is Python.",
        )

        self.assertEqual(decision.action, "write")
        self.assertEqual(decision.key, "project_language")
        self.assertEqual(decision.value, "Python")

    def test_allows_going_forward_memory_write(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key="project_python_version",
                value="Use Python 3.12 for this project.",
                reason="The user explicitly set a durable project preference.",
            ),
            user_input="Going forward, use Python 3.12 for this project.",
        )

        self.assertEqual(decision.action, "write")
        self.assertEqual(decision.key, "project_python_version")
        self.assertEqual(
            decision.value,
            "Use Python 3.12 for this project.",
        )

    def test_allows_preference_memory_write(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key="answer_style",
                value="Prefer concise technical explanations.",
                reason="The user explicitly stated a durable answer preference.",
            ),
            user_input="From now on, prefer concise technical explanations.",
        )

        self.assertEqual(decision.action, "write")
        self.assertEqual(decision.key, "answer_style")
        self.assertEqual(
            decision.value,
            "Prefer concise technical explanations.",
        )

    def test_rejects_write_without_key(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key=None,
                value="Python",
                reason="Missing key.",
            ),
            user_input="Remember that the project language is Python.",
        )

        self.assertEqual(decision.action, "none")
        self.assertIsNone(decision.key)
        self.assertIsNone(decision.value)

    def test_rejects_write_without_value(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key="project_language",
                value="",
                reason="Missing value.",
            ),
            user_input="Remember that the project language is Python.",
        )

        self.assertEqual(decision.action, "none")
        self.assertIsNone(decision.key)
        self.assertIsNone(decision.value)

    def test_rejects_write_without_explicit_memory_intent(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="write",
                key="temporary_state",
                value="debugging today",
                reason="The model over-classified a temporary state.",
            ),
            user_input="I am debugging this today.",
        )

        self.assertEqual(decision.action, "none")
        self.assertIsNone(decision.key)
        self.assertIsNone(decision.value)

    def test_preserves_read_decision(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="read",
                key=None,
                value=None,
                reason="The user asked about stored context.",
            ),
            user_input="What project settings are stored?",
        )

        self.assertEqual(decision.action, "read")

    def test_preserves_none_decision(self):
        decision = sanitize_memory_decision(
            decision=MemoryDecision(
                action="none",
                key=None,
                value=None,
                reason="No memory action needed.",
            ),
            user_input="Explain dependency injection.",
        )

        self.assertEqual(decision.action, "none")


if __name__ == "__main__":
    unittest.main()