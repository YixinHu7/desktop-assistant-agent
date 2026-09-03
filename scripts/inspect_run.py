import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect agent run_summary events from a trace JSONL file."
    )

    parser.add_argument(
        "--trace-path",
        default=config.trace_path,
        help="Path to trace JSONL file.",
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Inspect the latest run_summary event.",
    )

    parser.add_argument(
        "--run-id",
        default=None,
        help="Inspect a specific run_id.",
    )

    parser.add_argument(
        "--max-answer-chars",
        type=int,
        default=1600,
        help="Maximum characters of final answer to print.",
    )

    parser.add_argument(
        "--max-result-chars",
        type=int,
        default=700,
        help="Maximum characters of tool result/error JSON to print.",
    )

    return parser.parse_args()


def load_run_summaries(trace_path: str | Path) -> list[dict[str, Any]]:
    path = Path(trace_path)

    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")

    summaries = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("event_type") == "run_summary":
                payload = event.get("payload", {})

                if isinstance(payload, dict):
                    summaries.append(payload)

            elif "run_id" in event and "final_answer" in event:
                summaries.append(event)

    return summaries


def select_run(
    summaries: list[dict[str, Any]],
    run_id: str | None = None,
) -> dict[str, Any]:
    if not summaries:
        raise ValueError("No run_summary events found.")

    if run_id is None:
        return summaries[-1]

    for summary in summaries:
        if summary.get("run_id") == run_id:
            return summary

    raise ValueError(f"Run ID not found: {run_id}")


def render_run_summary(
    run: dict[str, Any],
    max_answer_chars: int = 1600,
    max_result_chars: int = 700,
) -> str:
    lines = []

    lines.extend(_render_header(run))
    lines.extend(_render_decisions(run))
    lines.extend(_render_plan("Plan", run.get("plan")))
    lines.extend(_render_tool_calls(run, max_result_chars=max_result_chars))
    lines.extend(_render_approvals(run))
    lines.extend(_render_recovery(run))
    lines.extend(_render_review(run))
    lines.extend(_render_plan("Revised Plan", run.get("revised_plan")))
    lines.extend(_render_replan_decision(run))
    lines.extend(_render_final_answer(run, max_chars=max_answer_chars))

    return "\n".join(lines).rstrip() + "\n"


def _render_header(run: dict[str, Any]) -> list[str]:
    return [
        "Run Summary",
        "===========",
        "",
        f"Run ID: {run.get('run_id', 'unknown')}",
        f"User input: {_single_line(run.get('user_input', ''))}",
        "",
    ]


def _render_decisions(run: dict[str, Any]) -> list[str]:
    route = _as_dict(run.get("route_decision"))
    memory = _as_dict(run.get("memory_decision"))
    tool_policy = _as_dict(run.get("tool_use_decision"))
    skill = _as_dict(run.get("skill_decision"))

    lines = [
        "Decisions",
        "---------",
        f"Route: {route.get('route', 'unknown')}",
        f"Route reason: {_single_line(route.get('reason', ''))}",
        f"Memory action: {memory.get('action', 'unknown')}",
        f"Tool policy should use tools: {tool_policy.get('should_use_tools', 'unknown')}",
        f"Tool policy likely tools: {tool_policy.get('likely_tools', [])}",
        f"Tool policy avoid tools: {tool_policy.get('avoid_tools', [])}",
        f"Requires grounding: {tool_policy.get('requires_grounding', 'unknown')}",
        f"Skill selected: {run.get('selected_skill') or skill.get('selected_skill') or 'none'}",
        f"Skill should use: {skill.get('should_use_skill', 'unknown')}",
        "",
    ]

    return lines


def _render_plan(title: str, plan: Any) -> list[str]:
    plan = _as_dict(plan)

    if not plan:
        return []

    goal = plan.get("goal") or plan.get("revised_goal") or "unknown"
    steps = plan.get("steps", [])

    lines = [
        title,
        "-" * len(title),
        f"Goal: {goal}",
        "",
    ]

    if not steps:
        lines.append("No steps recorded.")
        lines.append("")
        return lines

    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {_step_text(step)}")

    lines.append("")
    return lines


def _render_tool_calls(
    run: dict[str, Any],
    max_result_chars: int,
) -> list[str]:
    calls = run.get("tool_calls", [])

    if not isinstance(calls, list) or not calls:
        return [
            "Tool Calls",
            "----------",
            "None",
            "",
        ]

    lines = [
        "Tool Calls",
        "----------",
    ]

    for index, call in enumerate(calls, start=1):
        if not isinstance(call, dict):
            continue

        tool_name = call.get("tool") or call.get("tool_name") or "unknown"
        status = call.get("status", "unknown")
        ok = call.get("ok", "unknown")
        kind = call.get("kind", "primary")
        source = call.get("source", "unknown")

        lines.append(f"{index}. [{status}] {tool_name}")
        lines.append(f"   kind: {kind}")
        lines.append(f"   ok: {ok}")
        lines.append(f"   source: {source}")

        if call.get("recovery_for"):
            lines.append(f"   recovery_for: {call.get('recovery_for')}")

        if call.get("requires_approval") is not None:
            lines.append(f"   requires_approval: {call.get('requires_approval')}")

        if call.get("risk_level") is not None:
            lines.append(f"   risk_level: {call.get('risk_level')}")

        mcp = call.get("mcp")
        if isinstance(mcp, dict):
            lines.append(f"   mcp.provider: {mcp.get('provider')}")
            lines.append(f"   mcp.server: {mcp.get('server')}")
            lines.append(f"   mcp.original_tool: {mcp.get('original_tool')}")
            lines.append(f"   mcp.exposed_tool: {mcp.get('exposed_tool')}")

        arguments = call.get("arguments", {})
        lines.append(f"   arguments: {_json_inline(arguments)}")

        result = _as_dict(call.get("result"))
        error = result.get("error")

        if error:
            lines.append(f"   error: {_single_line(error)}")

        if result:
            lines.append("   result:")
            lines.append(_indent(_json_block(result, max_chars=max_result_chars), "     "))

        lines.append("")

    return lines


def _render_approvals(run: dict[str, Any]) -> list[str]:
    approvals = run.get("approval_decisions", [])

    if not isinstance(approvals, list) or not approvals:
        return [
            "Approvals",
            "---------",
            "None",
            "",
        ]

    lines = [
        "Approvals",
        "---------",
    ]

    for index, approval in enumerate(approvals, start=1):
        if not isinstance(approval, dict):
            continue

        lines.append(
            f"{index}. {approval.get('tool', 'unknown')} "
            f"required={approval.get('required')} "
            f"approved={approval.get('approved')} "
            f"risk={approval.get('risk_level')}"
        )
        lines.append(f"   reason: {_single_line(approval.get('reason', ''))}")

    lines.append("")
    return lines


def _render_recovery(run: dict[str, Any]) -> list[str]:
    events = run.get("recovery_events", [])

    if not isinstance(events, list) or not events:
        return [
            "Recovery",
            "--------",
            "None",
            "",
        ]

    lines = [
        "Recovery",
        "--------",
    ]

    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            continue

        lines.append(f"{index}. type={event.get('type', 'unknown')}")
        lines.append(f"   original_tool: {event.get('original_tool')}")
        lines.append(f"   retry_tool: {event.get('retry_tool')}")

        if event.get("success") is not None:
            lines.append(f"   success: {event.get('success')}")

        if event.get("reason"):
            lines.append(f"   reason: {_single_line(event.get('reason'))}")

    lines.append("")
    return lines


def _render_review(run: dict[str, Any]) -> list[str]:
    review = _as_dict(run.get("step_review"))

    if not review:
        return [
            "Execution Review",
            "----------------",
            "None",
            "",
        ]

    lines = [
        "Execution Review",
        "----------------",
    ]

    for key in ["completed_steps", "failed_steps", "skipped_steps", "remaining_steps"]:
        values = review.get(key, [])
        lines.append(f"{key}:")
        lines.extend(_bullet_list(values))
        lines.append("")

    if review.get("summary"):
        lines.append(f"summary: {_single_line(review.get('summary'))}")
        lines.append("")

    return lines


def _render_replan_decision(run: dict[str, Any]) -> list[str]:
    decision = _as_dict(run.get("replan_decision"))

    if not decision:
        return [
            "Replan Decision",
            "---------------",
            "None",
            "",
        ]

    lines = [
        "Replan Decision",
        "---------------",
        f"should_replan: {decision.get('should_replan')}",
        f"reason: {_single_line(decision.get('reason', ''))}",
        "",
    ]

    next_steps = decision.get("next_steps", [])

    if next_steps:
        lines.append("next_steps:")
        lines.extend(_bullet_list(next_steps))
        lines.append("")

    return lines


def _render_final_answer(
    run: dict[str, Any],
    max_chars: int,
) -> list[str]:
    answer = str(run.get("final_answer", "")).strip()

    if not answer:
        answer = "No final answer recorded."

    return [
        "Final Answer",
        "------------",
        _truncate(answer, max_chars),
        "",
    ]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _step_text(step: Any) -> str:
    if isinstance(step, dict):
        return str(step.get("step") or step.get("description") or step)

    return str(step)


def _bullet_list(values: Any) -> list[str]:
    if not values:
        return ["- None"]

    if not isinstance(values, list):
        return [f"- {_step_text(values)}"]

    return [f"- {_step_text(value)}" for value in values]


def _single_line(value: Any, max_chars: int = 240) -> str:
    text = str(value or "").strip().replace("\n", " ")

    return _truncate(text, max_chars)


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "... [truncated]"


def _json_inline(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _json_block(value: Any, max_chars: int) -> str:
    try:
        text = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)

    return _truncate(text, max_chars)


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def main() -> int:
    args = parse_args()

    try:
        summaries = load_run_summaries(args.trace_path)
        run = select_run(summaries, run_id=args.run_id)

    except Exception as exc:
        print(f"Unable to inspect run: {exc}")
        return 1

    print(
        render_run_summary(
            run,
            max_answer_chars=args.max_answer_chars,
            max_result_chars=args.max_result_chars,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())