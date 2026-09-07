# Desktop Assistant Agent Runtime

A local-first desktop assistant agent runtime built in Python.

This project focuses on core AI agent architecture rather than a simple chatbot. It includes routing, planning, skill selection, tool execution, approval-aware safety controls, recovery, replanning, lightweight memory, MCP tool integration, deterministic evaluations, failure analysis, flaky eval detection, runtime metrics, and trace inspection.

## Why This Project

Most simple AI assistants only respond to user messages. This project explores how to build a more agentic runtime that can:

* decide whether a request needs tools
* route requests into chat, tool, or planning flows
* select reusable task skills
* break complex tasks into structured plans
* execute local and MCP-backed tools
* request approval before higher-risk actions
* recover from failed tool calls
* review completed and remaining steps
* decide whether replanning is useful
* persist lightweight durable memory
* log every run for debugging, metrics, and evaluation

The goal is to understand how agent runtimes work beyond a basic chatbot interface.

## Current Features

* **Routing**: classifies user requests as `chat`, `tool`, or `plan`.
* **Planning**: decomposes complex tasks into structured goals and steps.
* **Skill Selection**: selects reusable task skills such as repository review and interview preparation.
* **Tool Use Policy**: decides whether tools should be used and which tools are likely relevant.
* **Tool Runtime**: uses a generic tool registry and executor for local and MCP tools.
* **Memory Policy**: decides when to read or write lightweight durable memory.
* **Approval Policy**: asks for confirmation before approval-required tool actions.
* **Failure Recovery**: retries certain failed tool calls with deterministic fallback strategies.
* **Execution Review**: reviews which plan steps were completed, failed, skipped, or remain.
* **Replanning**: decides whether a revised plan is useful after partial progress or failure.
* **Run Summary**: records a structured summary of each agent run.
* **Runtime Metrics**: computes tool success rate, recovery rate, replanning rate, and possible failure signals.
* **MCP Integration**: supports mock and real MCP tool providers with allowlists, namespacing, approval metadata, timeouts, telemetry, schema normalization, and eval coverage.
* **Evaluation Harness**: tests routing, skills, tools, approvals, recovery, completion, grounding, answer requirements, and MCP telemetry.
* **Developer Debugging Tools**: includes failure reports, repeated eval runs, metrics reports, and a run summary inspector.

## Tech Stack

* Python
* OpenAI Responses API
* Pydantic
* Model Context Protocol
* Local JSON memory
* JSONL trace logging
* unittest-based regression tests
* Makefile developer workflow

## Architecture

```text
User Input
   ↓
Memory Policy
   ↓
Router
   ↓
Tool-Use Policy
   ↓
Skill Selector
   ↓
Planner
   ↓
Tool Executor
   ↓
Recovery Manager
   ↓
Execution Reviewer
   ↓
Replanner
   ↓
Final Answer
   ↓
Run Summary + Metrics + Trace
```

Core runtime modules:

| Module                   | Purpose                                      |
| ------------------------ | -------------------------------------------- |
| `app/agent.py`           | Main runtime orchestration                   |
| `app/run_context.py`     | Structured run summary contract              |
| `app/memory.py`          | Lightweight memory store                     |
| `app/memory_policy.py`   | Conservative memory read/write policy        |
| `app/router.py`          | Route selection                              |
| `app/tool_use_policy.py` | Tool-use and grounding policy                |
| `app/planner.py`         | Task planning                                |
| `app/executor.py`        | Tool execution                               |
| `app/approval_policy.py` | Tool approval decisions                      |
| `app/recovery.py`        | Tool failure recovery                        |
| `app/reviewer.py`        | Execution progress review                    |
| `app/replanner.py`       | Follow-up planning when work remains         |
| `app/tools/`             | Local tool definitions and registry          |
| `app/mcp/`               | MCP provider integration                     |
| `app/evaluation/`        | Eval models, snapshots, scorers, and reports |
| `scripts/`               | Developer, eval, demo, and inspection CLIs   |

## Project Structure

```text
desktop-assistant-agent/
├── app/
│   ├── agent.py                    # Main agent runtime
│   ├── router.py                   # Route decisions: chat / tool / plan
│   ├── planner.py                  # Structured task planning
│   ├── replanner.py                # Revised plan decisions
│   ├── reviewer.py                 # Execution review
│   ├── executor.py                 # Generic tool executor
│   ├── memory.py                   # Lightweight memory store
│   ├── memory_policy.py            # Memory read/write decisions
│   ├── tool_use_policy.py          # Tool-use decisions and grounding
│   ├── approval_policy.py          # Approval and risk policy
│   ├── recovery.py                 # Deterministic tool failure recovery
│   ├── run_context.py              # Unified per-run summary object
│   ├── metrics.py                  # Runtime metrics calculation
│   ├── mcp/                        # MCP providers, config, diagnostics, telemetry
│   ├── evaluation/                 # Eval models, snapshots, scorers, reports
│   ├── skills/                     # Skill registry and skill selection
│   └── tools/
│       ├── base.py                 # ToolDefinition model
│       ├── registry.py             # Tool schemas and function bindings
│       ├── results.py              # Normalized tool result schema
│       ├── system_tools.py         # Local tools
│       └── mock_mcp_tools.py       # Mock MCP tool wrappers
├── skills/
│   ├── repo_review/
│   │   └── SKILL.md
│   └── interview_prep/
│       └── SKILL.md
├── scripts/
│   ├── run_evals.py                # Main eval runner
│   ├── eval_worker.py              # Isolated single-case eval worker
│   ├── run_eval_repeated.py        # Repeated eval runner for flaky cases
│   ├── analyze_eval_failures.py    # Failure report helper
│   ├── inspect_run.py              # Run summary inspector
│   ├── run_demo_workflow.py        # Repo review demo workflow
│   ├── report_metrics.py           # Runtime metrics report
│   └── mcp_discover.py             # MCP provider discovery helper
├── evals/
│   ├── cases/                      # JSONL eval case definitions
│   ├── fixtures/                   # Safe fixture repositories and files
│   ├── results/                    # Generated eval reports
│   └── reports/                    # Generated failure reports
├── docs/
│   ├── demo.md                     # Demo workflow guide
│   ├── evals.md                    # Eval developer guide
│   ├── mcp.md                      # MCP setup and safety guide
│   ├── memory.md                   # Memory design guide
│   └── run-summary-inspector.md    # Trace inspection guide
├── config/
│   └── mcp_servers.example.json
├── data/
│   ├── memory.json                 # Local persistent memory
│   ├── traces.jsonl                # Runtime traces
│   └── notes/                      # Generated notes
├── tests/
│   └── evaluation/                 # Evaluation and runtime contract tests
├── main.py                         # CLI entry point
├── requirements.txt
├── Makefile
├── .env.example
└── README.md
```

## Demo

Run the repository review demo:

```bash
PYTHONPATH=. make demo-repo-review
```

The demo uses a safe fixture repository and runs an end-to-end architecture review. It prints both the final answer and the run summary inspector output.

The demo shows:

* memory policy
* route selection
* tool-use policy
* skill selection
* planning
* tool calls
* approval decisions
* recovery events
* execution review
* replan decision
* final answer
* run summary inspection

Equivalent direct command:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py
```

Run without inspector output:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py --no-inspect
```

Use a custom prompt:

```bash
PYTHONPATH=. python scripts/run_demo_workflow.py \
  --prompt "Review this repository and summarize the runtime architecture."
```

See [Demo Workflow](docs/demo.md) for more details.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YixinHu7/desktop-assistant-agent.git
cd desktop-assistant-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file:

```bash
cp .env.example .env
```

Then add an OpenAI API key:

```text
OPENAI_API_KEY=your_api_key_here
```

## Run the Agent

```bash
python main.py
```

Example prompts:

```text
Explain what an AI agent is in simple terms.

Read main.py and summarize it.

Analyze this codebase structure and explain its architecture.

Create a note titled "Agent Architecture" with a short overview of this project.

Remember that this project uses Python for the runtime.
```

## Developer Commands

Run the agent:

```bash
make run
```

Run the repository review demo:

```bash
make demo-repo-review
```

Run all tests:

```bash
make test
```

Run evaluation unit tests:

```bash
make test-evaluation
```

Run all evals:

```bash
make eval-all
```

Run MCP evals:

```bash
make eval-mcp
```

Run one eval case:

```bash
make eval-case CASE=skill_repo_review_001
```

Run one eval case with a failure report:

```bash
make eval-case-report CASE=skill_repo_review_001
```

Repeat a suspected flaky eval case:

```bash
make eval-repeat CASE=skill_repo_review_001 COUNT=5
```

Inspect the latest agent run:

```bash
make inspect-latest-run
```

Inspect a specific run:

```bash
make inspect-run RUN_ID=<run_id>
```

Inspect configured MCP providers:

```bash
ENABLE_MCP_TOOLS=true \
ENABLE_REAL_MCP_TOOLS=true \
ENABLE_MOCK_MCP_TOOLS=false \
PYTHONPATH=. python scripts/mcp_discover.py
```

Generate a runtime metrics report:

```bash
make metrics
```

Run core validation checks:

```bash
make check
```

Clean traces:

```bash
make clean-traces
```

Clean generated notes:

```bash
make clean-notes
```

Reset local runtime data:

```bash
make reset-data
```

If `make` is not available, use:

```bash
python scripts/dev.py run
python scripts/dev.py metrics
python scripts/dev.py reset-data
```

## Evaluation System

The project includes an end-to-end evaluation harness for testing agent behavior.

The eval system checks:

* route selection
* skill selection
* tool selection
* tool arguments
* MCP telemetry
* approval behavior
* recovery behavior
* task completion
* deterministic answer requirements
* answer grounding
* optional LLM judge quality

Run all deterministic evals:

```bash
PYTHONPATH=. make eval-all
```

Run one case with a generated failure report:

```bash
PYTHONPATH=. make eval-case-report CASE=skill_repo_review_001
```

Repeat a suspected flaky case:

```bash
PYTHONPATH=. make eval-repeat CASE=skill_repo_review_001 COUNT=5
```

See [Eval Developer Guide](docs/evals.md) for eval case format, debugging workflow, failure reports, and flake detection.

## Runtime Metrics

The runtime logs each run into:

```text
data/traces.jsonl
```

To generate a metrics report:

```bash
PYTHONPATH=. make metrics
```

The report summarizes:

* total runs
* route distribution
* skill usage
* tool usage
* tool success rate
* recovery attempts
* replanning activity
* possible failure signals

Example output:

```text
=== Agent Runtime Metrics Report ===

Total runs: 12
Tool-using runs: 7
Grounding-required runs: 3

Routes:
  - chat: 4
  - plan: 5
  - tool: 3

Skills:
  - Skill-using runs: 5
  - repo_review: 3
  - interview_prep: 2

Tool Calls:
  - Total tool calls: 10
  - Successful tool calls: 8
  - Failed tool calls: 2
  - Average per-run tool success rate: 86.0%

Recovery:
  - Recovery attempted runs: 2
  - Recovery succeeded runs: 2

Replanning:
  - Replan considered runs: 3
  - Replan triggered runs: 1

Quality Signals:
  - Possible failure runs: 2
```

## Run Summary Inspector

The run summary inspector renders a human-readable report for a single agent run.

Inspect the latest run:

```bash
PYTHONPATH=. make inspect-latest-run
```

Inspect a specific run:

```bash
PYTHONPATH=. make inspect-run RUN_ID=<run_id>
```

The inspector shows:

* user input
* route decision
* memory decision
* tool-use policy decision
* selected skill
* original plan
* tool calls
* approval decisions
* recovery events
* execution review
* replan decision
* revised plan
* final answer

See [Run Summary Inspector](docs/run-summary-inspector.md) for trace inspection, run debugging, and demo workflow.

## Current Local Tools

| Tool                  | Purpose                                        |
| --------------------- | ---------------------------------------------- |
| `list_files`          | List files in a directory                      |
| `read_file`           | Read local file contents                       |
| `create_note`         | Create a markdown note                         |
| `save_memory_fact`    | Save durable memory through the tool interface |
| `open_app`            | Open a desktop application                     |
| `get_project_tree`    | Inspect a project directory tree               |
| `find_file`           | Find local project files                       |
| `search_files`        | Search local project files                     |
| `read_multiple_files` | Read multiple local files in one tool call     |

## Skills

Skills package reusable task instructions for specialized workflows.

Current skills include:

| Skill            | Purpose                                                   |
| ---------------- | --------------------------------------------------------- |
| `repo_review`    | Analyze a repository and produce an architecture overview |
| `interview_prep` | Help prepare interview stories and checklists             |

The skill selector decides whether a user request should use a specialized skill. If a skill is selected, its instructions are injected into the agent execution context.

## Memory Design

The memory system is intentionally lightweight. It stores durable facts, preferences, and recent conversation history in a normalized JSON structure.

Memory writes are gated by `MemoryPolicy`, which only allows writes when the user clearly asks the assistant to remember durable information. The store validates its shape on load, recovers from malformed files, and exposes stable helper methods for setting facts, setting preferences, reading context, and truncating recent history.

The current memory design prioritizes transparency, testability, and safe persistence. It does not implement vector memory, semantic retrieval, memory ranking, memory decay, or multi-user memory.

See [Memory Design](docs/memory.md) for more details.

## MCP Integration

This project supports MCP tools through the same registry and executor path as local tools.

MCP support includes:

* mock MCP tools for deterministic evals
* real stdio MCP server providers
* explicit `allowed_tools` allowlists
* namespaced tool names such as `mcp_tiny_echo`
* approval and risk metadata through `tool_policies`
* discovery and execution timeouts
* runtime guardrails for unregistered tools
* schema normalization for MCP tool parameters
* telemetry for eval scoring and debugging

See [MCP Developer Guide](docs/mcp.md) for setup, configuration, safety model, and troubleshooting.

## Safety Model

The runtime uses a conservative safety model:

* tools are registered with explicit permission metadata
* approval-required tools are gated before execution
* local file tools are constrained in eval mode
* eval and demo runs use isolated data directories
* real MCP tools are disabled by default
* real MCP tools require explicit server configuration and allowlists
* MCP calls are namespaced and guarded at runtime
* memory writes are policy-gated and sanitized before persistence

## Documentation

See:

* [Demo Workflow](docs/demo.md)
* [Eval Developer Guide](docs/evals.md)
* [MCP Developer Guide](docs/mcp.md)
* [Memory Design](docs/memory.md)
* [Run Summary Inspector](docs/run-summary-inspector.md)

## Recommended Validation

Before committing changes:

```bash
PYTHONPATH=. make check
```

Before presenting the project:

```bash
PYTHONPATH=. make check
PYTHONPATH=. make eval-all
PYTHONPATH=. make demo-repo-review
```

For suspected flaky eval cases:

```bash
PYTHONPATH=. make eval-repeat CASE=<case_id> COUNT=5
```

## Project Status

This project is a CLI-based AI agent runtime prototype.

The focus is backend agent architecture, tool execution, safety controls, MCP integration, evaluation, and observability rather than a polished user interface.

## Future Work

Potential future improvements:

* add a terminal dashboard or local web UI
* add stronger step-level execution tracking
* add richer file search and repository indexing
* add interactive approval UI for high-risk tools
* support additional MCP transports
* add trace-based regression snapshots
* add more reusable task skills
