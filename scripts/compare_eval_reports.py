import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.evaluation.comparison import (  # noqa: E402
    compare_eval_report_files,
    compare_latest_to_baseline,
    has_regressions,
    render_comparison_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare an eval report against a saved baseline."
    )

    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline eval result JSON.",
    )

    current_group = parser.add_mutually_exclusive_group(required=True)
    current_group.add_argument(
        "--latest",
        action="store_true",
        help="Compare against the latest JSON report under evals/results.",
    )
    current_group.add_argument(
        "--current",
        default=None,
        help="Path to current eval result JSON.",
    )

    parser.add_argument(
        "--results-dir",
        default="evals/results",
        help="Directory used with --latest.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional Markdown output path.",
    )
    parser.add_argument(
        "--min-score-delta",
        type=float,
        default=0.05,
        help="Minimum score delta to report as improvement or regression.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print comparison Markdown to stdout.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 when new failures or score regressions are found.",
    )

    return parser.parse_args()


def resolve_project_path(path: str) -> Path:
    resolved = Path(path)

    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved

    return resolved


def default_output_path(current_path: Path, baseline_path: Path) -> Path:
    return (
        PROJECT_ROOT
        / "evals"
        / "reports"
        / f"{current_path.stem}-vs-{baseline_path.stem}.md"
    )


def main() -> int:
    args = parse_args()

    try:
        baseline_path = resolve_project_path(args.baseline)

        if args.latest:
            comparison, current_path = compare_latest_to_baseline(
                baseline_path=baseline_path,
                results_dir=PROJECT_ROOT / args.results_dir,
                min_score_delta=args.min_score_delta,
            )
        else:
            current_path = resolve_project_path(args.current)
            comparison = compare_eval_report_files(
                baseline_path=baseline_path,
                current_path=current_path,
                min_score_delta=args.min_score_delta,
            )

        markdown = render_comparison_report(
            comparison=comparison,
            baseline_path=str(baseline_path),
            current_path=str(current_path),
        )

        output_path = (
            resolve_project_path(args.output)
            if args.output
            else default_output_path(current_path, baseline_path)
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

        if args.print:
            print(markdown)

        print("Evaluation comparison complete.")
        print(f"Baseline:          {baseline_path}")
        print(f"Current:           {current_path}")
        print(f"Comparison report: {output_path}")
        print(f"New failures:      {len(comparison.new_failures)}")
        print(f"Fixed cases:       {len(comparison.fixed_cases)}")
        print(f"Score regressions: {len(comparison.score_regressions)}")
        print(f"Score improvements:{len(comparison.score_improvements)}")

        if args.fail_on_regression and has_regressions(comparison):
            return 1

        return 0

    except Exception as exc:
        print(f"Failed to compare evaluation reports: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())