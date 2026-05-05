import json
from pathlib import Path
from statistics import mean
from app.config import config


TRACE_PATH = Path(config.trace_path)


def load_run_metrics(trace_path: Path):
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")

    metrics = []

    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("event_type") == "run_metrics":
                metrics.append(event.get("payload", {}))

    return metrics


def safe_mean(values):
    values = [v for v in values if v is not None]

    if not values:
        return None

    return mean(values)


def format_percent(value):
    if value is None:
        return "N/A"

    return f"{value * 100:.1f}%"


def main():
    metrics = load_run_metrics(TRACE_PATH)

    if not metrics:
        print("No run_metrics events found.")
        return

    total_runs = len(metrics)

    routes = {}
    for item in metrics:
        route = item.get("route") or "unknown"
        routes[route] = routes.get(route, 0) + 1

    tool_using_runs = sum(
        1 for item in metrics
        if item.get("total_tool_calls", 0) > 0
    )

    total_tool_calls = sum(
        item.get("total_tool_calls", 0)
        for item in metrics
    )

    successful_tool_calls = sum(
        item.get("successful_tool_calls", 0)
        for item in metrics
    )

    failed_tool_calls = sum(
        item.get("failed_tool_calls", 0)
        for item in metrics
    )

    average_tool_success_rate = safe_mean(
        item.get("tool_success_rate")
        for item in metrics
    )

    recovery_attempted = sum(
        1 for item in metrics
        if item.get("recovery_attempted")
    )

    recovery_succeeded = sum(
        1 for item in metrics
        if item.get("recovery_succeeded")
    )

    replan_considered = sum(
        1 for item in metrics
        if item.get("replan_considered")
    )

    replan_triggered = sum(
        1 for item in metrics
        if item.get("replan_triggered")
    )

    possible_failures = sum(
        1 for item in metrics
        if item.get("has_possible_failure")
    )

    grounding_required = sum(
        1 for item in metrics
        if item.get("tool_policy_requires_grounding")
    )

    print("\n=== Agent Runtime Metrics Report ===\n")

    print(f"Total runs: {total_runs}")
    print(f"Tool-using runs: {tool_using_runs}")
    print(f"Grounding-required runs: {grounding_required}")
    print()

    print("Routes:")
    for route, count in sorted(routes.items()):
        print(f"  - {route}: {count}")

    print()

    print("Tool Calls:")
    print(f"  - Total tool calls: {total_tool_calls}")
    print(f"  - Successful tool calls: {successful_tool_calls}")
    print(f"  - Failed tool calls: {failed_tool_calls}")
    print(f"  - Average per-run tool success rate: {format_percent(average_tool_success_rate)}")

    print()

    print("Recovery:")
    print(f"  - Recovery attempted runs: {recovery_attempted}")
    print(f"  - Recovery succeeded runs: {recovery_succeeded}")

    print()

    print("Replanning:")
    print(f"  - Replan considered runs: {replan_considered}")
    print(f"  - Replan triggered runs: {replan_triggered}")

    print()

    print("Quality Signals:")
    print(f"  - Possible failure runs: {possible_failures}")

    print("\n====================================\n")


if __name__ == "__main__":
    main()