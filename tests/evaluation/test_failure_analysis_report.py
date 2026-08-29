import unittest
from datetime import datetime, timezone

from app.evaluation.failure_analysis import render_failure_report
from app.evaluation.results import (
    EvalCaseRunResult,
    EvalCheckResult,
    EvalCheckStatus,
    EvalRunReport,
)


class FailureAnalysisReportTests(unittest.TestCase):
    def test_failure_report_includes_completion_debug_signals(self):
        report = EvalRunReport(
            run_id="eval-test",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            requested_suite="skills",
            total_cases=1,
            passed_cases=0,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.0,
            average_score=0.67,
            results=[
                EvalCaseRunResult(
                    case_id="skill_repo_review_001",
                    suite="skills",
                    description="Repository analysis should select the repo review skill.",
                    source_path="evals/cases/skills.jsonl",
                    line_number=1,
                    passed=False,
                    score=0.67,
                    duration_ms=1000,
                    final_answer=(
                        "This repository is a desktop assistant runtime with "
                        "routing, planning, tool execution, and evaluation."
                    ),
                    checks=[
                        EvalCheckResult(
                            name="task_completion",
                            status=EvalCheckStatus.FAILED,
                            score=0.0,
                            message=(
                                "Expected completion status 'complete', "
                                "but observed 'partial'."
                            ),
                            details={
                                "expected": "complete",
                                "actual": "partial",
                                "reason": (
                                    "Execution completed some work, but the "
                                    "reviewer reported remaining steps."
                                ),
                                "signals": {
                                    "actual_tools": ["get_project_tree"],
                                    "missing_required_tools": [],
                                    "used_forbidden_tools": [],
                                    "successful_tool_calls": 1,
                                    "failed_tool_calls": 0,
                                    "policy_error_tools": [],
                                    "denied_tool_calls": 0,
                                    "denied_approvals": 0,
                                    "remaining_steps": [
                                        "Read important files using read_multiple_files."
                                    ],
                                    "route": "plan",
                                    "tool_policy_should_use_tools": True,
                                    "has_final_answer": True,
                                },
                            },
                        )
                    ],
                    run_summary={
                        "tool_calls": [
                            {
                                "tool": "get_project_tree",
                                "kind": "primary",
                                "status": "completed",
                                "ok": True,
                                "source": "local",
                                "arguments": {
                                    "path": ".",
                                    "max_depth": 3,
                                },
                                "result": {
                                    "ok": True,
                                    "error": None,
                                },
                            }
                        ]
                    },
                )
            ],
        )

        markdown = render_failure_report(report, source_path="evals/results/test.json")

        self.assertIn("Final answer excerpt", markdown)
        self.assertIn("Tool call summary", markdown)
        self.assertIn("Completion signals", markdown)
        self.assertIn("get_project_tree", markdown)
        self.assertIn("Read important files using read_multiple_files", markdown)
        self.assertIn("Expected status: `complete`", markdown)
        self.assertIn("Observed status: `partial`", markdown)


if __name__ == "__main__":
    unittest.main()