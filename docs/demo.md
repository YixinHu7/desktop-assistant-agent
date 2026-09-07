# Demo Workflow

This project includes a safe repository review demo workflow.

The demo runs the agent against a fixture repository, asks it to analyze the codebase architecture, and then prints both the final answer and the run summary inspector output.

## Command

```bash
PYTHONPATH=. make demo-repo-review
```

Equivalent direct command:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py
```

## What the Demo Shows

The demo demonstrates the main runtime loop:

```text
Prompt
  ↓
Memory policy
  ↓
Routing
  ↓
Tool-use policy
  ↓
Skill selection
  ↓
Planning
  ↓
Tool execution
  ↓
Execution review
  ↓
Replanning decision
  ↓
Final answer
  ↓
Run summary inspector
```

## Default Prompt

```text
Analyze this codebase structure and explain its architecture.
```

## Safety Defaults

The demo uses safe defaults:

```text
EVAL_MODE=true
EVAL_ALLOW_REAL_SIDE_EFFECTS=false
EVAL_FIXTURE_ROOT=evals/fixtures/sample_repo
DATA_DIR=data/demo
ENABLE_MCP_TOOLS=false
ENABLE_REAL_MCP_TOOLS=false
ENABLE_MOCK_MCP_TOOLS=false
```

This keeps the demo focused on local repository review and prevents accidental real side effects.

## Useful Variants

Run without inspector output:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py --no-inspect
```

Use a custom prompt:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py \
  --prompt "Review this repository and summarize the runtime architecture."
```

Use a custom fixture repository:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py \
  --fixture-root evals/fixtures/sample_repo
```

Limit inspector output:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py \
  --max-answer-chars 1000 \
  --max-result-chars 500
```

## Expected Output

The demo prints:

```text
Demo Workflow
=============

Fixture root: ...
Data dir: ...
Prompt: ...

Final Answer
------------

...

Inspector Output
----------------

Run Summary
===========
...
```

The inspector output includes route, skill, plan, tool calls, approval decisions, recovery events, execution review, replan decision, and final answer.

## When to Use This

Use this demo before showing the project, after major runtime changes, or before updating resume/project documentation.

Recommended final check:

```bash
PYTHONPATH=. make check
PYTHONPATH=. make eval-all
PYTHONPATH=. make demo-repo-review
```
