import unittest
from datetime import datetime, timezone

from app.evaluation.comparison import (
    compare_eval_reports,
    has_regressions,
    render_comparison_report,
)
from app.evaluation.results import EvalCaseRunResult, EvalRunReport


def build_report(run_id: str, results: list[EvalCaseRunResult]) -> EvalRunReport:
    passed_cases = sum(1 for result in results if result.passed)
    failed_cases = len(results) - passed_cases
    average_score = (
        sum(result.score for result in results) / len(results)
        if results
        else 0.0
    )

    return EvalRunReport(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        requested_suite=None,
        total_cases=len(results),
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        error_cases=0,
        pass_rate=passed_cases / len(results) if results else 0.0,
        average_score=average_score,
        results=results,
    )


def build_case(case_id: str, passed: bool, score: float) -> EvalCaseRunResult:
    return EvalCaseRunResult(
        case_id=case_id,
        suite="regression",
        description=f"{case_id} description.",
        source_path="evals/cases/regression.jsonl",
        line_number=1,
        passed=passed,
        score=score,
        duration_ms=100,
        checks=[],
    )


class EvalComparisonTests(unittest.TestCase):
    def test_detects_new_failures_and_fixes(self):
        baseline = build_report(
            "baseline",
            [
                build_case("case_a", True, 1.0),
                build_case("case_b", False, 0.4),
            ],
        )
        current = build_report(
            "current",
            [
                build_case("case_a", False, 0.5),
                build_case("case_b", True, 1.0),
            ],
        )

        comparison = compare_eval_reports(baseline, current)

        self.assertEqual(
            [change.case_id for change in comparison.new_failures],
            ["case_a"],
        )
        self.assertEqual(
            [change.case_id for change in comparison.fixed_cases],
            ["case_b"],
        )
        self.assertTrue(has_regressions(comparison))

    def test_detects_score_regressions_and_improvements(self):
        baseline = build_report(
            "baseline",
            [
                build_case("case_a", True, 1.0),
                build_case("case_b", True, 0.5),
            ],
        )
        current = build_report(
            "current",
            [
                build_case("case_a", True, 0.8),
                build_case("case_b", True, 0.9),
            ],
        )

        comparison = compare_eval_reports(
            baseline,
            current,
            min_score_delta=0.1,
        )

        self.assertEqual(
            [change.case_id for change in comparison.score_regressions],
            ["case_a"],
        )
        self.assertEqual(
            [change.case_id for change in comparison.score_improvements],
            ["case_b"],
        )

    def test_detects_added_and_removed_cases(self):
        baseline = build_report(
            "baseline",
            [
                build_case("old_case", True, 1.0),
            ],
        )
        current = build_report(
            "current",
            [
                build_case("new_case", True, 1.0),
            ],
        )

        comparison = compare_eval_reports(baseline, current)

        self.assertEqual(comparison.added_cases, ["new_case"])
        self.assertEqual(comparison.removed_cases, ["old_case"])

    def test_render_comparison_report(self):
        baseline = build_report("baseline", [build_case("case_a", True, 1.0)])
        current = build_report("current", [build_case("case_a", False, 0.5)])

        comparison = compare_eval_reports(baseline, current)
        markdown = render_comparison_report(comparison)

        self.assertIn("Evaluation Baseline Comparison", markdown)
        self.assertIn("case_a", markdown)
        self.assertIn("New Failures", markdown)


if __name__ == "__main__":
    unittest.main()