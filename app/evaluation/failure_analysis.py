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
        "forbidden_tools",
        "missing_required_tools",
        "used_forbidden_tools",
        "actual_tools",
        "missing_required",
        "present_excluded",
        "matched_any",
        "matched_expectations",
        "total_expectations",
        "unsupported_files",
        "observed_files",
        "answer_files",
        "answer_length",
        "minimum_characters",
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


def _truncate_text(text: str, max_chars: int = 1200) -> str:
    normalized = text.strip()

    if len(normalized) <= max_chars:
        return normalized

    return normalized[:max_chars].rstrip() + "\n\n...[truncated]"


def _format_final_answer_excerpt(final_answer: str) -> str:
    if not final_answer.strip():
        return ""

    return "\n".join(
        [
            "**Final answer excerpt:**",
            "",
            "```text",
            _truncate_text(final_answer),
            "```",
            "",
        ]
    )


def _format_run_summary_tool_calls(run_summary: dict[str, Any]) -> str:
    tool_calls = run_summary.get("tool_calls")

    if not isinstance(tool_calls, list) or not tool_calls:
        return ""

    compact_calls = []

    for item in tool_calls[:10]:
        if not isinstance(item, dict):
            continue

        result = item.get("result")
        result = result if isinstance(result, dict) else {}

        compact_calls.append(
            {
                "tool": item.get("tool") or item.get("tool_name"),
                "kind": item.get("kind"),
                "status": item.get("status"),
                "ok": item.get("ok"),
                "source": item.get("source"),
                "arguments": item.get("arguments"),
                "error": result.get("error"),
                "mcp": item.get("mcp"),
            }
        )

    if not compact_calls:
        return ""

    if len(tool_calls) > 10:
        compact_calls.append(
            {
                "truncated": True,
                "remaining_tool_calls": len(tool_calls) - 10,
            }
        )

    return "\n".join(
        [
            "**Tool call summary:**",
            "",
            "```json",
            json.dumps(compact_calls, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    )


def _format_list_signal(value: Any) -> str:
    if not value:
        return "- None"

    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)

    return f"- {value}"


def _format_completion_signals(details: dict[str, Any]) -> str:
    signals = details.get("signals")

    if not isinstance(signals, dict):
        return ""

    lines = [
        "**Completion signals:**",
        "",
        f"- Expected status: `{details.get('expected')}`",
        f"- Observed status: `{details.get('actual')}`",
        f"- Reason: {details.get('reason')}",
        f"- Route: `{signals.get('route')}`",
        f"- Tool policy should use tools: `{signals.get('tool_policy_should_use_tools')}`",
        f"- Has final answer: `{signals.get('has_final_answer')}`",
        f"- Successful tool calls: {signals.get('successful_tool_calls')}",
        f"- Failed tool calls: {signals.get('failed_tool_calls')}",
        f"- Denied tool calls: {signals.get('denied_tool_calls')}",
        f"- Denied approvals: {signals.get('denied_approvals')}",
        "",
        "Actual tools:",
        "",
        _format_list_signal(signals.get("actual_tools")),
        "",
        "Missing required tools:",
        "",
        _format_list_signal(signals.get("missing_required_tools")),
        "",
        "Forbidden tools used:",
        "",
        _format_list_signal(signals.get("used_forbidden_tools")),
        "",
        "Policy error tools:",
        "",
        _format_list_signal(signals.get("policy_error_tools")),
        "",
        "Remaining steps:",
        "",
        _format_list_signal(signals.get("remaining_steps")),
        "",
    ]

    return "\n".join(lines)


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

        final_answer_excerpt = _format_final_answer_excerpt(result.final_answer)

        if final_answer_excerpt:
            lines.append(final_answer_excerpt)

        tool_call_summary = _format_run_summary_tool_calls(result.run_summary)

        if tool_call_summary:
            lines.append(tool_call_summary)

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

            if check.name == "task_completion":
                completion_signals = _format_completion_signals(check.details)

                if completion_signals:
                    lines.append("")
                    lines.append(completion_signals)

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