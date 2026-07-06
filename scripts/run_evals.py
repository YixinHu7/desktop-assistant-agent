import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

from app.config import config
from app.evaluation import EvalJudgeResult
from app.evaluation.judge import run_llm_judge

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.evaluation import (  # noqa: E402
    EvalCaseLoadError,
    EvalCaseRunResult,
    EvalExecutionError,
    EvalRunReport,
    EvalSuite,
    load_eval_cases,
    score_eval_case,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run end-to-end desktop agent evaluations.")
    )

    parser.add_argument(
        "--cases-dir",
        default="evals/cases",
        help="Directory containing JSONL evaluation cases.",
    )

    parser.add_argument(
        "--suite",
        choices=[suite.value for suite in EvalSuite],
        default=None,
        help="Run one evaluation suite.",
    )

    parser.add_argument(
        "--case-id",
        default=None,
        help="Run one specific evaluation case.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run at most N selected cases.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Maximum seconds allowed for each case.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional path for the JSON report.",
    )

    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run optional LLM-as-Judge scoring for cases that enable it.",
    )

    parser.add_argument(
        "--judge-all",
        action="store_true",
        help="Run LLM-as-Judge for all selected cases.",
    )

    return parser.parse_args()


def run_worker(
    loaded_case,
    timeout_seconds: int,
) -> tuple[dict, int]:
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(
        prefix=(f"agent-eval-" f"{loaded_case.case.id}-")
    ) as temp_dir:
        temp_root = Path(temp_dir)

        case_path = temp_root / "case.json"

        output_path = temp_root / "worker-result.json"

        work_dir = temp_root / "workspace"

        work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        case_path.write_text(
            loaded_case.case.model_dump_json(indent=2),
            encoding="utf-8",
        )

        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "eval_worker.py"),
            "--case-path",
            str(case_path),
            "--output-path",
            str(output_path),
            "--work-dir",
            str(work_dir),
        ]

        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)

            return {
                "case_id": loaded_case.case.id,
                "final_answer": "",
                "run_summary": {},
                "error": {
                    "error_type": "TimeoutExpired",
                    "message": (
                        "Evaluation case exceeded " f"{timeout_seconds} seconds."
                    ),
                    "traceback": None,
                },
            }, duration_ms

        duration_ms = int((time.perf_counter() - started) * 1000)

        if output_path.exists():
            try:
                payload = json.loads(output_path.read_text(encoding="utf-8"))

            except json.JSONDecodeError as exc:
                payload = {
                    "case_id": loaded_case.case.id,
                    "final_answer": "",
                    "run_summary": {},
                    "error": {
                        "error_type": ("InvalidWorkerOutput"),
                        "message": str(exc),
                        "traceback": (completed.stderr or completed.stdout or None),
                    },
                }

        else:
            process_output = "\n".join(
                part
                for part in [
                    completed.stdout,
                    completed.stderr,
                ]
                if part
            )

            payload = {
                "case_id": loaded_case.case.id,
                "final_answer": "",
                "run_summary": {},
                "error": {
                    "error_type": ("WorkerOutputMissing"),
                    "message": ("Evaluation worker did not " "produce an output file."),
                    "traceback": (process_output or None),
                },
            }

        if completed.returncode != 0 and payload.get("error") is None:
            process_output = "\n".join(
                part
                for part in [
                    completed.stdout,
                    completed.stderr,
                ]
                if part
            )

            payload["error"] = {
                "error_type": ("WorkerProcessError"),
                "message": ("Worker exited with code " f"{completed.returncode}."),
                "traceback": (process_output or None),
            }

        return payload, duration_ms


def maybe_run_judge(
    client: OpenAI,
    loaded_case,
    result: EvalCaseRunResult,
    judge_enabled: bool,
    judge_all: bool,
) -> EvalCaseRunResult:
    if result.error is not None:
        result.judge = EvalJudgeResult(enabled=False)
        return result

    should_judge = judge_all or (
        judge_enabled and loaded_case.case.expected.judge.enabled
    )

    if not should_judge:
        result.judge = EvalJudgeResult(enabled=False)
        return result

    try:
        judge_score = run_llm_judge(
            client=client,
            case=loaded_case.case,
            run_summary=result.run_summary,
        )

        threshold = loaded_case.case.expected.judge.min_overall_score
        passed = True if threshold is None else judge_score.overall_quality >= threshold

        result.judge = EvalJudgeResult(
            enabled=True,
            score=judge_score.overall_quality,
            passed=passed,
            details=judge_score.model_dump(),
        )
        return result

    except Exception as exc:
        result.judge = EvalJudgeResult(
            enabled=True,
            score=None,
            passed=False,
            details={},
            error=EvalExecutionError(
                error_type=type(exc).__name__,
                message=str(exc),
                traceback=None,
            ),
        )
        return result


def build_case_result(
    loaded_case,
    worker_payload: dict,
    duration_ms: int,
) -> EvalCaseRunResult:
    execution_error = worker_payload.get("error")

    if execution_error is not None:
        return EvalCaseRunResult(
            case_id=loaded_case.case.id,
            suite=loaded_case.case.suite.value,
            description=(loaded_case.case.description),
            source_path=(loaded_case.source_path),
            line_number=(loaded_case.line_number),
            passed=False,
            score=0.0,
            duration_ms=duration_ms,
            final_answer=worker_payload.get(
                "final_answer",
                "",
            ),
            checks=[],
            run_summary=worker_payload.get(
                "run_summary",
                {},
            ),
            error=(EvalExecutionError.model_validate(execution_error)),
        )

    run_summary = worker_payload.get(
        "run_summary",
        {},
    )

    scored_result = score_eval_case(
        case=loaded_case.case,
        run_summary=run_summary,
    )

    return EvalCaseRunResult(
        case_id=loaded_case.case.id,
        suite=loaded_case.case.suite.value,
        description=(loaded_case.case.description),
        source_path=loaded_case.source_path,
        line_number=loaded_case.line_number,
        passed=scored_result.passed,
        score=scored_result.score,
        duration_ms=duration_ms,
        final_answer=worker_payload.get(
            "final_answer",
            "",
        ),
        checks=scored_result.checks,
        run_summary=run_summary,
        error=None,
    )


def print_case_result(
    result: EvalCaseRunResult,
) -> None:
    marker = "PASS" if result.passed else "FAIL"

    print(
        f"[{marker}] {result.case_id} "
        f"score={result.score:.2f} "
        f"time={result.duration_ms}ms"
    )

    if result.error is not None:
        print(f"  ERROR " f"{result.error.error_type}: " f"{result.error.message}")
        return

    for check in result.checks:
        if check.status.value == "skipped":
            continue

        print(f"  - {check.name}: " f"{check.status.value} " f"({check.score:.2f})")

        if check.status.value == "failed":
            print(f"    {check.message}")

    if result.judge is not None and result.judge.enabled:
        if result.judge.error is not None:
            print(
                f"  - llm_judge: error "
                f"{result.judge.error.error_type}: {result.judge.error.message}"
            )
        else:
            judge_marker = "passed" if result.judge.passed else "failed"
            print(f"  - llm_judge: {judge_marker} " f"({result.judge.score:.2f})")


def resolve_output_path(
    requested_output: str | None,
    run_id: str,
) -> Path:
    if requested_output:
        output_path = Path(requested_output)

        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        return output_path

    return PROJECT_ROOT / "evals" / "results" / f"{run_id}.json"


def main() -> int:
    args = parse_args()

    selected_suite = EvalSuite(args.suite) if args.suite else None

    try:
        loaded_cases = load_eval_cases(
            cases_dir=args.cases_dir,
            suite=selected_suite,
        )

    except EvalCaseLoadError as exc:
        print("Unable to load evaluation cases:")
        print(exc)
        return 1

    if args.case_id:
        loaded_cases = [
            loaded_case
            for loaded_case in loaded_cases
            if (loaded_case.case.id == args.case_id)
        ]

        if not loaded_cases:
            print("Evaluation case not found: " f"{args.case_id}")
            return 1

    if args.limit is not None:
        if args.limit < 1:
            print("--limit must be at least 1.")
            return 1

        loaded_cases = loaded_cases[: args.limit]

    if not loaded_cases:
        print("No evaluation cases were selected.")
        return 1

    started_at = datetime.now(timezone.utc)

    run_id = (
        "eval-" + started_at.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )

    results: list[EvalCaseRunResult] = []

    print(f"Evaluation run: {run_id}")
    print(f"Cases: {len(loaded_cases)}")
    print()

    judge_client = OpenAI() if (args.judge or args.judge_all) else None

    for index, loaded_case in enumerate(
        loaded_cases,
        start=1,
    ):
        print(f"Running {index}/" f"{len(loaded_cases)}: " f"{loaded_case.case.id}")

        worker_payload, duration_ms = run_worker(
            loaded_case=loaded_case,
            timeout_seconds=args.timeout,
        )

        case_result = build_case_result(
            loaded_case=loaded_case,
            worker_payload=worker_payload,
            duration_ms=duration_ms,
        )

        if judge_client is not None:
            case_result = maybe_run_judge(
                client=judge_client,
                loaded_case=loaded_case,
                result=case_result,
                judge_enabled=args.judge,
                judge_all=args.judge_all,
            )

        results.append(case_result)

        print_case_result(case_result)
        print()

    completed_at = datetime.now(timezone.utc)

    total_cases = len(results)

    passed_cases = sum(1 for result in results if result.passed)

    error_cases = sum(1 for result in results if result.error is not None)

    failed_cases = sum(
        1 for result in results if (not result.passed and result.error is None)
    )

    pass_rate = passed_cases / total_cases if total_cases else 0.0

    average_score = (
        sum(result.score for result in results) / total_cases if total_cases else 0.0
    )

    judge_results = [
        result.judge
        for result in results
        if result.judge is not None and result.judge.enabled
    ]

    judge_count = len(judge_results)
    judge_passed = sum(1 for judge in judge_results if judge.passed)
    judge_average = (
        sum(judge.score for judge in judge_results if judge.score is not None)
        / judge_count
        if judge_count
        else 0.0
    )

    report = EvalRunReport(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        requested_suite=args.suite,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        error_cases=error_cases,
        pass_rate=pass_rate,
        average_score=average_score,
        results=results,
    )

    output_path = resolve_output_path(
        requested_output=args.output,
        run_id=run_id,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print("Evaluation Summary")
    print("------------------")
    print(f"Total:         {total_cases}")
    print(f"Passed:        {passed_cases}")
    print(f"Failed:        {failed_cases}")
    print(f"Errors:        {error_cases}")
    print(f"Pass rate:     {pass_rate:.1%}")
    print(f"Average score: " f"{average_score:.2f}")
    
    if judge_count:
        print(f"Judge cases:   {judge_count}")
        print(f"Judge passed:  {judge_passed}")
        print(f"Judge average: {judge_average:.2f}")
        
    print(f"Report:        {output_path}")
    
    has_failures = failed_cases > 0 or error_cases > 0

    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
