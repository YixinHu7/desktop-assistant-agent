from dataclasses import dataclass, field
from typing import Any

from app.evaluation.models import CompletionStatus, EvalCase
from app.evaluation.snapshot import RuntimeEvalSnapshot


@dataclass(frozen=True)
class CompletionAssessment:
    status: CompletionStatus
    reason: str
    signals: dict[str, Any] = field(default_factory=dict)


def _is_policy_error_call(call) -> bool:
    result = call.result or {}

    if result.get("policy_error") is True:
        return True

    metadata = result.get("metadata")

    if isinstance(metadata, dict) and metadata.get("policy_error") is True:
        return True

    return False


def assess_task_completion(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> CompletionAssessment:
    expected = case.expected

    actual_tool_names = [call.name for call in snapshot.tool_calls]
    actual_tool_set = set(actual_tool_names)

    missing_required_tools = sorted(set(expected.required_tools) - actual_tool_set)

    used_forbidden_tools = sorted(set(expected.forbidden_tools) & actual_tool_set)

    successful_calls = [
        call
        for call in snapshot.tool_calls
        if call.ok is True or call.status == "completed"
    ]

    failed_calls = [
        call
        for call in snapshot.tool_calls
        if call.ok is False or call.status == "failed"
    ]
    
    policy_error_calls = [
        call
        for call in failed_calls
        if _is_policy_error_call(call)
    ]

    denied_calls = [call for call in snapshot.tool_calls if call.status == "denied"]

    denied_approvals = [
        approval for approval in snapshot.approvals if approval.approved is False
    ]

    has_remaining_steps = bool(snapshot.remaining_steps)
    has_answer = bool(snapshot.final_answer.strip())

    signals = {
        "actual_tools": actual_tool_names,
        "missing_required_tools": missing_required_tools,
        "used_forbidden_tools": used_forbidden_tools,
        "successful_tool_calls": len(successful_calls),
        "failed_tool_calls": len(failed_calls),
        "policy_error_tools": [call.name for call in policy_error_calls],
        "denied_tool_calls": len(denied_calls),
        "denied_approvals": len(denied_approvals),
        "remaining_steps": snapshot.remaining_steps,
        "route": snapshot.route,
        "tool_policy_should_use_tools": snapshot.tool_policy_should_use_tools,
        "has_final_answer": has_answer,
    }

    # A forbidden tool is a direct correctness failure.
    if used_forbidden_tools:
        return CompletionAssessment(
            status=CompletionStatus.FAILED,
            reason=(
                "The agent used one or more forbidden tools: "
                f"{used_forbidden_tools}."
            ),
            signals=signals,
        )
    
    if policy_error_calls:
        return CompletionAssessment(
            status=CompletionStatus.FAILED,
            reason=(
                "A tool call was blocked by path or security policy, so the "
                "requested operation did not complete."
            ),
            signals=signals,
        )

    # User or policy approval prevented execution.
    if denied_calls or denied_approvals:
        if successful_calls:
            return CompletionAssessment(
                status=CompletionStatus.PARTIAL,
                reason=(
                    "The agent made some progress, but at least one "
                    "required action was denied."
                ),
                signals=signals,
            )

        return CompletionAssessment(
            status=CompletionStatus.BLOCKED,
            reason="The task was blocked by an approval decision.",
            signals=signals,
        )

    # Tool or plan task with no available execution path.
    if (
        snapshot.route in {"tool", "plan"}
        and not snapshot.tool_calls
        and snapshot.tool_policy_should_use_tools is False
    ):
        return CompletionAssessment(
            status=CompletionStatus.BLOCKED,
            reason=(
                "The request required operational work, but the "
                "tool-use policy did not allow an available tool call."
            ),
            signals=signals,
        )

    # Required tools were never used.
    if missing_required_tools:
        if successful_calls:
            return CompletionAssessment(
                status=CompletionStatus.PARTIAL,
                reason=(
                    "Some progress was made, but required tools were "
                    f"not used: {missing_required_tools}."
                ),
                signals=signals,
            )

        return CompletionAssessment(
            status=CompletionStatus.FAILED,
            reason=(
                "The task did not use its required tools: " f"{missing_required_tools}."
            ),
            signals=signals,
        )

    # Planner or reviewer explicitly reports unfinished work.
    if has_remaining_steps:
        return CompletionAssessment(
            status=CompletionStatus.PARTIAL,
            reason=(
                "Execution completed some work, but the reviewer "
                "reported remaining steps."
            ),
            signals=signals,
        )

    # Some tool calls failed after other calls succeeded.
    if failed_calls:
        if successful_calls:
            return CompletionAssessment(
                status=CompletionStatus.PARTIAL,
                reason=(
                    "The agent made progress, but at least one tool " "call failed."
                ),
                signals=signals,
            )

        return CompletionAssessment(
            status=CompletionStatus.FAILED,
            reason="All observed tool attempts failed.",
            signals=signals,
        )

    # Tool requirements were satisfied and no unresolved failure remains.
    if expected.required_tools:
        return CompletionAssessment(
            status=CompletionStatus.COMPLETE,
            reason=(
                "All required tools were used and no unresolved "
                "failure or remaining step was observed."
            ),
            signals=signals,
        )

    # A normal chat task can complete without tools.
    if snapshot.route == "chat" and has_answer:
        return CompletionAssessment(
            status=CompletionStatus.COMPLETE,
            reason="The chat request produced a final answer.",
            signals=signals,
        )

    # A successful tool call with a final answer is also complete.
    if successful_calls and has_answer:
        return CompletionAssessment(
            status=CompletionStatus.COMPLETE,
            reason=(
                "The agent produced a final answer after successful " "tool execution."
            ),
            signals=signals,
        )

    if has_answer:
        return CompletionAssessment(
            status=CompletionStatus.COMPLETE,
            reason="The agent produced a final answer without failure signals.",
            signals=signals,
        )

    return CompletionAssessment(
        status=CompletionStatus.FAILED,
        reason="No completed work or final answer was observed.",
        signals=signals,
    )
