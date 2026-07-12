import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.evaluation.failure_analysis import (  # noqa: E402
    find_latest_eval_result,
    load_eval_report,
    render_failure_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown failure report from an evaluation result JSON."
    )

    parser.add_argument(
        "--input",
        default=None,
        help="Path to an eval result JSON file.",
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the most recent JSON file under evals/results.",
    )

    parser.add_argument(
        "--results-dir",
        default="evals/results",
        help="Directory used when --latest is provided.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional output Markdown path.",
    )

    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the generated report to stdout.",
    )

    return parser.parse_args()


def resolve_input_path(args: argparse.Namespace) -> Path:
    if args.latest:
        return find_latest_eval_result(args.results_dir)

    if args.input:
        input_path = Path(args.input)

        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path

        return input_path

    raise ValueError("Provide either --input <path> or --latest.")


def default_output_path(input_path: Path) -> Path:
    stem = input_path.stem
    return PROJECT_ROOT / "evals" / "reports" / f"{stem}-failures.md"


def main() -> int:
    args = parse_args()

    try:
        input_path = resolve_input_path(args)
        report = load_eval_report(input_path)
        markdown = render_failure_report(report, source_path=str(input_path))

        output_path = Path(args.output) if args.output else default_output_path(input_path)

        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        if args.print:
            print(markdown)

        print(f"Failure report written to: {output_path}")
        return 0

    except Exception as exc:
        print(f"Failed to generate failure report: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())