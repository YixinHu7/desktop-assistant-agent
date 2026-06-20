import unittest

from app.evaluation.models import EvalCase
from app.evaluation.results import EvalCheckStatus
from app.evaluation.scorers import score_eval_case


def build_case(
    case_id: str,
    expected: dict,
) -> EvalCase:
    return EvalCase.model_validate({
        "id": case_id,
        "suite": "tools",
        "description": "Synthetic scorer test.",
        "input": "Synthetic user input.",
        "expected": expected,
    })


class DeterministicScorerTests(unittest.TestCase):
    def test_passing_tool_case(self):
        case = build_case(
            case_id="test_tool_pass",
            expected={
                "route": "tool",
                "required_tools": [
                    "get_project_tree"
                ],
                "forbidden_tools": [
                    "open_app"
                ],
                "tool_arguments": [
                    {
                        "tool": "get_project_tree",
                        "arguments": {
                            "path": ".",
                            "max_depth": 3,
                        },
                        "match": "exact",
                    }
                ],
                "minimum_tool_calls": 1,
                "maximum_tool_calls": 1,
            },
        )

        run_summary = {
            "route_decision": {
                "route": "tool"
            },
            "tool_calls": [
                {
                    "tool": "get_project_tree",
                    "arguments": {
                        "path": ".",
                        "max_depth": 3,
                    },
                }
            ],
        }

        result = score_eval_case(
            case,
            run_summary,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_forbidden_tool_fails(self):
        case = build_case(
            case_id="test_forbidden_tool",
            expected={
                "forbidden_tools": [
                    "open_app"
                ],
                "maximum_tool_calls": 0,
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "open_app",
                    "arguments": {
                        "app_name": "Notes"
                    },
                }
            ],
        }

        result = score_eval_case(
            case,
            run_summary,
        )

        self.assertFalse(result.passed)

        tool_check = next(
            check
            for check in result.checks
            if check.name == "tool_selection"
        )

        self.assertEqual(
            tool_check.status,
            EvalCheckStatus.FAILED,
        )

    def test_subset_argument_matching(self):
        case = build_case(
            case_id="test_subset_arguments",
            expected={
                "required_tools": [
                    "search_files"
                ],
                "tool_arguments": [
                    {
                        "tool": "search_files",
                        "arguments": {
                            "query": "ToolExecutor"
                        },
                        "match": "subset",
                    }
                ],
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "search_files",
                    "arguments": {
                        "query": "ToolExecutor",
                        "path": ".",
                        "max_results": 20,
                    },
                }
            ],
        }

        result = score_eval_case(
            case,
            run_summary,
        )

        self.assertTrue(result.passed)

    def test_executed_tool_requires_approval(self):
        case = build_case(
            case_id="test_approval_required",
            expected={
                "required_tools": [
                    "open_app"
                ],
                "approval_required_tools": [
                    "open_app"
                ],
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "open_app",
                    "arguments": {
                        "app_name": "Notes"
                    },
                }
            ],
            "approval_decisions": [],
        }

        result = score_eval_case(
            case,
            run_summary,
        )

        self.assertFalse(result.passed)

        approval_check = next(
            check
            for check in result.checks
            if check.name == "approval"
        )

        self.assertEqual(
            approval_check.status,
            EvalCheckStatus.FAILED,
        )

    def test_recovery_expectation(self):
        case = build_case(
            case_id="test_recovery",
            expected={
                "recovery_expected": True
            },
        )

        run_summary = {
            "recovery_attempts": [
                {
                    "tool": "read_file",
                    "fallback_tool": "list_files",
                }
            ]
        }

        result = score_eval_case(
            case,
            run_summary,
        )

        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()