import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "evals" / "results" / "repeats"


@dataclass(frozen=True)
class RepeatResult:
    index: int
    passed: bool
    score: float
    duration_ms: int
    output_path: Path
    failed_checks: list[str]
    error_type: str | None = None
    error_message: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one eval case repeatedly to detect flaky behavior."
    )

    parser.add_argument(
        "--case-id",
        required=True,
        help="Eval case ID to run repeatedly.",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of repeated runs.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout in seconds for each run.",
    )

    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed run.",
    )

    return parser.parse_args()


def run_once(case_id: str, index: int, timeout: int) -> RepeatResult:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RESULTS_DIR / f"{case_id}-repeat-{index}.json"

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_evals.py"),
        "--case-id",
        case_id,
        "--timeout",
        str(timeout),
        "--output",
        str(output_path),
        "--no-failure-report",
    ]

    started = time.perf_counter()

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    fallback_duration_ms = int((time.perf_counter() - started) * 1000)

    if not output_path.exists():
        return RepeatResult(
            index=index,
            passed=False,
            score=0.0,
            duration_ms=fallback_duration_ms,
            output_path=output_path,
            failed_checks=[],
            error_type="OutputMissing",
            error_message=(completed.stderr or completed.stdout or "").strip(),
        )

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return RepeatResult(
            index=index,
            passed=False,
            score=0.0,
            duration_ms=fallback_duration_ms,
            output_path=output_path,
            failed_checks=[],
            error_type="InvalidJSON",
            error_message=str(exc),
        )

    results = payload.get("results", [])

    if not results:
        return RepeatResult(
            index=index,
            passed=False,
            score=0.0,
            duration_ms=fallback_duration_ms,
            output_path=output_path,
            failed_checks=[],
            error_type="NoCaseResult",
            error_message="Eval report did not contain case results.",
        )

    case_result = results[0]
    error = case_result.get("error")

    failed_checks = [
        check.get("name", "unknown")
        for check in case_result.get("checks", [])
        if check.get("status") == "failed"
    ]

    return RepeatResult(
        index=index,
        passed=bool(case_result.get("passed")),
        score=float(case_result.get("score", 0.0)),
        duration_ms=int(case_result.get("duration_ms", fallback_duration_ms)),
        output_path=output_path,
        failed_checks=failed_checks,
        error_type=error.get("error_type") if isinstance(error, dict) else None,
        error_message=error.get("message") if isinstance(error, dict) else None,
    )


def print_result(result: RepeatResult) -> None:
    marker = "PASS" if result.passed else "FAIL"

    print(
        f"[{marker}] run={result.index} "
        f"score={result.score:.2f} "
        f"time={result.duration_ms}ms "
        f"report={result.output_path}"
    )

    if result.failed_checks:
        print(f"  failed_checks={result.failed_checks}")

    if result.error_type:
        print(f"  error={result.error_type}: {result.error_message}")


def main() -> int:
    args = parse_args()

    if args.count < 1:
        print("--count must be at least 1.")
        return 1

    results: list[RepeatResult] = []

    print(f"Repeated eval run: {args.case_id}")
    print(f"Count: {args.count}")
    print()

    for index in range(1, args.count + 1):
        result = run_once(
            case_id=args.case_id,
            index=index,
            timeout=args.timeout,
        )

        results.append(result)
        print_result(result)
        print()

        if args.stop_on_failure and not result.passed:
            break

    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count
    pass_rate = passed_count / len(results) if results else 0.0

    observed_outcomes = {result.passed for result in results}
    flaky = len(observed_outcomes) > 1

    print("Repeat Summary")
    print("--------------")
    print(f"Case:       {args.case_id}")
    print(f"Runs:       {len(results)}")
    print(f"Passed:     {passed_count}")
    print(f"Failed:     {failed_count}")
    print(f"Pass rate:  {pass_rate:.1%}")
    print(f"Flaky:      {'yes' if flaky else 'no'}")

    if flaky:
        print()
        print("Observed both passing and failing outcomes.")
        return 1

    if failed_count:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())