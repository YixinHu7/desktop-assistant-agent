from typing import Any

from app.evaluation.models import (
    EvalCase,
    ToolArgumentExpectation,
)
from app.evaluation.results import (
    EvalCaseResult,
    EvalCheckResult,
    EvalCheckStatus,
)
from app.evaluation.snapshot import (
    ObservedToolCall,
    RuntimeEvalSnapshot,
)
from app.evaluation.completion import assess_task_completion


def _passed(
    name: str,
    message: str,
    details: dict[str, Any] | None = None,
    score: float = 1.0,
) -> EvalCheckResult:
    return EvalCheckResult(
        name=name,
        status=EvalCheckStatus.PASSED,
        score=score,
        message=message,
        details=details or {},
    )


def _failed(
    name: str,
    message: str,
    details: dict[str, Any] | None = None,
    score: float = 0.0,
) -> EvalCheckResult:
    return EvalCheckResult(
        name=name,
        status=EvalCheckStatus.FAILED,
        score=score,
        message=message,
        details=details or {},
    )


def _skipped(
    name: str,
    message: str,
) -> EvalCheckResult:
    return EvalCheckResult(
        name=name,
        status=EvalCheckStatus.SKIPPED,
        score=1.0,
        message=message,
        details={},
    )


def score_route(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected_route = case.expected.route

    if expected_route is None:
        return _skipped(
            name="route",
            message="No route expectation was defined.",
        )

    expected_value = expected_route.value

    if snapshot.route == expected_value:
        return _passed(
            name="route",
            message=f"Route matched: {expected_value}.",
            details={
                "expected": expected_value,
                "actual": snapshot.route,
            },
        )

    return _failed(
        name="route",
        message=(
            f"Expected route '{expected_value}', "
            f"but observed '{snapshot.route}'."
        ),
        details={
            "expected": expected_value,
            "actual": snapshot.route,
        },
    )


def score_skill_selection(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected_should_use = (
        case.expected.should_use_skill
    )
    expected_skill = case.expected.skill

    if (
        expected_should_use is None
        and expected_skill is None
    ):
        return _skipped(
            name="skill_selection",
            message="No skill expectation was defined.",
        )

    conditions: list[bool] = []
    failures: list[str] = []

    if expected_should_use is not None:
        matched = (
            snapshot.skill_used
            == expected_should_use
        )
        conditions.append(matched)

        if not matched:
            failures.append(
                "Expected should_use_skill="
                f"{expected_should_use}, observed "
                f"{snapshot.skill_used}."
            )

    if expected_skill is not None:
        matched = (
            snapshot.selected_skill
            == expected_skill
        )
        conditions.append(matched)

        if not matched:
            failures.append(
                f"Expected skill '{expected_skill}', "
                f"observed '{snapshot.selected_skill}'."
            )

    score = (
        sum(conditions) / len(conditions)
        if conditions
        else 1.0
    )

    details = {
        "expected_should_use_skill": expected_should_use,
        "actual_should_use_skill": snapshot.skill_used,
        "expected_skill": expected_skill,
        "actual_skill": snapshot.selected_skill,
    }

    if all(conditions):
        return _passed(
            name="skill_selection",
            message="Skill selection expectations passed.",
            details=details,
        )

    return _failed(
        name="skill_selection",
        message=" ".join(failures),
        details=details,
        score=score,
    )


def score_tool_selection(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected = case.expected

    has_expectation = any([
        expected.required_tools,
        expected.forbidden_tools,
        expected.minimum_tool_calls is not None,
        expected.maximum_tool_calls is not None,
    ])

    if not has_expectation:
        return _skipped(
            name="tool_selection",
            message="No tool selection expectation was defined.",
        )

    actual_names = [
        call.name
        for call in snapshot.tool_calls
    ]
    actual_name_set = set(actual_names)

    checks: list[bool] = []
    failures: list[str] = []

    missing_required = sorted(
        set(expected.required_tools)
        - actual_name_set
    )

    required_passed = not missing_required
    checks.append(required_passed)

    if missing_required:
        failures.append(
            f"Missing required tools: {missing_required}."
        )

    used_forbidden = sorted(
        set(expected.forbidden_tools)
        & actual_name_set
    )

    forbidden_passed = not used_forbidden
    checks.append(forbidden_passed)

    if used_forbidden:
        failures.append(
            f"Forbidden tools were used: {used_forbidden}."
        )

    tool_call_count = len(snapshot.tool_calls)

    if expected.minimum_tool_calls is not None:
        minimum_passed = (
            tool_call_count
            >= expected.minimum_tool_calls
        )
        checks.append(minimum_passed)

        if not minimum_passed:
            failures.append(
                f"Expected at least "
                f"{expected.minimum_tool_calls} tool calls, "
                f"observed {tool_call_count}."
            )

    if expected.maximum_tool_calls is not None:
        maximum_passed = (
            tool_call_count
            <= expected.maximum_tool_calls
        )
        checks.append(maximum_passed)

        if not maximum_passed:
            failures.append(
                f"Expected at most "
                f"{expected.maximum_tool_calls} tool calls, "
                f"observed {tool_call_count}."
            )

    score = (
        sum(checks) / len(checks)
        if checks
        else 1.0
    )

    details = {
        "required_tools": expected.required_tools,
        "forbidden_tools": expected.forbidden_tools,
        "actual_tools": actual_names,
        "missing_required_tools": missing_required,
        "used_forbidden_tools": used_forbidden,
        "tool_call_count": tool_call_count,
    }

    if all(checks):
        return _passed(
            name="tool_selection",
            message="All tool selection expectations passed.",
            details=details,
        )

    return _failed(
        name="tool_selection",
        message=" ".join(failures),
        details=details,
        score=score,
    )


def score_tool_arguments(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expectations = case.expected.tool_arguments

    if not expectations:
        return _skipped(
            name="tool_arguments",
            message="No tool argument expectations were defined.",
        )

    matched_expectations = 0
    failures: list[str] = []

    for expectation in expectations:
        matching_calls = [
            call
            for call in snapshot.tool_calls
            if call.name == expectation.tool
        ]

        if not matching_calls:
            failures.append(
                f"No call was recorded for tool "
                f"'{expectation.tool}'."
            )
            continue

        if any(
            _arguments_match(
                expectation=expectation,
                actual=call,
            )
            for call in matching_calls
        ):
            matched_expectations += 1
        else:
            failures.append(
                f"No '{expectation.tool}' call matched "
                f"the expected arguments."
            )

    score = (
        matched_expectations
        / len(expectations)
    )

    details = {
        "expected": [
            expectation.model_dump()
            for expectation in expectations
        ],
        "actual": [
            {
                "tool": call.name,
                "arguments": call.arguments,
            }
            for call in snapshot.tool_calls
        ],
        "matched_expectations": matched_expectations,
        "total_expectations": len(expectations),
    }

    if matched_expectations == len(expectations):
        return _passed(
            name="tool_arguments",
            message="All tool argument expectations passed.",
            details=details,
        )

    return _failed(
        name="tool_arguments",
        message=" ".join(failures),
        details=details,
        score=score,
    )


def _arguments_match(
    expectation: ToolArgumentExpectation,
    actual: ObservedToolCall,
) -> bool:
    if expectation.match == "exact":
        return actual.arguments == expectation.arguments

    return _is_subset(
        expected=expectation.arguments,
        actual=actual.arguments,
    )


def _is_subset(
    expected: Any,
    actual: Any,
) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False

        for key, expected_value in expected.items():
            if key not in actual:
                return False

            if not _is_subset(
                expected_value,
                actual[key],
            ):
                return False

        return True

    if isinstance(expected, list):
        return expected == actual

    return expected == actual


def score_approval(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected_tools = (
        case.expected.approval_required_tools
    )

    if not expected_tools:
        return _skipped(
            name="approval",
            message="No approval expectations were defined.",
        )

    approval_by_tool = {
        approval.tool: approval.approved
        for approval in snapshot.approvals
    }

    executed_tools = {
        call.name
        for call in snapshot.tool_calls
    }

    checks: list[bool] = []
    failures: list[str] = []

    for tool in expected_tools:
        if tool not in approval_by_tool:
            checks.append(False)
            failures.append(
                f"No approval decision was recorded "
                f"for '{tool}'."
            )
            continue

        approved = approval_by_tool[tool]

        if tool in executed_tools and approved is not True:
            checks.append(False)
            failures.append(
                f"Tool '{tool}' executed without an "
                f"approved decision."
            )
            continue

        checks.append(True)

    score = sum(checks) / len(checks)

    details = {
        "approval_required_tools": expected_tools,
        "observed_approvals": {
            approval.tool: approval.approved
            for approval in snapshot.approvals
        },
        "executed_tools": sorted(executed_tools),
    }

    if all(checks):
        return _passed(
            name="approval",
            message="Approval expectations passed.",
            details=details,
        )

    return _failed(
        name="approval",
        message=" ".join(failures),
        details=details,
        score=score,
    )


def score_recovery(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected = case.expected.recovery_expected

    if expected is None:
        return _skipped(
            name="recovery",
            message="No recovery expectation was defined.",
        )

    if snapshot.recovery_occurred == expected:
        return _passed(
            name="recovery",
            message=(
                "Recovery behavior matched the expectation."
            ),
            details={
                "expected": expected,
                "actual": snapshot.recovery_occurred,
            },
        )

    return _failed(
        name="recovery",
        message=(
            f"Expected recovery_occurred={expected}, "
            f"observed "
            f"{snapshot.recovery_occurred}."
        ),
        details={
            "expected": expected,
            "actual": snapshot.recovery_occurred,
        },
    )


def score_task_completion(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> EvalCheckResult:
    expected_status = case.expected.completion_status

    if expected_status is None:
        return _skipped(
            name="task_completion",
            message="No task completion expectation was defined.",
        )

    assessment = assess_task_completion(case, snapshot)

    details = {
        "expected": expected_status.value,
        "actual": assessment.status.value,
        "reason": assessment.reason,
        "signals": assessment.signals,
    }

    if assessment.status == expected_status:
        return _passed(
            name="task_completion",
            message=(
                "Task completion status matched: "
                f"{assessment.status.value}."
            ),
            details=details,
        )

    return _failed(
        name="task_completion",
        message=(
            f"Expected completion status '{expected_status.value}', "
            f"but observed '{assessment.status.value}'. "
            f"{assessment.reason}"
        ),
        details=details,
    )
    
    
def score_eval_case(
    case: EvalCase,
    run_summary: dict[str, Any],
) -> EvalCaseResult:
    snapshot = RuntimeEvalSnapshot.from_run_summary(
        run_summary
    )

    checks = [
        score_route(case, snapshot),
        score_skill_selection(case, snapshot),
        score_tool_selection(case, snapshot),
        score_tool_arguments(case, snapshot),
        score_approval(case, snapshot),
        score_recovery(case, snapshot),
        score_task_completion(case, snapshot),
    ]

    scored_checks = [
        check
        for check in checks
        if check.status != EvalCheckStatus.SKIPPED
    ]

    overall_score = (
        sum(check.score for check in scored_checks)
        / len(scored_checks)
        if scored_checks
        else 1.0
    )

    passed = all(
        check.status != EvalCheckStatus.FAILED
        for check in checks
    )

    return EvalCaseResult(
        case_id=case.id,
        suite=case.suite.value,
        passed=passed,
        score=overall_score,
        checks=checks,
    )