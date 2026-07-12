import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.evaluation.results import EvalRunReport


@dataclass
class FailureSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    pass_rate: float
    average_score: float

    failures_by_suite: Counter = field(default_factory=Counter)
    failures_by_check: Counter = field(default_factory=Counter)
    errors_by_type: Counter = field(default_factory=Counter)
    judge_failures: int = 0
    judge_errors: int = 0


def load_eval_report(path: str | Path) -> EvalRunReport:
    report_path = Path(path)

    raw = json.loads(report_path.read_text(encoding="utf-8"))
    return EvalRunReport.model_validate(raw)


def find_latest_eval_result(results_dir: str | Path = "evals/results") -> Path:
    root = Path(results_dir)

    if not root.exists():
        raise FileNotFoundError(f"Results directory does not exist: {root}")

    candidates = sorted(
        root.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(f"No evaluation result JSON files found in: {root}")

    return candidates[0]


def build_failure_summary(report: EvalRunReport) -> FailureSummary:
    summary = FailureSummary(
        total_cases=report.total_cases,
        passed_cases=report.passed_cases,
        failed_cases=report.failed_cases,
        error_cases=report.error_cases,
        pass_rate=report.pass_rate,
        average_score=report.average_score,
    )

    for result in report.results:
        if result.passed:
            continue

        summary.failures_by_suite[result.suite] += 1

        if result.error is not None:
            summary.errors_by_type[result.error.error_type] += 1

        for check in result.checks:
            if check.status.value == "failed":
                summary.failures_by_check[check.name] += 1

        if result.judge is not None and result.judge.enabled:
            if result.judge.error is not None:
                summary.judge_errors += 1
            elif result.judge.passed is False:
                summary.judge_failures += 1

    return summary


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "- None\n"

    lines = []

    for key, count in counter.most_common():
        lines.append(f"- `{key}`: {count}")

    return "\n".join(lines) + "\n"


def _format_check_details(details: dict[str, Any]) -> str:
    if not details:
        return ""

    interesting_keys = [
        "expected",
        "actual",
        "required_tools",
        "missing_required_tools",
        "used_forbidden_tools",
        "actual_tools",
        "missing_required",
        "present_excluded",
        "unsupported_files",
        "observed_files",
        "answer_files",
        "reason",
    ]

    selected = {
        key: details[key]
        for key in interesting_keys
        if key in details
    }

    if not selected:
        return ""

    formatted = json.dumps(selected, indent=2, ensure_ascii=False)
    return f"\n```json\n{formatted}\n```\n"


def _case_failure_reason(result) -> str:
    if result.error is not None:
        return f"Worker error: {result.error.error_type}: {result.error.message}"

    failed_checks = [
        check
        for check in result.checks
        if check.status.value == "failed"
    ]

    if failed_checks:
        names = ", ".join(check.name for check in failed_checks)
        return f"Failed checks: {names}"

    if result.judge is not None and result.judge.enabled:
        if result.judge.error is not None:
            return f"Judge error: {result.judge.error.error_type}"
        if result.judge.passed is False:
            return "LLM judge failed"

    return "Unknown failure reason"


def render_failure_report(report: EvalRunReport, source_path: Optional[str] = None) -> str:
    summary = build_failure_summary(report)

    lines = [
        f"# Evaluation Failure Report",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Source: `{source_path}`" if source_path else "- Source: unknown",
        f"- Requested suite: `{report.requested_suite or 'all'}`",
        f"- Total cases: {summary.total_cases}",
        f"- Passed cases: {summary.passed_cases}",
        f"- Failed cases: {summary.failed_cases}",
        f"- Error cases: {summary.error_cases}",
        f"- Pass rate: {summary.pass_rate:.1%}",
        f"- Average score: {summary.average_score:.2f}",
        "",
        "## Failure Groups",
        "",
        "### By Suite",
        "",
        _format_counter(summary.failures_by_suite),
        "### By Failed Check",
        "",
        _format_counter(summary.failures_by_check),
        "### By Worker Error Type",
        "",
        _format_counter(summary.errors_by_type),
        "### Judge Failures",
        "",
        f"- Judge failed cases: {summary.judge_failures}",
        f"- Judge error cases: {summary.judge_errors}",
        "",
        "## Failed Cases",
        "",
    ]

    failed_results = [result for result in report.results if not result.passed]

    if not failed_results:
        lines.append("No failed cases.")
        return "\n".join(lines).strip() + "\n"

    for result in failed_results:
        lines.extend(
            [
                f"### `{result.case_id}`",
                "",
                f"- Suite: `{result.suite}`",
                f"- Score: {result.score:.2f}",
                f"- Source: `{result.source_path}:{result.line_number}`",
                f"- Reason: {_case_failure_reason(result)}",
                "",
                f"**Description:** {result.description}",
                "",
            ]
        )

        if result.error is not None:
            lines.extend(
                [
                    "**Execution error:**",
                    "",
                    f"- Type: `{result.error.error_type}`",
                    f"- Message: {result.error.message}",
                    "",
                ]
            )

            if result.error.traceback:
                lines.extend(
                    [
                        "<details>",
                        "<summary>Traceback</summary>",
                        "",
                        "```text",
                        result.error.traceback.strip(),
                        "```",
                        "",
                        "</details>",
                        "",
                    ]
                )

            continue

        for check in result.checks:
            if check.status.value != "failed":
                continue

            lines.extend(
                [
                    f"#### Failed check: `{check.name}`",
                    "",
                    f"- Score: {check.score:.2f}",
                    f"- Message: {check.message}",
                ]
            )

            detail_text = _format_check_details(check.details)

            if detail_text:
                lines.append(detail_text)

            lines.append("")

        if result.judge is not None and result.judge.enabled:
            if result.judge.error is not None:
                lines.extend(
                    [
                        "#### Judge error",
                        "",
                        f"- Type: `{result.judge.error.error_type}`",
                        f"- Message: {result.judge.error.message}",
                        "",
                    ]
                )
            elif result.judge.passed is False:
                lines.extend(
                    [
                        "#### Judge failed",
                        "",
                        f"- Score: {result.judge.score}",
                        "",
                        "```json",
                        json.dumps(result.judge.details, indent=2, ensure_ascii=False),
                        "```",
                        "",
                    ]
                )

    lines.extend(
        [
            "## Suggested Debugging Order",
            "",
            "1. Fix worker errors first because failed execution can hide all downstream signals.",
            "2. Fix route and skill failures before tool failures.",
            "3. Fix tool selection before tool argument failures.",
            "4. Fix approval and recovery failures before judging final answer quality.",
            "5. Fix task completion and answer grounding after tool behavior is stable.",
            "6. Treat LLM judge failures as quality signals after deterministic checks are mostly passing.",
            "",
        ]
    )

    return "\n".join(lines).strip() + "\n"