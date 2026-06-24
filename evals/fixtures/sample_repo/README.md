# Sample Desktop Agent

This fixture represents a small desktop assistant runtime.

## Architecture

- `main.py` is the entry point.
- `app/agent.py` coordinates routing, planning, and execution.
- `app/router.py` selects the execution route.
- `app/planner.py` creates multi-step plans.
- `app/executor.py` executes registered tools.
- `app/tools/registry.py` creates the tool registry.