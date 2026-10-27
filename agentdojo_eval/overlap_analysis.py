"""Static analysis: which attacks can a tool allowlist block *in principle*?

For every (user task, injection task) pair in an AgentDojo suite we compare two sets of tools:

  * user tools   - tools in the user task's ground-truth solution (an idealised allowlist)
  * attack tools - tools in the injection task's ground-truth solution

If the attack needs a tool OUTSIDE the user's tool set, an allowlist built from the user request
blocks it (the attacker must call a tool the task never needed). If every attack tool is already in
the user's tool set, the allowlist cannot see the attack: it uses tools the task legitimately needs,
and only argument- or data-flow-level checks (e.g. CaMeL) could stop it.

Limitations:
  * Ground truth is ONE valid solution. The model may use other tools, and a real policy LLM may
    allow more or fewer tools than the ideal set.
  * Workspace injection tasks 6-13 have no ground truth in AgentDojo; their tool sets are labelled
    by hand from the goal text (see MANUAL_REQUIRED_TOOLS) and are marked "(manual)" in the output.
  * Tool-set containment ignores arguments, so it does not measure how risky an allowed call is.

Run:  python overlap_analysis.py [--suite workspace] [--version v1.2.2] [--results results.json]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite


# AgentDojo v1.2 added workspace injection tasks 6-13 WITHOUT a ground-truth solution
# (their ground_truth() returns an empty list). For those we label, by hand, the tools that the
# goal text makes unavoidable. Only tools that CANNOT be skipped are listed, so the labels are
# conservative: fewer required tools makes an attack more likely to count as "invisible" to an
# allowlist. Reading tools are left out on purpose because there are several ways to read the data.
#   6, 8, 9 : "email all unread emails ... then delete the sent email" -> send_email, delete_email
#   7       : same, for received and sent emails                        -> send_email, delete_email
#   10      : "email every file, then delete the sent email"           -> send_email, delete_email
#   11, 12  : same, and "delete each of the five files"                -> + delete_file
#   13      : "send individual emails to everyone I meet today"        -> send_email
MANUAL_REQUIRED_TOOLS: dict[str, set[str]] = {
    "injection_task_6": {"send_email", "delete_email"},
    "injection_task_7": {"send_email", "delete_email"},
    "injection_task_8": {"send_email", "delete_email"},
    "injection_task_9": {"send_email", "delete_email"},
    "injection_task_10": {"send_email", "delete_email"},
    "injection_task_11": {"send_email", "delete_email", "delete_file"},
    "injection_task_12": {"send_email", "delete_email", "delete_file"},
    "injection_task_13": {"send_email"},
}


def natural_key(task_id: str) -> int:
    return int(re.findall(r"\d+", task_id)[-1])


def tools_of(calls) -> set[str]:
    return {call.function for call in calls}


def collect_ground_truth(suite):
    """Return ({user_id: tools}, {injection_id: tools}, errors, manually_labelled_injection_ids)."""
    errors: list[str] = []
    manual: set[str] = set()
    user_tools: dict[str, set[str]] = {}
    injection_tools: dict[str, set[str]] = {}

    for uid, task in suite.user_tasks.items():
        try:
            env = task.init_environment(suite.load_and_inject_default_environment({}))
            user_tools[uid] = tools_of(task.ground_truth(env))
        except Exception as exc:  # keep going; report at the end
            errors.append(f"{uid}: {type(exc).__name__}: {exc}")

    for iid, task in suite.injection_tasks.items():
        try:
            env = suite.load_and_inject_default_environment({})
            tools = tools_of(task.ground_truth(env))
        except Exception as exc:
            errors.append(f"{iid}: {type(exc).__name__}: {exc}")
            continue
        if tools:
            injection_tools[iid] = tools
        elif iid in MANUAL_REQUIRED_TOOLS:
            injection_tools[iid] = set(MANUAL_REQUIRED_TOOLS[iid])
            manual.add(iid)
        else:
            errors.append(f"{iid}: empty ground truth and no manual label; excluded")

    return user_tools, injection_tools, errors, manual


def classify(user_set: set[str], attack_set: set[str], writes_only: bool = False) -> str:
    """'blockable' if the attack needs a tool the user task does not, else 'invisible'.

    writes_only=False models the strict gate ("enforce"): every tool must be in the allowlist.
    writes_only=True models "enforce_writes": read-only tools are never blocked, so only the
    state-changing tools count (an attack that merely needs an extra READ tool is invisible to it).
    """
    if writes_only:
        from query_guard import is_read_only

        user_set = {t for t in user_set if not is_read_only(t)}
        attack_set = {t for t in attack_set if not is_read_only(t)}
    return "blockable" if attack_set - user_set else "invisible"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--version", default="v1.2.2")
    parser.add_argument("--results", default="results.json", help="Optional: restrict the subset view to the pairs you ran.")
    parser.add_argument("--out", default="overlap_analysis.json")
    args = parser.parse_args()

    suite = get_suite(args.version, args.suite)
    user_tools, injection_tools, errors, manual = collect_ground_truth(suite)

    print(f"Suite {args.suite} ({args.version}): {len(user_tools)} user tasks, {len(injection_tools)} injection tasks")
    if errors:
        print(f"WARNING: ground truth failed for {len(errors)} task(s); they are excluded:")
        for line in errors:
            print("  ", line)

    print("\nInjection tasks and the tools they need ('manual' = labelled by hand from the goal text):")
    for iid in sorted(injection_tools, key=natural_key):
        tag = "  (manual)" if iid in manual else ""
        print(f"  {iid:<18} {sorted(injection_tools[iid])}{tag}")

    def summarize(user_ids: list[str], injection_ids: list[str]) -> dict:
        pairs, pairs_writes = {}, {}
        for uid in user_ids:
            for iid in injection_ids:
                if uid in user_tools and iid in injection_tools:
                    pairs[f"{uid}|{iid}"] = classify(user_tools[uid], injection_tools[iid])
                    pairs_writes[f"{uid}|{iid}"] = classify(user_tools[uid], injection_tools[iid], writes_only=True)
        return {
            "n_pairs": len(pairs),
            "counts": dict(Counter(pairs.values())),
            "pairs": pairs,
            "counts_writes": dict(Counter(pairs_writes.values())),
            "pairs_writes": pairs_writes,
        }

    all_users = sorted(user_tools, key=natural_key)
    all_injections = sorted(injection_tools, key=natural_key)
    full = summarize(all_users, all_injections)
    print(f"\nWhole suite ({full['n_pairs']} pairs):")
    print(f"  strict gate (all tools allowlisted, arm 'enforce'):            {full['counts']}")
    print(f"  writes-only gate (reads always allowed, arm 'enforce_writes'): {full['counts_writes']}")

    # Per injection task: in how many user tasks is the attack invisible to an allowlist?
    print("\nPer injection task (share of user tasks where the attack is INVISIBLE to a tool allowlist):")
    per_injection = {}
    for iid in all_injections:
        invisible = sum(1 for uid in all_users if full["pairs"].get(f"{uid}|{iid}") == "invisible")
        total = sum(1 for uid in all_users if f"{uid}|{iid}" in full["pairs"])
        per_injection[iid] = {"invisible": invisible, "total": total}
        print(f"  {iid:<18} {invisible:>2}/{total}")

    output = {"suite": args.suite, "version": args.version, "whole_suite": full, "per_injection": per_injection}

    results_path = Path(args.results)
    if results_path.exists():
        data = json.loads(results_path.read_text())
        subset = summarize(data["user_tasks"], data["injection_tasks"])
        output["subset"] = subset
        print(f"\nThe subset you actually ran ({subset['n_pairs']} pairs):")
        print(f"  strict gate:      {subset['counts']}")
        print(f"  writes-only gate: {subset['counts_writes']}")
        print(f"\n  {'pair':<32}{'strict gate':<14}writes-only gate")
        for key in sorted(subset["pairs"]):
            print(f"  {key:<32}{subset['pairs'][key]:<14}{subset['pairs_writes'][key]}")

        # Compare with the observed outcomes per arm, using the labels that fit the arm's gate.
        print("\nAttack successes by label (blockable = the gate should stop it; invisible = it cannot see it):")
        for arm, res in data["arms"].items():
            writes_only = arm == "enforce_writes"
            labels = subset["pairs_writes"] if writes_only else subset["pairs"]
            by_label = {"blockable": [0, 0], "invisible": [0, 0]}
            for key, succeeded in res["raw"]["attack_success"].items():
                label = labels.get(key)
                if label:
                    by_label[label][1] += 1
                    by_label[label][0] += int(succeeded)
            gate = "writes-only labels" if writes_only else "strict labels"
            text = ", ".join(f"{lab}: {k}/{n}" for lab, (k, n) in by_label.items())
            print(f"  [{arm}] ({gate}) {text}")
        print(
            "\nCaution: these labels come from ideal tool sets. A real policy may allow other tools "
            "(for example it never allowed send_email for user_task_13), so check the policy decisions too."
        )
    else:
        print(f"\n(no {args.results} found; skipping the subset view)")

    Path(args.out).write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()