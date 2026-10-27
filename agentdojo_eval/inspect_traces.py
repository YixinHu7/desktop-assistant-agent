"""Inspect AgentDojo trace files: what did each arm actually do, and what did the policy block?

For every run under <logdir>/<pipeline_name>/<suite>/ it reports the outcome (utility / attack
success), the tool calls the assistant made, and which calls were denied by the policy gate.
If <logdir>/policy_decisions.jsonl exists (written by QueryToolPolicy), it also shows which tools
the policy allowed for each user task and which tools of the ideal solution were NOT allowed.

Run:
  python inspect_traces.py --logdir runs_hard                 # per-task summary for every arm
  python inspect_traces.py --logdir runs_hard --verbose       # also print every run's tool sequence
  python inspect_traces.py --logdir runs_hard --arm enforce --task user_task_13

Notes:
  * The policy decision log only exists for runs made after decision logging was added. Re-run the
    arm with a fresh --logdir (or --force-rerun) to get it; cached runs do not call the policy again.
  * A denial is recognised by the text "denied by policy" in a tool result's error field.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

DENIAL_MARKER = "denied by policy"


def text_of(content) -> str:
    """Join the text blocks of an AgentDojo message content field."""
    if not content:
        return ""
    return "\n".join(block.get("content") or "" for block in content if isinstance(block, dict))


def load_runs(logdir: Path, suite: str) -> list[dict]:
    runs = []
    for path in sorted(logdir.glob(f"*/{suite}/**/*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if "messages" not in data or "pipeline_name" not in data:
            continue
        calls, call_args, denied, other_errors = [], [], [], []
        first_user = ""
        for message in data["messages"]:
            role = message.get("role")
            if role == "user" and not first_user:
                first_user = text_of(message.get("content"))
            elif role == "assistant":
                for call in message.get("tool_calls") or []:
                    calls.append(call["function"])
                    call_args.append((call["function"], call.get("args")))
            elif role == "tool":
                error = message.get("error")
                name = message["tool_call"]["function"]
                if error and DENIAL_MARKER in error:
                    denied.append(name)
                elif error:
                    other_errors.append(f"{name}: {error[:80]}")
        injection_id = data.get("injection_task_id")
        has_injection = injection_id not in (None, "none")
        if str(data["user_task_id"]).startswith("injection_task"):
            kind = "injection_as_user"  # AgentDojo runs each injection goal as a plain user task too
        else:
            kind = "attacked" if has_injection else "clean"
        runs.append(
            {
                "pipeline": data["pipeline_name"],
                "kind": kind,
                "user_task": data["user_task_id"],
                "injection_task": injection_id,
                "utility": data.get("utility"),
                # AgentDojo stores security=True for runs without an attack; it only means something
                # when an injection was present, so hide it otherwise.
                "security": data.get("security") if kind == "attacked" else None,
                "calls": calls,
                "call_args": call_args,
                "denied": denied,
                "errors": other_errors,
                "query": first_user,
                "path": str(path),
            }
        )
    return runs


def load_decisions(logdir: Path) -> dict[str, list[dict]]:
    """query text -> list of logged policy decisions (in time order)."""
    path = logdir / "policy_decisions.jsonl"
    by_query: dict[str, list[dict]] = defaultdict(list)
    if not path.exists():
        return by_query
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            by_query[record["query"]].append(record)
    return by_query


def ideal_tools(suite_name: str, version: str) -> dict[str, set[str]]:
    """Tools of each user task's ground-truth solution (needs agentdojo; returns {} if unavailable)."""
    try:
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent))  # also works under `python -I`
        from agentdojo.task_suite.load_suites import get_suite

        from overlap_analysis import collect_ground_truth

        user_tools, _, _, _ = collect_ground_truth(get_suite(version, suite_name))
        return user_tools
    except Exception as exc:  # diagnostics must not crash on this
        print(f"(could not load ideal tool sets: {type(exc).__name__}: {exc})")
        return {}


def arm_of(pipeline_name: str) -> str:
    """Map a pipeline name back to its arm. The baseline pipeline name is just the model name."""
    if "-policy-" in pipeline_name:
        return pipeline_name.split("-policy-", 1)[1]
    if pipeline_name.endswith("-tool_filter"):
        return "tool_filter"
    return "baseline"


def fmt_pair(run: dict) -> str:
    inj = run["injection_task"] if run["injection_task"] not in (None, "none") else "-"
    return f"{run['user_task']}|{inj}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--logdir", default="runs_hard")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--version", default="v1.2.2")
    parser.add_argument(
        "--arm",
        default=None,
        help="Only this arm: baseline, tool_filter, advisory, enforce, enforce_writes or both (exact match).",
    )
    parser.add_argument("--task", default=None, help="Only this user task id, e.g. user_task_13.")
    parser.add_argument("--verbose", action="store_true", help="Print every run's tool-call sequence.")
    parser.add_argument(
        "--show-args",
        default=None,
        help="Comma-separated tool names whose call arguments are printed per run (implies --verbose), e.g. send_email.",
    )
    args = parser.parse_args()
    show_args = {t.strip() for t in args.show_args.split(",")} if args.show_args else set()
    if show_args:
        args.verbose = True

    logdir = Path(args.logdir)
    runs = load_runs(logdir, args.suite)
    if args.arm:
        # Exact arm match (so "enforce" does not also pick up "enforce_writes"); a full pipeline name works too.
        runs = [r for r in runs if args.arm in (arm_of(r["pipeline"]), r["pipeline"])]
    if args.task:
        runs = [r for r in runs if r["user_task"] == args.task]
    if not runs:
        print(f"No trace files found under {logdir}/*/{args.suite}/ with these filters.")
        return

    decisions = load_decisions(logdir)
    ideal = ideal_tools(args.suite, args.version)
    if not decisions:
        print("(no policy_decisions.jsonl found: allowed sets cannot be shown for these runs)\n")

    by_pipeline: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        by_pipeline[run["pipeline"]].append(run)

    for pipeline, group in sorted(by_pipeline.items()):
        print("=" * 100)
        print(f"PIPELINE {pipeline}   (arm: {arm_of(pipeline)}, {len(group)} runs)")
        print("=" * 100)
        clean = [r for r in group if r["kind"] == "clean"]
        attacked = [r for r in group if r["kind"] == "attacked"]
        inj_as_user = [r for r in group if r["kind"] == "injection_as_user"]
        task_runs_all = clean + attacked
        denial_runs = [r for r in task_runs_all if r["denied"]]
        print(f"clean runs: utility {sum(bool(r['utility']) for r in clean)}/{len(clean)}")
        print(
            f"attacked runs: utility {sum(bool(r['utility']) for r in attacked)}/{len(attacked)}, "
            f"attack succeeded {sum(bool(r['security']) for r in attacked)}/{len(attacked)}"
        )
        print(
            f"runs with at least one denied call: {len(denial_runs)}/{len(task_runs_all)}; "
            f"of those, utility failed in {sum(not r['utility'] for r in denial_runs)}"
        )
        if inj_as_user:
            print(
                f"(injection goals run as plain user tasks, not part of the table above: {len(inj_as_user)} runs, "
                f"{sum(bool(r['denied']) for r in inj_as_user)} with a denied call)"
            )

        by_task: dict[str, list[dict]] = defaultdict(list)
        for run in task_runs_all:
            by_task[run["user_task"]].append(run)

        print("\nper user task:")
        for task in sorted(by_task, key=lambda t: int(t.split("_")[-1])):
            task_runs = by_task[task]
            ok = sum(bool(r["utility"]) for r in task_runs)
            denied_counts: dict[str, int] = defaultdict(int)
            for r in task_runs:
                for name in r["denied"]:
                    denied_counts[name] += 1
            query = task_runs[0]["query"]
            print(f"  {task}: utility {ok}/{len(task_runs)} | denied calls: {dict(denied_counts) or 'none'}")
            print(f"      query: {query[:110]}{'...' if len(query) > 110 else ''}")
            logged = decisions.get(query, [])
            if logged:
                allowed_sets = sorted({tuple(d["allowed_tools"]) for d in logged})
                print(f"      policy allowed (distinct sets over {len(logged)} decisions): {[list(s) for s in allowed_sets]}")
                if task in ideal:
                    missing = sorted(ideal[task] - set().union(*map(set, allowed_sets)))
                    print(f"      ideal tools never allowed: {missing or 'none'}")
                reasons = {d["reason"] for d in logged if d.get("reason")}
                if reasons:
                    print(f"      policy reason: {sorted(reasons)[0][:140]}")
            elif task in ideal:
                print(f"      ideal tools: {sorted(ideal[task])}")

        if args.verbose:
            print("\nevery run:")
            for r in sorted(task_runs_all, key=lambda r: (int(r["user_task"].split("_")[-1]), str(r["injection_task"]))):
                flags = f"utility={r['utility']}" + (
                    f" attack_success={r['security']}" if r["kind"] == "attacked" else ""
                )
                print(f"  {fmt_pair(r):<30} {flags}")
                print(f"      calls:  {r['calls']}")
                for name, call_arguments in r["call_args"]:
                    if name in show_args:
                        text = json.dumps(call_arguments, ensure_ascii=False)
                        print(f"      {name} args: {text[:400]}{'...' if len(text) > 400 else ''}")
                if r["denied"]:
                    print(f"      DENIED: {r['denied']}")
                if r["errors"]:
                    print(f"      errors: {r['errors'][:3]}")
        print()


if __name__ == "__main__":
    main()