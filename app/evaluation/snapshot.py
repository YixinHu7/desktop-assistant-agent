from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ObservedToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservedApproval:
    tool: str
    approved: Optional[bool]


@dataclass(frozen=True)
class RuntimeEvalSnapshot:
    route: Optional[str]
    skill_used: Optional[bool]
    selected_skill: Optional[str]

    tool_calls: list[ObservedToolCall]
    approvals: list[ObservedApproval]

    recovery_occurred: bool
    final_answer: str

    @classmethod
    def from_run_summary(
        cls,
        run_summary: dict[str, Any],
    ) -> "RuntimeEvalSnapshot":
        route_decision = (
            run_summary.get("route_decision")
            or {}
        )

        skill_decision = (
            run_summary.get("skill_decision")
            or {}
        )

        route = (
            route_decision.get("route")
            or run_summary.get("route")
        )

        selected_skill = (
            run_summary.get("selected_skill")
            or skill_decision.get("selected_skill")
        )

        should_use_skill = skill_decision.get(
            "should_use_skill"
        )

        if should_use_skill is None:
            skill_used = (
                bool(selected_skill)
                if selected_skill is not None
                else None
            )
        else:
            skill_used = bool(should_use_skill)

        return cls(
            route=route,
            skill_used=skill_used,
            selected_skill=selected_skill,
            tool_calls=_extract_tool_calls(run_summary),
            approvals=_extract_approvals(run_summary),
            recovery_occurred=_extract_recovery_status(
                run_summary
            ),
            final_answer=str(
                run_summary.get("final_answer") or ""
            ),
        )


def _extract_tool_calls(
    run_summary: dict[str, Any],
) -> list[ObservedToolCall]:
    raw_calls = run_summary.get("tool_calls")

    if raw_calls is None:
        raw_calls = run_summary.get("used_tools", [])

    if not isinstance(raw_calls, list):
        return []

    calls: list[ObservedToolCall] = []

    for item in raw_calls:
        if isinstance(item, str):
            calls.append(
                ObservedToolCall(
                    name=item,
                    arguments={},
                )
            )
            continue

        if not isinstance(item, dict):
            continue

        name = (
            item.get("name")
            or item.get("tool")
            or item.get("tool_name")
        )

        if not name:
            continue

        arguments = (
            item.get("arguments")
            or item.get("args")
            or {}
        )

        if not isinstance(arguments, dict):
            arguments = {}

        calls.append(
            ObservedToolCall(
                name=str(name),
                arguments=arguments,
            )
        )

    return calls


def _extract_approvals(
    run_summary: dict[str, Any],
) -> list[ObservedApproval]:
    raw_approvals = (
        run_summary.get("approval_decisions")
        or run_summary.get("approvals")
        or []
    )

    if isinstance(raw_approvals, dict):
        raw_approvals = [raw_approvals]

    if not isinstance(raw_approvals, list):
        return []

    approvals: list[ObservedApproval] = []

    for item in raw_approvals:
        if not isinstance(item, dict):
            continue

        tool = (
            item.get("tool")
            or item.get("tool_name")
            or item.get("name")
        )

        if not tool:
            continue

        approved = _normalize_approval_value(
            item.get(
                "approved",
                item.get("decision"),
            )
        )

        approvals.append(
            ObservedApproval(
                tool=str(tool),
                approved=approved,
            )
        )

    return approvals


def _normalize_approval_value(
    value: Any,
) -> Optional[bool]:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "approved",
            "approve",
            "accepted",
            "yes",
            "true",
        }:
            return True

        if normalized in {
            "denied",
            "deny",
            "rejected",
            "no",
            "false",
        }:
            return False

    return None


def _extract_recovery_status(
    run_summary: dict[str, Any],
) -> bool:
    explicit = run_summary.get("recovery_occurred")

    if isinstance(explicit, bool):
        return explicit

    recovery_used = run_summary.get("recovery_used")

    if isinstance(recovery_used, bool):
        return recovery_used

    for key in (
        "recovery_attempts",
        "recovery_actions",
        "recoveries",
    ):
        value = run_summary.get(key)

        if isinstance(value, (list, dict, str)):
            if bool(value):
                return True

    recovery = run_summary.get("recovery")

    if isinstance(recovery, dict):
        return bool(
            recovery.get("attempted")
            or recovery.get("used")
            or recovery.get("actions")
        )

    return False