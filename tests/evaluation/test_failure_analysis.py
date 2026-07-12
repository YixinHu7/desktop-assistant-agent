import unittest
from datetime import datetime, timezone

from app.evaluation.failure_analysis import build_failure_summary, render_failure_report
from app.evaluation.results import (
    EvalCaseRunResult,
    EvalCheckResult,
    EvalCheckStatus,
    EvalRunReport,
)


class FailureAnalysisTests(unittest.TestCase):
    def test_build_failure_summary_counts_failed_checks(self):
        report = EvalRunReport(
            run_id="eval-test",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            requested_suite="tools",
            total_cases=2,
            passed_cases=1,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.5,
            average_score=0.75,
            results=[
                EvalCaseRunResult(
                    case_id="passing_case",
                    suite="tools",
                    description="Passing case.",
                    source_path="evals/cases/tools.jsonl",
                    line_number=1,
                    passed=True,
                    score=1.0,
                    duration_ms=100,
                    checks=[],
                ),
                EvalCaseRunResult(
                    case_id="failing_case",
                    suite="tools",
                    description="Failing case.",
                    source_path="evals/cases/tools.jsonl",
                    line_number=2,
                    passed=False,
                    score=0.5,
                    duration_ms=100,
                    checks=[
                        EvalCheckResult(
                            name="tool_selection",
                            status=EvalCheckStatus.FAILED,
                            score=0.0,
                            message="Missing required tool.",
                        )
                    ],
                ),
            ],
        )

        summary = build_failure_summary(report)

        self.assertEqual(summary.failures_by_suite["tools"], 1)
        self.assertEqual(summary.failures_by_check["tool_selection"], 1)

    def test_render_failure_report_includes_failed_case(self):
        report = EvalRunReport(
            run_id="eval-test",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            requested_suite=None,
            total_cases=1,
            passed_cases=0,
            failed_cases=1,
            error_cases=0,
            pass_rate=0.0,
            average_score=0.0,
            results=[
                EvalCaseRunResult(
                    case_id="tool_failure_001",
                    suite="tools",
                    description="Tool failure example.",
                    source_path="evals/cases/tools.jsonl",
                    line_number=3,
                    passed=False,
                    score=0.0,
                    duration_ms=100,
                    checks=[
                        EvalCheckResult(
                            name="tool_selection",
                            status=EvalCheckStatus.FAILED,
                            score=0.0,
                            message="Missing required tool.",
                            details={"missing_required_tools": ["read_file"]},
                        )
                    ],
                )
            ],
        )

        markdown = render_failure_report(report, source_path="evals/results/example.json")

        self.assertIn("tool_failure_001", markdown)
        self.assertIn("tool_selection", markdown)
        self.assertIn("read_file", markdown)


if __name__ == "__main__":
    unittest.main()