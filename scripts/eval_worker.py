import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Importing this model is safe before environment configuration.
# Do not import app.agent here because app.config reads environment
# variables during module import.
from app.evaluation.models import EvalCase  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one agent evaluation case."
    )

    parser.add_argument(
        "--case-path",
        required=True,
        help="Path to a JSON file containing one EvalCase.",
    )

    parser.add_argument(
        "--output-path",
        required=True,
        help="Path where the worker result JSON will be written.",
    )

    parser.add_argument(
        "--work-dir",
        required=True,
        help="Temporary isolated directory for this case.",
    )

    return parser.parse_args()


def configure_case_environment(case: EvalCase, work_dir: Path) -> None:
    for key, value in case.environment.env.items():
        os.environ[key] = value

    fixture_root = case.environment.fixture_root

    if fixture_root:
        resolved_fixture_root = Path(fixture_root)

        if not resolved_fixture_root.is_absolute():
            resolved_fixture_root = PROJECT_ROOT / resolved_fixture_root

        resolved_fixture_root = resolved_fixture_root.resolve()

        if not resolved_fixture_root.is_dir():
            raise ValueError(
                f"Evaluation fixture root does not exist: {resolved_fixture_root}"
            )

        os.environ["EVAL_FIXTURE_ROOT"] = str(resolved_fixture_root)
    else:
        os.environ.pop("EVAL_FIXTURE_ROOT", None)

    os.environ["EVAL_ALLOW_REAL_SIDE_EFFECTS"] = (
        "true" if case.environment.allow_real_side_effects else "false"
    )

    eval_data_dir = work_dir / "data"
    eval_notes_dir = eval_data_dir / "notes"

    eval_data_dir.mkdir(parents=True, exist_ok=True)
    eval_notes_dir.mkdir(parents=True, exist_ok=True)

    os.environ["EVAL_MODE"] = "true"
    os.environ["DATA_DIR"] = str(eval_data_dir)
    os.environ["MEMORY_PATH"] = str(eval_data_dir / "memory.json")
    os.environ["TRACE_PATH"] = str(eval_data_dir / "trace.jsonl")
    os.environ["NOTES_DIR"] = str(eval_notes_dir)
    

def write_output(
    output_path: Path,
    payload: dict,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )


def normalize_approval_response(
    case: EvalCase,
) -> str:
    """
    Approval-required actions are denied by default.

    A specific eval case may override this by placing:
    {"approval_response": "y"}
    inside metadata.
    """

    response = str(
        case.metadata.get(
            "approval_response",
            "n",
        )
    ).strip().lower()

    if response not in {"y", "n"}:
        return "n"

    return response


def main() -> int:
    args = parse_args()

    case_path = Path(args.case_path)
    output_path = Path(args.output_path)
    work_dir = Path(args.work_dir)

    try:
        raw_case = json.loads(
            case_path.read_text(
                encoding="utf-8"
            )
        )

        case = EvalCase.model_validate(
            raw_case
        )

    except Exception as exc:
        write_output(
            output_path,
            {
                "case_id": "unknown",
                "final_answer": "",
                "run_summary": {},
                "error": {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            },
        )

        return 1

    configure_case_environment(
        case=case,
        work_dir=work_dir,
    )

    approval_response = normalize_approval_response(
        case
    )

    try:
        # This import must happen after environment variables
        # have been configured.
        from app.agent import DesktopAssistantAgent

        agent = DesktopAssistantAgent()

        # Prevent interactive approval prompts from blocking
        # an automated evaluation process.
        with patch(
            "builtins.input",
            return_value=approval_response,
        ):
            final_answer = (
                agent.handle_user_message(
                    case.input
                )
            )

        run_summary = agent.last_run_summary

        if run_summary is None:
            raise RuntimeError(
                "Agent completed without exposing "
                "last_run_summary."
            )

        write_output(
            output_path,
            {
                "case_id": case.id,
                "final_answer": final_answer,
                "run_summary": run_summary,
                "error": None,
            },
        )

        return 0

    except Exception as exc:
        write_output(
            output_path,
            {
                "case_id": case.id,
                "final_answer": "",
                "run_summary": {},
                "error": {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            },
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())