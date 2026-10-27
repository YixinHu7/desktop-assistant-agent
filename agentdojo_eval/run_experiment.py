"""Run the AgentDojo comparison: baseline vs built-in tool_filter vs query-derived policy variants.

Arms (all use the same model, suite, user tasks, injection tasks and attack):
  baseline     - no defense
  tool_filter  - AgentDojo's built-in defense (removes tools the query does not need)
  advisory     - query-derived policy injected into the prompt as a hint only (no enforcement)
  enforce      - query-derived policy enforced at execution time (calls outside the set are denied)
  enforce_writes - same, but read-only tools (get_/search_/list_/read_) are never blocked; only
                 state-changing tools must be in the allowed set (optional, not run by default)
  both         - hint in the prompt AND enforcement   (optional, not run by default)

Metrics per arm (each with a 95% Wilson interval):
  utility_clean   - user-task success without any attack
  utility_attack  - user-task success while the attack is present
  asr             - attack success rate: fraction of (user task, injection task) pairs where the
                    attacker's goal was achieved. AgentDojo calls this field "security_results", and
                    its CLI prints it as "Average security", but True means the ATTACK SUCCEEDED.

Re-running the same command resumes from the logs in --logdir (finished tasks are not re-run).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import openai
from dotenv import load_dotenv

from agentdojo.agent_pipeline import (
    AgentPipeline,
    InitQuery,
    OpenAILLM,
    PipelineConfig,
    SystemMessage,
    ToolsExecutionLoop,
    ToolsExecutor,
)
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import SuiteResults, benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite

from query_guard import GatedToolsExecutor, QueryToolPolicy

DEFAULT_ARMS = ["baseline", "tool_filter", "advisory", "enforce"]
ALL_ARMS = [*DEFAULT_ARMS, "enforce_writes", "both"]


def build_pipeline(arm: str, model: str, client: openai.OpenAI, decision_log: Path | None = None) -> AgentPipeline:
    """Build the agent pipeline for one arm. The pipeline name must contain the model name.

    decision_log: optional JSONL file where the query-derived policy records every decision.
    """
    if arm in ("baseline", "tool_filter"):
        # Built-in pipelines, constructed exactly like AgentDojo's own CLI does.
        return AgentPipeline.from_config(
            PipelineConfig(
                llm=model,
                model_id=None,
                defense=None if arm == "baseline" else "tool_filter",
                system_message_name=None,
                system_message=None,
            )
        )

    llm = OpenAILLM(client, model)
    # "enforce_writes" uses the same policy as "enforce", but read-only tools are never blocked.
    policy_mode = "enforce" if arm == "enforce_writes" else arm
    policy = QueryToolPolicy(client, model, mode=policy_mode, decision_log=decision_log)
    if arm == "enforce_writes":
        executor = GatedToolsExecutor(allow_reads=True)
    elif arm in ("enforce", "both"):
        executor = GatedToolsExecutor()
    else:
        executor = ToolsExecutor()
    pipeline = AgentPipeline(
        [
            SystemMessage(load_system_message(None)),
            InitQuery(),
            policy,
            llm,
            ToolsExecutionLoop([executor, llm]),
        ]
    )
    # Some attacks read the model name from the pipeline name, and logs are stored per pipeline name.
    pipeline.name = f"{model}-policy-{arm}"
    return pipeline


def natural_key(task_id: str) -> int:
    return int(re.findall(r"\d+", task_id)[-1])


def pick_spread(ids: list[str], n: int) -> list[str]:
    """Pick n ids spread evenly over the sorted list (deterministic, not just the first n)."""
    ids = sorted(ids, key=natural_key)
    if n >= len(ids):
        return ids
    step = len(ids) / n
    return [ids[int(i * step)] for i in range(n)]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(values: list[bool]) -> dict:
    k, n = sum(values), len(values)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else float("nan"), "ci95": [lo, hi]}


def pairs_to_json(results: dict[tuple[str, str], bool]) -> dict[str, bool]:
    return {f"{user}|{inj}": value for (user, inj), value in results.items()}


def run_arm(arm, args, suite, user_tasks, injection_tasks, client) -> dict:
    logdir = Path(args.logdir)
    pipeline = build_pipeline(arm, args.model, client, decision_log=logdir / "policy_decisions.jsonl")
    with OutputLogger(str(logdir)):
        clean: SuiteResults = benchmark_suite_without_injections(
            pipeline,
            suite,
            logdir=logdir,
            force_rerun=args.force_rerun,
            user_tasks=user_tasks,
            benchmark_version=args.benchmark_version,
        )
        attacker = load_attack(args.attack, suite, pipeline)
        attacked: SuiteResults = benchmark_suite_with_injections(
            pipeline,
            suite,
            attacker,
            logdir=logdir,
            force_rerun=args.force_rerun,
            user_tasks=user_tasks,
            injection_tasks=injection_tasks,
            benchmark_version=args.benchmark_version,
        )
    return {
        "pipeline_name": pipeline.name,
        "utility_clean": rate(list(clean["utility_results"].values())),
        "utility_attack": rate(list(attacked["utility_results"].values())),
        "asr": rate(list(attacked["security_results"].values())),
        "raw": {
            "clean_utility": pairs_to_json(clean["utility_results"]),
            "attack_utility": pairs_to_json(attacked["utility_results"]),
            "attack_success": pairs_to_json(attacked["security_results"]),
        },
    }


def fmt(stat: dict) -> str:
    lo, hi = stat["ci95"]
    return f"{stat['rate'] * 100:5.1f}% ({stat['k']}/{stat['n']}) [{lo * 100:4.1f}-{hi * 100:4.1f}]"


def print_table(results: dict[str, dict]) -> None:
    print("\n95% Wilson intervals in brackets. ASR = attack success rate (lower is better).\n")
    header = f"{'arm':<13}{'utility (no attack)':<30}{'utility (attack)':<30}{'ASR':<30}"
    print(header)
    print("-" * len(header))
    for arm, res in results.items():
        print(f"{arm:<13}{fmt(res['utility_clean']):<30}{fmt(res['utility_attack']):<30}{fmt(res['asr']):<30}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18", help="Must be an OpenAI model AgentDojo supports.")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--arms", default=",".join(DEFAULT_ARMS), help=f"Comma-separated, from: {ALL_ARMS}")
    parser.add_argument("--n-user-tasks", type=int, default=10)
    parser.add_argument("--n-injection-tasks", type=int, default=3)
    parser.add_argument(
        "--user-tasks",
        default=None,
        help="Comma-separated user task ids (e.g. user_task_13,user_task_19). Overrides --n-user-tasks.",
    )
    parser.add_argument(
        "--injection-tasks",
        default=None,
        help="Comma-separated injection task ids (e.g. injection_task_0,injection_task_13). Overrides --n-injection-tasks.",
    )
    parser.add_argument("--logdir", default="runs")
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--force-rerun", action="store_true", help="Ignore cached logs and re-run everything.")
    args = parser.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ALL_ARMS]
    if unknown:
        parser.error(f"Unknown arms: {unknown}. Choose from {ALL_ARMS}")

    load_dotenv()  # reads OPENAI_API_KEY from .env if present
    client = openai.OpenAI()

    suite = get_suite(args.benchmark_version, args.suite)
    if args.user_tasks:
        user_tasks = [t.strip() for t in args.user_tasks.split(",") if t.strip()]
        missing = [t for t in user_tasks if t not in suite.user_tasks]
        if missing:
            parser.error(f"Unknown user tasks: {missing}")
    else:
        user_tasks = pick_spread(list(suite.user_tasks), args.n_user_tasks)
    if args.injection_tasks:
        injection_tasks = [t.strip() for t in args.injection_tasks.split(",") if t.strip()]
        missing = [t for t in injection_tasks if t not in suite.injection_tasks]
        if missing:
            parser.error(f"Unknown injection tasks: {missing}")
    else:
        injection_tasks = pick_spread(list(suite.injection_tasks), args.n_injection_tasks)
    print(f"Suite: {args.suite} ({args.benchmark_version}); attack: {args.attack}; model: {args.model}")
    print(f"User tasks ({len(user_tasks)}): {user_tasks}")
    print(f"Injection tasks ({len(injection_tasks)}): {injection_tasks}")
    print(f"Arms: {arms}")

    results: dict[str, dict] = {}
    for arm in arms:
        print(f"\n=== Arm: {arm} ===")
        results[arm] = run_arm(arm, args, suite, user_tasks, injection_tasks, client)
        # Save after every arm so an interrupted run keeps what it has.
        Path(args.out).write_text(
            json.dumps(
                {
                    "config": {k: v for k, v in vars(args).items()},
                    "user_tasks": user_tasks,
                    "injection_tasks": injection_tasks,
                    "arms": results,
                },
                indent=2,
            )
        )

    print_table(results)
    print(f"\nSaved per-pair results to {args.out}; full traces are in {args.logdir}/")


if __name__ == "__main__":
    main()