# Run Summary Inspector

The run summary inspector is a CLI tool for reading agent `run_summary` events from the trace log and rendering them as a human-readable execution report.

It is useful for debugging, demos, eval failures, and understanding how the agent made decisions during a run.

## What It Shows

The inspector prints:

- user input
- route decision
- memory decision
- tool-use policy decision
- selected skill
- original plan
- tool calls
- approval decisions
- recovery events
- execution review
- replan decision
- revised plan
- final answer

## Commands

Inspect the latest run:

```bash
PYTHONPATH=. make inspect-latest-run
```

Inspect a specific run:

```bash
PYTHONPATH=. make inspect-run RUN_ID=<run_id>
```

Call the script directly:

```bash
PYTHONPATH=. python scripts/inspect_run.py --latest
```

Inspect a specific trace file:

```bash
PYTHONPATH=. python scripts/inspect_run.py \
  --trace-path data/traces.jsonl \
  --latest
```

Limit printed final answer length:

```bash
PYTHONPATH=. python scripts/inspect_run.py \
  --latest \
  --max-answer-chars 800
```

Limit printed tool result length:

```bash
PYTHONPATH=. python scripts/inspect_run.py \
  --latest \
  --max-result-chars 400
```

## Example Output

```text
Run Summary
===========

Run ID: 2fd1d7f4-...
User input: Analyze this codebase structure and explain its architecture.

Decisions
---------
Route: plan
Route reason: Repository analysis requires planning and local file inspection.
Memory action: none
Tool policy should use tools: True
Tool policy likely tools: ['get_project_tree']
Tool policy avoid tools: ['open_app']
Requires grounding: True
Skill selected: repo_review
Skill should use: True

Plan
----
Goal: Analyze this repository architecture.

1. Inspect the project tree.
2. Read important files.
3. Summarize the architecture.

Tool Calls
----------
1. [completed] get_project_tree
   kind: primary
   ok: True
   source: local
   arguments: {"max_depth": 3, "path": "."}

Approvals
---------
1. get_project_tree required=False approved=True risk=low

Recovery
--------
None

Execution Review
----------------
completed_steps:
- Inspect the project tree.

remaining_steps:
- Read important files.

Replan Decision
---------------
should_replan: False
reason: No useful next action is available.

Final Answer
------------
This repository is a desktop assistant agent runtime...
```

## Why This Exists

The trace log is written as JSONL and is optimized for machines. The inspector gives a compact human-readable view of one run.

This is especially useful when debugging questions like:

- Did the router choose the right route?
- Did the skill selector choose the expected skill?
- Did the tool-use policy allow tool calls?
- Which tools were called?
- Were approvals required?
- Did recovery happen?
- Did the reviewer mark remaining steps?
- Was replanning triggered?
- Did the final answer reflect the actual tool results?

## Relationship to Eval Reports

Eval failure reports show why an eval case failed.

The run summary inspector shows what happened during a specific agent run.

Use both together:

```bash
PYTHONPATH=. make eval-case-report CASE=skill_repo_review_001
PYTHONPATH=. make inspect-latest-run
```

## Relationship to Metrics

The metrics report aggregates many runs:

```bash
PYTHONPATH=. make metrics
```

The run summary inspector explains one run in detail:

```bash
PYTHONPATH=. make inspect-latest-run
```

## Key Files

| File | Purpose |
| --- | --- |
| `scripts/inspect_run.py` | CLI inspector |
| `app/run_context.py` | Source of the run summary contract |
| `data/traces.jsonl` | Runtime trace log |
| `tests/evaluation/test_inspect_run.py` | Inspector behavior tests |
| `tests/evaluation/test_run_summary_contract.py` | Run summary schema contract tests |