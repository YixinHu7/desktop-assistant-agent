from typing import Any, Dict


def compute_run_metrics(run_summary: Dict[str, Any]) -> Dict[str, Any]:
    tool_calls = run_summary.get("tool_calls", [])
    recovery_events = run_summary.get("recovery_events", [])

    total_tool_calls = len(tool_calls)

    successful_tool_calls = 0
    failed_tool_calls = 0

    for call in tool_calls:
        result = call.get("result", {})
        if result.get("ok") is True:
            successful_tool_calls += 1
        elif result.get("ok") is False:
            failed_tool_calls += 1

    recovery_attempted = any(
        event.get("type") == "attempt" for event in recovery_events
    )

    recovery_succeeded = any(
        event.get("type") == "result"
        and event.get("retry_result", {}).get("ok") is True
        for event in recovery_events
    )

    route_decision = run_summary.get("route_decision") or {}
    tool_use_decision = run_summary.get("tool_use_decision") or {}
    replan_decision = run_summary.get("replan_decision") or {}

    final_answer = run_summary.get("final_answer") or ""

    return {
        "run_id": run_summary.get("run_id"),
        "route": route_decision.get("route"),
        "used_plan": run_summary.get("plan") is not None,
        "used_revised_plan": run_summary.get("revised_plan") is not None,

        "tool_policy_should_use_tools": tool_use_decision.get("should_use_tools"),
        "tool_policy_requires_grounding": tool_use_decision.get("requires_grounding"),

        "total_tool_calls": total_tool_calls,
        "successful_tool_calls": successful_tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "tool_success_rate": (
            successful_tool_calls / total_tool_calls
            if total_tool_calls > 0 else None
        ),

        "recovery_attempted": recovery_attempted,
        "recovery_succeeded": recovery_succeeded,

        "replan_considered": replan_decision != {},
        "replan_triggered": replan_decision.get("should_replan", False),

        "final_answer_length": len(final_answer),
        "has_possible_failure": (
            failed_tool_calls > 0
            or recovery_attempted
            or "could not" in final_answer.lower()
            or "failed" in final_answer.lower()
        ),
    }