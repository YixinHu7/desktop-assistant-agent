# Eval Developer Guide

This project includes an end-to-end evaluation system for testing the desktop assistant runtime.

The eval system checks routing, skill selection, tool selection, tool arguments, approval behavior, recovery behavior, task completion, answer requirements, grounding, MCP telemetry, and optional LLM judge quality.

## Eval Architecture

```text
evals/cases/*.jsonl
   ↓
scripts/run_evals.py
   ↓
scripts/eval_worker.py
   ↓
DesktopAssistantAgent
   ↓
run_summary
   ↓
RuntimeEvalSnapshot
   ↓
scorers
   ↓
EvalRunReport
   ↓
failure report
```

Each eval case runs in an isolated temporary workspace. The worker configures eval-specific environment variables before importing the agent runtime.

## Eval Case Files

Eval cases live in:

```text
evals/cases/
```

Each JSONL file contains one eval case per line.

Current suites include:

```text
routing
skills
tools
recovery
regression
mcp
```

A typical case looks like:

```json
{
  "id": "skill_repo_review_001",
  "suite": "skills",
  "description": "Repository analysis should select the repo review skill.",
  "input": "Analyze this codebase structure and explain its architecture.",
  "tags": ["skill", "repo-review"],
  "environment": {
    "fixture_root": "evals/fixtures/sample_repo"
  },
  "expected": {
    "should_use_skill": true,
    "skill": "repo_review",
    "required_tools": ["get_project_tree"],
    "optional_tools": ["read_multiple_files", "search_files"],
    "forbidden_tools": ["open_app"],
    "answer": {
      "contains_any": [
        "architecture",
        "structure",
        "components",
        "runtime",
        "entry point",
        "main components"
      ],
      "min_characters": 120
    }
  }
}
```

## Running Evals

Run all evals:

```bash
PYTHONPATH=. make eval-all
```

Run one suite:

```bash
PYTHONPATH=. make eval-routing
PYTHONPATH=. make eval-skills
PYTHONPATH=. make eval-tools
PYTHONPATH=. make eval-recovery
PYTHONPATH=. make eval-regression
PYTHONPATH=. make eval-mcp
```

Run one case:

```bash
PYTHONPATH=. make eval-case CASE=skill_repo_review_001
```

Run one case with a failure report:

```bash
PYTHONPATH=. make eval-case-report CASE=skill_repo_review_001
```

Run all evaluation unit tests:

```bash
PYTHONPATH=. make test-evaluation
```

## Repeating a Flaky Case

Some eval cases can be nondeterministic because the agent, planner, reviewer, or final answer generation may vary across runs.

Use the repeat runner to detect flaky behavior:

```bash
PYTHONPATH=. make eval-repeat CASE=skill_repo_review_001 COUNT=5
```

Or call the script directly:

```bash
PYTHONPATH=. python scripts/run_eval_repeated.py --case-id skill_repo_review_001 --count 5
```

The repeat runner prints pass/fail status for each run and reports whether both passing and failing outcomes were observed.

Example:

```text
Repeat Summary
--------------
Case:       skill_repo_review_001
Runs:       5
Passed:     4
Failed:     1
Pass rate:  80.0%
Flaky:      yes
```

## Failure Reports

When evals fail, `scripts/run_evals.py` writes a JSON report to:

```text
evals/results/
```

It also writes a Markdown failure report to:

```text
evals/reports/
```

Print the latest failure report:

```bash
PYTHONPATH=. make eval-latest-report
```

Failure reports include:

- failed case ID
- suite
- score
- failed checks
- final answer excerpt
- tool call summary
- task completion debug signals
- judge failure details when enabled

## Scorer Checks

### Route

Checks whether the runtime selected the expected route:

```text
chat
tool
plan
```

### Skill Selection

Checks whether a skill was used and whether the selected skill matches the expected skill.

Useful fields:

```json
{
  "should_use_skill": true,
  "skill": "repo_review"
}
```

### Tool Selection

Checks required, optional, forbidden, minimum, and maximum tool usage.

Useful fields:

```json
{
  "required_tools": ["get_project_tree"],
  "optional_tools": ["read_multiple_files"],
  "forbidden_tools": ["open_app"],
  "minimum_tool_calls": 1,
  "maximum_tool_calls": 3
}
```

### Tool Arguments

Checks whether a tool was called with expected arguments.

Example:

```json
{
  "tool_arguments": [
    {
      "tool": "read_file",
      "arguments": {
        "path": "README.md"
      },
      "match": "subset"
    }
  ]
}
```

Use `exact` for strict matching and `subset` when extra arguments are acceptable.

### MCP Telemetry

Checks whether MCP calls used the expected provider and exposed/original tool metadata.

Example:

```json
{
  "mcp": [
    {
      "tool": "mcp_read_ticket",
      "provider": "mock_mcp",
      "original_tool": "mcp_read_ticket",
      "exposed_tool": "mcp_read_ticket"
    }
  ]
}
```

### Approval

Checks whether approval-required tools recorded an approval decision before execution.

### Recovery

Checks whether recovery behavior occurred when expected.

### Task Completion

Checks whether the task was assessed as:

```text
complete
partial
failed
blocked
```

Use this carefully. It depends on runtime signals such as successful tool calls, failed tool calls, required tools, forbidden tools, denied approvals, and reviewer remaining steps.

For cases where the goal is mostly routing, skill selection, or answer shape, prefer answer requirements over strict `completion_status`.

### Answer Requirements

Checks deterministic final answer constraints.

Useful fields:

```json
{
  "answer": {
    "contains_all": ["routing", "planning"],
    "contains_any": ["architecture", "structure"],
    "excludes": ["I cannot"],
    "min_characters": 120
  }
}
```

### Answer Grounding

Checks whether the final answer only cites or discusses files that were actually observed through tool calls.

### LLM Judge

Some cases can enable optional LLM judge scoring.

Use this for quality signals, not for low-level deterministic behavior.

Example:

```json
{
  "judge": {
    "enabled": true,
    "min_overall_score": 0.75,
    "rubric": "The answer should provide practical interview preparation help."
  }
}
```

## Debugging Order

When a case fails, debug in this order:

1. Worker errors
2. Route selection
3. Skill selection
4. Tool selection
5. Tool arguments
6. Approval / denied actions
7. Recovery behavior
8. Task completion
9. Answer requirements
10. Answer grounding
11. LLM judge quality

This order avoids chasing downstream failures caused by earlier runtime decisions.

## Stabilizing Flaky Evals

A case is likely flaky if:

- the same case sometimes passes and sometimes fails
- the failed check changes across runs
- `task_completion` switches between `complete` and `partial`
- final answer wording changes enough to miss deterministic phrases
- reviewer remaining steps differ across runs

Use:

```bash
PYTHONPATH=. make eval-repeat CASE=<case_id> COUNT=5
```

Common stabilization strategies:

### Prefer answer requirements for broad qualitative tasks

For repo review, project explanation, interview prep, or summary tasks, use:

```json
"answer": {
  "contains_any": ["architecture", "components", "runtime"],
  "min_characters": 120
}
```

instead of:

```json
"completion_status": "complete"
```

### Use `completion_status` for operational tasks

Use strict task completion expectations when the case has a clear operational success condition, such as:

- required tool was used
- no forbidden tools were used
- no failed tool calls occurred
- reviewer remaining steps should truly be empty

### Avoid over-specific answer phrases

Prefer concept-level phrases:

```json
"contains_any": ["architecture", "structure", "components"]
```

Avoid brittle phrases:

```json
"contains_all": ["This repository contains exactly three layers"]
```

### Use `subset` argument matching when appropriate

If the runtime may include harmless extra arguments, prefer:

```json
"match": "subset"
```

instead of:

```json
"match": "exact"
```

## Eval Environment

Each eval case can configure environment behavior.

Example:

```json
{
  "environment": {
    "fixture_root": "evals/fixtures/sample_repo",
    "env": {
      "ENABLE_MCP_TOOLS": "true",
      "ENABLE_MOCK_MCP_TOOLS": "true"
    },
    "allow_real_side_effects": false
  }
}
```

The eval worker configures:

```text
EVAL_MODE=true
EVAL_FIXTURE_ROOT=<fixture path>
EVAL_ALLOW_REAL_SIDE_EFFECTS=false
DATA_DIR=<temporary eval data dir>
MEMORY_PATH=<temporary eval memory path>
TRACE_PATH=<temporary eval trace path>
NOTES_DIR=<temporary eval notes dir>
```

This keeps eval runs isolated from local runtime data.

## Reports and Artifacts

Eval JSON reports are written to:

```text
evals/results/
```

Markdown failure reports are written to:

```text
evals/reports/
```

Repeated eval reports are written to:

```text
evals/results/repeats/
```

These generated reports are useful for debugging but should usually not be committed.

## Recommended Local Workflow

Before committing eval-related changes:

```bash
PYTHONPATH=. make test-evaluation
PYTHONPATH=. make eval-mcp
PYTHONPATH=. make eval-skills
PYTHONPATH=. make eval-all
```

For suspected flaky cases:

```bash
PYTHONPATH=. make eval-repeat CASE=<case_id> COUNT=5
```

Before a final cleanup commit:

```bash
PYTHONPATH=. make check
```

## Key Files

| File | Purpose |
| --- | --- |
| `evals/cases/*.jsonl` | Eval case definitions |
| `evals/fixtures/` | Test fixture repositories and files |
| `scripts/run_evals.py` | Main eval runner |
| `scripts/eval_worker.py` | Isolated single-case worker |
| `scripts/run_eval_repeated.py` | Repeated case runner for flake detection |
| `app/evaluation/models.py` | Eval case schemas |
| `app/evaluation/snapshot.py` | Runtime summary normalization |
| `app/evaluation/scorers.py` | Deterministic eval scorers |
| `app/evaluation/completion.py` | Task completion assessment |
| `app/evaluation/grounding.py` | Answer grounding assessment |
| `app/evaluation/failure_analysis.py` | Markdown failure report generation |