import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.failure_analysis import (
    build_failure_summary,
    find_latest_eval_result,
    load_eval_report,
)
from app.evaluation.results import EvalRunReport


@dataclass(frozen=True)
class EvalBaseline:
    name: str
    result_path: Path
    summary_path: Path
    metadata_path: Path


def normalize_baseline_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name.strip()).strip("-")

    if not normalized:
        raise ValueError("Baseline name cannot be empty.")

    return normalized


def default_baseline_name(report: EvalRunReport) -> str:
    return f"baseline-{report.run_id}"


def render_baseline_summary(report: EvalRunReport, source_path: str | None = None) -> str:
    summary = build_failure_summary(report)
    failed_results = [result for result in report.results if not result.passed]

    lines = [
        "# Evaluation Baseline",
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
        "## Failure Counts",
        "",
        "### By Suite",
        "",
        _format_counter(summary.failures_by_suite),
        "### By Check",
        "",
        _format_counter(summary.failures_by_check),
        "### By Worker Error Type",
        "",
        _format_counter(summary.errors_by_type),
        "",
        "## Failed Cases",
        "",
    ]

    if not failed_results:
        lines.append("No failed cases. This is a clean baseline.")
        return "\n".join(lines).strip() + "\n"

    for result in failed_results:
        failed_checks = [
            check.name
            for check in result.checks
            if check.status.value == "failed"
        ]

        lines.extend(
            [
                f"### `{result.case_id}`",
                "",
                f"- Suite: `{result.suite}`",
                f"- Score: {result.score:.2f}",
                f"- Failed checks: {', '.join(failed_checks) or 'none'}",
                f"- Source: `{result.source_path}:{result.line_number}`",
                "",
                result.description,
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def create_eval_baseline(
    input_path: str | Path,
    name: str | None = None,
    baselines_dir: str | Path = "evals/baselines",
    overwrite: bool = False,
) -> EvalBaseline:
    input_path = Path(input_path).resolve()
    report = load_eval_report(input_path)

    baseline_name = normalize_baseline_name(name or default_baseline_name(report))
    output_dir = Path(baselines_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result_path = output_dir / f"{baseline_name}.json"
    summary_path = output_dir / f"{baseline_name}-summary.md"
    metadata_path = output_dir / f"{baseline_name}-metadata.json"

    for path in [result_path, summary_path, metadata_path]:
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Baseline file already exists: {path}. "
                "Use --overwrite to replace it."
            )

    shutil.copyfile(input_path, result_path)

    summary = render_baseline_summary(report, source_path=str(input_path))
    summary_path.write_text(summary, encoding="utf-8")

    metadata = {
        "name": baseline_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(input_path),
        "result_path": str(result_path),
        "summary_path": str(summary_path),
        "run_id": report.run_id,
        "requested_suite": report.requested_suite,
        "total_cases": report.total_cases,
        "passed_cases": report.passed_cases,
        "failed_cases": report.failed_cases,
        "error_cases": report.error_cases,
        "pass_rate": report.pass_rate,
        "average_score": report.average_score,
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return EvalBaseline(
        name=baseline_name,
        result_path=result_path,
        summary_path=summary_path,
        metadata_path=metadata_path,
    )


def create_latest_eval_baseline(
    name: str | None = None,
    results_dir: str | Path = "evals/results",
    baselines_dir: str | Path = "evals/baselines",
    overwrite: bool = False,
) -> EvalBaseline:
    latest_result = find_latest_eval_result(results_dir)

    return create_eval_baseline(
        input_path=latest_result,
        name=name,
        baselines_dir=baselines_dir,
        overwrite=overwrite,
    )


def _format_counter(counter) -> str:
    if not counter:
        return "- None\n"

    return "\n".join(
        f"- `{key}`: {count}"
        for key, count in counter.most_common()
    ) + "\n"