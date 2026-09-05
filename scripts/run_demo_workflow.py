import argparse
import os
import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_REPO_REVIEW_PROMPT = (
    "Analyze this codebase structure and explain its architecture."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic repo review demo workflow."
    )

    parser.add_argument(
        "--prompt",
        default=DEFAULT_REPO_REVIEW_PROMPT,
        help="Prompt to send to the agent.",
    )

    parser.add_argument(
        "--fixture-root",
        default="evals/fixtures/sample_repo",
        help="Fixture repository root for safe local file inspection.",
    )

    parser.add_argument(
        "--data-dir",
        default="data/demo",
        help="Demo data directory for memory, traces, and generated notes.",
    )

    parser.add_argument(
        "--approval-response",
        choices=["y", "n"],
        default="n",
        help="Automatic response for approval prompts during the demo.",
    )

    parser.add_argument(
        "--no-inspect",
        action="store_true",
        help="Do not print the run summary inspector output.",
    )

    parser.add_argument(
        "--max-answer-chars",
        type=int,
        default=1800,
        help="Maximum final answer characters shown by the inspector.",
    )

    parser.add_argument(
        "--max-result-chars",
        type=int,
        default=900,
        help="Maximum tool result characters shown by the inspector.",
    )

    return parser.parse_args()


def configure_demo_environment(
    fixture_root: str,
    data_dir: str,
) -> Path:
    resolved_fixture_root = Path(fixture_root)

    if not resolved_fixture_root.is_absolute():
        resolved_fixture_root = PROJECT_ROOT / resolved_fixture_root

    resolved_fixture_root = resolved_fixture_root.resolve()

    if not resolved_fixture_root.is_dir():
        raise ValueError(
            f"Demo fixture root does not exist: {resolved_fixture_root}"
        )

    resolved_data_dir = Path(data_dir)

    if not resolved_data_dir.is_absolute():
        resolved_data_dir = PROJECT_ROOT / resolved_data_dir

    resolved_data_dir = resolved_data_dir.resolve()
    notes_dir = resolved_data_dir / "notes"

    notes_dir.mkdir(parents=True, exist_ok=True)

    os.environ["EVAL_MODE"] = "true"
    os.environ["EVAL_FIXTURE_ROOT"] = str(resolved_fixture_root)
    os.environ["EVAL_ALLOW_REAL_SIDE_EFFECTS"] = "false"

    os.environ["DATA_DIR"] = str(resolved_data_dir)
    os.environ["MEMORY_PATH"] = str(resolved_data_dir / "memory.json")
    os.environ["TRACE_PATH"] = str(resolved_data_dir / "traces.jsonl")
    os.environ["NOTES_DIR"] = str(notes_dir)

    os.environ.setdefault("ENABLE_SKILLS", "true")

    # Keep the demo local and safe by default.
    os.environ.setdefault("ENABLE_MCP_TOOLS", "false")
    os.environ.setdefault("ENABLE_REAL_MCP_TOOLS", "false")
    os.environ.setdefault("ENABLE_MOCK_MCP_TOOLS", "false")

    return resolved_data_dir


def run_demo(args: argparse.Namespace) -> int:
    data_dir = configure_demo_environment(
        fixture_root=args.fixture_root,
        data_dir=args.data_dir,
    )

    # Import after environment configuration because app.config reads env vars
    # during module import.
    from app.agent import DesktopAssistantAgent
    from scripts.inspect_run import render_run_summary

    print("Demo Workflow")
    print("=============")
    print()
    print(f"Fixture root: {os.environ['EVAL_FIXTURE_ROOT']}")
    print(f"Data dir:     {data_dir}")
    print(f"Prompt:       {args.prompt}")
    print()

    agent = DesktopAssistantAgent()

    with patch(
        "builtins.input",
        return_value=args.approval_response,
    ):
        final_answer = agent.handle_user_message(args.prompt)

    print("Final Answer")
    print("------------")
    print(final_answer.strip())
    print()

    run_summary = agent.last_run_summary

    if run_summary is None:
        raise RuntimeError("Agent finished without exposing last_run_summary.")

    if not args.no_inspect:
        print("Inspector Output")
        print("----------------")
        print(
            render_run_summary(
                run_summary,
                max_answer_chars=args.max_answer_chars,
                max_result_chars=args.max_result_chars,
            )
        )

    return 0


def main() -> int:
    args = parse_args()

    try:
        return run_demo(args)
    except Exception as exc:
        print(f"Demo workflow failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())