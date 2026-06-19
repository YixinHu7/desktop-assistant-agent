import argparse
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.evaluation import (  # noqa: E402
    EvalCaseLoadError,
    EvalSuite,
    load_eval_cases,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate evaluation case files."
    )

    parser.add_argument(
        "--cases-dir",
        default="evals/cases",
        help="Directory containing JSONL evaluation files.",
    )

    parser.add_argument(
        "--suite",
        choices=[suite.value for suite in EvalSuite],
        default=None,
        help="Validate and display one evaluation suite.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    suite = (
        EvalSuite(args.suite)
        if args.suite
        else None
    )

    try:
        cases = load_eval_cases(
            cases_dir=args.cases_dir,
            suite=suite,
        )
    except EvalCaseLoadError as exc:
        print(f"Evaluation validation failed:\n{exc}")
        return 1

    suite_counts = Counter(
        record.case.suite.value
        for record in cases
    )

    print("Evaluation cases are valid.")
    print(f"Total cases: {len(cases)}")

    if suite_counts:
        print()
        print("Cases by suite:")

        for suite_name, count in sorted(
            suite_counts.items()
        ):
            print(f"  - {suite_name}: {count}")

    print()
    print("Case IDs:")

    for record in cases:
        print(
            f"  - {record.case.id} "
            f"({record.source_path}:{record.line_number})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())