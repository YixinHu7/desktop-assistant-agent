import unittest

from app.evaluation.completion import assess_task_completion
from app.evaluation.models import CompletionStatus, EvalCase
from app.evaluation.snapshot import RuntimeEvalSnapshot


def build_case(
    case_id: str,
    expected: dict,
) -> EvalCase:
    return EvalCase.model_validate(
        {
            "id": case_id,
            "suite": "end_to_end",
            "description": "Synthetic completion test.",
            "input": "Synthetic input.",
            "expected": expected,
        }
    )


class TaskCompletionTests(unittest.TestCase):
    def test_complete_when_required_tool_succeeds(self):
        case = build_case(
            "completion_complete",
            {
                "required_tools": ["read_file"],
                "completion_status": "complete",
            },
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "route_decision": {"route": "tool"},
                "tool_use_decision": {"should_use_tools": True},
                "tool_calls": [
                    {
                        "tool": "read_file",
                        "arguments": {"path": "main.py"},
                        "status": "completed",
                        "result": {"ok": True},
                    }
                ],
                "final_answer": "main.py is the entry point.",
            }
        )

        assessment = assess_task_completion(case, snapshot)

        self.assertEqual(
            assessment.status,
            CompletionStatus.COMPLETE,
        )

    def test_partial_when_required_tool_is_missing_after_progress(self):
        case = build_case(
            "completion_partial",
            {
                "required_tools": [
                    "get_project_tree",
                    "read_multiple_files",
                ],
                "completion_status": "partial",
            },
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "route_decision": {"route": "plan"},
                "tool_use_decision": {"should_use_tools": True},
                "tool_calls": [
                    {
                        "tool": "get_project_tree",
                        "status": "completed",
                        "result": {"ok": True},
                    }
                ],
                "final_answer": "I inspected the project tree.",
            }
        )

        assessment = assess_task_completion(case, snapshot)

        self.assertEqual(
            assessment.status,
            CompletionStatus.PARTIAL,
        )

    def test_failed_when_all_tools_fail(self):
        case = build_case(
            "completion_failed",
            {
                "required_tools": ["read_file"],
                "completion_status": "failed",
            },
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "route_decision": {"route": "tool"},
                "tool_use_decision": {"should_use_tools": True},
                "tool_calls": [
                    {
                        "tool": "read_file",
                        "status": "failed",
                        "result": {"ok": False},
                    }
                ],
                "final_answer": "I could not read the file.",
            }
        )

        assessment = assess_task_completion(case, snapshot)

        self.assertEqual(
            assessment.status,
            CompletionStatus.FAILED,
        )

    def test_blocked_when_approval_is_denied(self):
        case = build_case(
            "completion_blocked",
            {
                "completion_status": "blocked",
            },
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "route_decision": {"route": "tool"},
                "tool_calls": [
                    {
                        "tool": "open_app",
                        "status": "denied",
                        "result": {"ok": False},
                    }
                ],
                "approval_decisions": [
                    {
                        "tool": "open_app",
                        "approved": False,
                    }
                ],
                "final_answer": "The action was not approved.",
            }
        )

        assessment = assess_task_completion(case, snapshot)

        self.assertEqual(
            assessment.status,
            CompletionStatus.BLOCKED,
        )

    def test_chat_answer_is_complete(self):
        case = build_case(
            "completion_chat",
            {
                "completion_status": "complete",
            },
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "route_decision": {"route": "chat"},
                "tool_calls": [],
                "final_answer": "An AI agent can plan and take actions.",
            }
        )

        assessment = assess_task_completion(case, snapshot)

        self.assertEqual(
            assessment.status,
            CompletionStatus.COMPLETE,
        )


if __name__ == "__main__":
    unittest.main()