from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.evaluation.failure_analysis import find_latest_eval_result, load_eval_report
from app.evaluation.results import EvalCaseRunResult, EvalRunReport


@dataclass(frozen=True)
class CaseScoreChange:
    case_id: str
    suite: str
    baseline_score: float
    current_score: float
    delta: float
    baseline_passed: bool
    current_passed: bool


@dataclass(frozen=True)
class CaseStatusChange:
    case_id: str
    suite: str
    baseline_passed: bool
    current_passed: bool
    baseline_score: float
    current_score: float


@dataclass(frozen=True)
class EvalReportComparison:
    baseline_run_id: str
    current_run_id: str
    baseline_total_cases: int
    current_total_cases: int
    baseline_pass_rate: float
    current_pass_rate: float
    pass_rate_delta: float
    baseline_average_score: float
    current_average_score: float
    average_score_delta: float
    new_failures: list[CaseStatusChange] = field(default_factory=list)
    fixed_cases: list[CaseStatusChange] = field(default_factory=list)
    score_regressions: list[CaseScoreChange] = field(default_factory=list)
    score_improvements: list[CaseScoreChange] = field(default_factory=list)
    added_cases: list[str] = field(default_factory=list)
    removed_cases: list[str] = field(default_factory=list)


def compare_eval_reports(
    baseline: EvalRunReport,
    current: EvalRunReport,
    min_score_delta: float = 0.05,
) -> EvalReportComparison:
    baseline_cases = {result.case_id: result for result in baseline.results}
    current_cases = {result.case_id: result for result in current.results}

    shared_case_ids = sorted(set(baseline_cases) & set(current_cases))
    added_cases = sorted(set(current_cases) - set(baseline_cases))
    removed_cases = sorted(set(baseline_cases) - set(current_cases))

    new_failures = []
    fixed_cases = []
    score_regressions = []
    score_improvements = []

    for case_id in shared_case_ids:
        baseline_result = baseline_cases[case_id]
        current_result = current_cases[case_id]

        if baseline_result.passed and not current_result.passed:
            new_failures.append(
                _build_status_change(baseline_result, current_result)
            )

        if not baseline_result.passed and current_result.passed:
            fixed_cases.append(
                _build_status_change(baseline_result, current_result)
            )

        delta = current_result.score - baseline_result.score

        if delta <= -min_score_delta:
            score_regressions.append(
                _build_score_change(baseline_result, current_result, delta)
            )

        if delta >= min_score_delta:
            score_improvements.append(
                _build_score_change(baseline_result, current_result, delta)
            )

    score_regressions.sort(key=lambda change: change.delta)
    score_improvements.sort(key=lambda change: change.delta, reverse=True)

    return EvalReportComparison(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        baseline_total_cases=baseline.total_cases,
        current_total_cases=current.total_cases,
        baseline_pass_rate=baseline.pass_rate,
        current_pass_rate=current.pass_rate,
        pass_rate_delta=current.pass_rate - baseline.pass_rate,
        baseline_average_score=baseline.average_score,
        current_average_score=current.average_score,
        average_score_delta=current.average_score - baseline.average_score,
        new_failures=new_failures,
        fixed_cases=fixed_cases,
        score_regressions=score_regressions,
        score_improvements=score_improvements,
        added_cases=added_cases,
        removed_cases=removed_cases,
    )


def compare_eval_report_files(
    baseline_path: str | Path,
    current_path: str | Path,
    min_score_delta: float = 0.05,
) -> EvalReportComparison:
    baseline = load_eval_report(baseline_path)
    current = load_eval_report(current_path)

    return compare_eval_reports(
        baseline=baseline,
        current=current,
        min_score_delta=min_score_delta,
    )


def compare_latest_to_baseline(
    baseline_path: str | Path,
    results_dir: str | Path = "evals/results",
    min_score_delta: float = 0.05,
) -> tuple[EvalReportComparison, Path]:
    current_path = find_latest_eval_result(results_dir)
    comparison = compare_eval_report_files(
        baseline_path=baseline_path,
        current_path=current_path,
        min_score_delta=min_score_delta,
    )

    return comparison, current_path


def render_comparison_report(
    comparison: EvalReportComparison,
    baseline_path: Optional[str] = None,
    current_path: Optional[str] = None,
) -> str:
    lines = [
        "# Evaluation Baseline Comparison",
        "",
        f"- Baseline run: `{comparison.baseline_run_id}`",
        f"- Current run: `{comparison.current_run_id}`",
        f"- Baseline file: `{baseline_path}`" if baseline_path else "- Baseline file: unknown",
        f"- Current file: `{current_path}`" if current_path else "- Current file: unknown",
        f"- Baseline total cases: {comparison.baseline_total_cases}",
        f"- Current total cases: {comparison.current_total_cases}",
        f"- Baseline pass rate: {comparison.baseline_pass_rate:.1%}",
        f"- Current pass rate: {comparison.current_pass_rate:.1%}",
        f"- Pass rate delta: {_format_signed_percent(comparison.pass_rate_delta)}",
        f"- Baseline average score: {comparison.baseline_average_score:.2f}",
        f"- Current average score: {comparison.current_average_score:.2f}",
        f"- Average score delta: {_format_signed_float(comparison.average_score_delta)}",
        "",
        "## Summary",
        "",
        f"- New failures: {len(comparison.new_failures)}",
        f"- Fixed cases: {len(comparison.fixed_cases)}",
        f"- Score regressions: {len(comparison.score_regressions)}",
        f"- Score improvements: {len(comparison.score_improvements)}",
        f"- Added cases: {len(comparison.added_cases)}",
        f"- Removed cases: {len(comparison.removed_cases)}",
        "",
    ]

    lines.extend(_render_status_changes("New Failures", comparison.new_failures))
    lines.extend(_render_status_changes("Fixed Cases", comparison.fixed_cases))
    lines.extend(_render_score_changes("Score Regressions", comparison.score_regressions))
    lines.extend(_render_score_changes("Score Improvements", comparison.score_improvements))
    lines.extend(_render_case_list("Added Cases", comparison.added_cases))
    lines.extend(_render_case_list("Removed Cases", comparison.removed_cases))

    return "\n".join(lines).strip() + "\n"


def has_regressions(comparison: EvalReportComparison) -> bool:
    return bool(comparison.new_failures or comparison.score_regressions)


def _build_status_change(
    baseline_result: EvalCaseRunResult,
    current_result: EvalCaseRunResult,
) -> CaseStatusChange:
    return CaseStatusChange(
        case_id=current_result.case_id,
        suite=current_result.suite,
        baseline_passed=baseline_result.passed,
        current_passed=current_result.passed,
        baseline_score=baseline_result.score,
        current_score=current_result.score,
    )


def _build_score_change(
    baseline_result: EvalCaseRunResult,
    current_result: EvalCaseRunResult,
    delta: float,
) -> CaseScoreChange:
    return CaseScoreChange(
        case_id=current_result.case_id,
        suite=current_result.suite,
        baseline_score=baseline_result.score,
        current_score=current_result.score,
        delta=delta,
        baseline_passed=baseline_result.passed,
        current_passed=current_result.passed,
    )


def _format_signed_percent(value: float) -> str:
    return f"{value:+.1%}"


def _format_signed_float(value: float) -> str:
    return f"{value:+.2f}"


def _render_status_changes(title: str, changes: list[CaseStatusChange]) -> list[str]:
    lines = [f"## {title}", ""]

    if not changes:
        lines.extend(["None.", ""])
        return lines

    for change in changes:
        lines.extend(
            [
                f"### `{change.case_id}`",
                "",
                f"- Suite: `{change.suite}`",
                f"- Baseline passed: {change.baseline_passed}",
                f"- Current passed: {change.current_passed}",
                f"- Baseline score: {change.baseline_score:.2f}",
                f"- Current score: {change.current_score:.2f}",
                "",
            ]
        )

    return lines


def _render_score_changes(title: str, changes: list[CaseScoreChange]) -> list[str]:
    lines = [f"## {title}", ""]

    if not changes:
        lines.extend(["None.", ""])
        return lines

    for change in changes:
        lines.extend(
            [
                f"### `{change.case_id}`",
                "",
                f"- Suite: `{change.suite}`",
                f"- Baseline score: {change.baseline_score:.2f}",
                f"- Current score: {change.current_score:.2f}",
                f"- Delta: {_format_signed_float(change.delta)}",
                f"- Baseline passed: {change.baseline_passed}",
                f"- Current passed: {change.current_passed}",
                "",
            ]
        )

    return lines


def _render_case_list(title: str, case_ids: list[str]) -> list[str]:
    lines = [f"## {title}", ""]

    if not case_ids:
        lines.extend(["None.", ""])
        return lines

    lines.extend(f"- `{case_id}`" for case_id in case_ids)
    lines.append("")

    return lines