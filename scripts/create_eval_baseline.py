import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.evaluation.baseline import (  # noqa: E402
    create_eval_baseline,
    create_latest_eval_baseline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a named evaluation baseline from an eval result JSON."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--latest",
        action="store_true",
        help="Use the latest JSON report under evals/results.",
    )
    source_group.add_argument(
        "--input",
        default=None,
        help="Path to a specific eval result JSON file.",
    )

    parser.add_argument(
        "--name",
        default=None,
        help="Baseline name, for example pre-mcp-baseline.",
    )
    parser.add_argument(
        "--results-dir",
        default="evals/results",
        help="Directory used with --latest.",
    )
    parser.add_argument(
        "--baselines-dir",
        default="evals/baselines",
        help="Directory where baseline files will be written.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing baseline with the same name.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the generated baseline summary.",
    )

    return parser.parse_args()


def resolve_input_path(path: str) -> Path:
    input_path = Path(path)

    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    return input_path


def main() -> int:
    args = parse_args()

    try:
        if args.latest:
            baseline = create_latest_eval_baseline(
                name=args.name,
                results_dir=PROJECT_ROOT / args.results_dir,
                baselines_dir=PROJECT_ROOT / args.baselines_dir,
                overwrite=args.overwrite,
            )
        else:
            baseline = create_eval_baseline(
                input_path=resolve_input_path(args.input),
                name=args.name,
                baselines_dir=PROJECT_ROOT / args.baselines_dir,
                overwrite=args.overwrite,
            )

        if args.print:
            print(baseline.summary_path.read_text(encoding="utf-8"))

        print(f"Baseline created: {baseline.name}")
        print(f"Result:           {baseline.result_path}")
        print(f"Summary:          {baseline.summary_path}")
        print(f"Metadata:         {baseline.metadata_path}")
        return 0

    except Exception as exc:
        print(f"Failed to create evaluation baseline: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())