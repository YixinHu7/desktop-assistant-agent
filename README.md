# Desktop Assistant Agent Runtime

A local-first desktop assistant agent runtime built in Python.

This project focuses on core AI agent architecture: routing, planning, tool execution, memory policy, approval policy, recovery, replanning, tracing, and runtime metrics.

## Why This Project

Most simple AI assistants only respond to user messages. This project explores how to build a more agentic system that can:

- decide whether a request needs tools
- break complex tasks into plans
- execute local tools
- recover from failed tool calls
- review completed and remaining steps
- decide whether replanning is useful
- log every run for debugging and evaluation

The goal is to understand how agent runtimes work beyond a basic chatbot interface.

## Current Features

- **Routing**: classifies user requests as `chat`, `tool`, or `plan`
- **Planning**: decomposes complex tasks into structured steps
- **Tool Use Policy**: decides whether tools should be used and which tools are likely relevant
- **Tool Runtime**: uses a generic tool registry and executor
- **Memory Policy**: decides when to read or write durable user memory
- **Approval Policy**: asks for user confirmation before risky tool actions
- **Failure Recovery**: retries certain failed tool calls with deterministic fallback strategies
- **Execution Review**: reviews which plan steps were completed, failed, skipped, or remain
- **Replanning**: decides whether a revised plan is useful after partial failure
- **Run Summary**: logs a unified summary of each agent run
- **Runtime Metrics**: computes tool success rate, recovery rate, replanning rate, and possible failure signals

## Tech Stack

- Python
- OpenAI Responses API
- Pydantic
- Local JSON memory
- JSONL trace logging

## Project Structure

    desktop-assistant-agent/
    ├── app/
    │   ├── agent.py              # Main agent runtime
    │   ├── router.py             # Route decisions: chat / tool / plan
    │   ├── planner.py            # Structured task planning
    │   ├── replanner.py          # Revised plan decisions
    │   ├── reviewer.py           # Execution review
    │   ├── executor.py           # Generic tool executor
    │   ├── memory.py             # Persistent memory store
    │   ├── memory_policy.py      # Memory read/write decisions
    │   ├── tool_use_policy.py    # Tool-use decisions and grounding
    │   ├── approval_policy.py    # Approval and risk policy
    │   ├── recovery.py           # Deterministic tool failure recovery
    │   ├── run_context.py        # Unified per-run summary object
    │   ├── metrics.py            # Runtime metrics calculation
    │   └── tools/
    │       ├── base.py           # ToolDefinition model
    │       ├── registry.py       # Tool schemas + function bindings
    │       ├── results.py        # Normalized tool result schema
    │       └── system_tools.py   # Local tools
    ├── scripts/
    │   └── report_metrics.py     # CLI metrics report
    ├── data/
    │   ├── memory.json           # Local persistent memory
    │   ├── traces.jsonl          # Runtime traces
    │   └── notes/                # Generated notes
    ├── main.py                   # CLI entry point
    ├── requirements.txt
    ├── .env.example
    └── README.md

## Runtime Flow

    User Input
       ↓
    Memory Policy
       ↓
    Router
       ↓
    Tool Use Policy
       ↓
    Planner
       ↓
    Execution Cycle
       ↓
    Tool Executor
       ↓
    Failure Recovery
       ↓
    Execution Reviewer
       ↓
    Replanner
       ↓
    Run Summary + Metrics
       ↓
    Final Answer

## Core Design Ideas

### 1. Routing

The router decides whether a request should be handled as:

- `chat`: normal response without tools
- `tool`: direct tool execution
- `plan`: multi-step task requiring decomposition

### 2. Planning

For complex requests, the planner produces a structured goal and step list.

This gives the runtime something concrete to execute and later review.

### 3. Tool Use Policy

The tool-use policy controls whether tools should be available for a run.

For example, simple explanations should not use tools, while file inspection tasks should use tools and require grounding.

### 4. Generic Tool Runtime

Tools are represented as `ToolDefinition` objects containing:

- model-facing schema
- executable Python function
- approval requirement
- source metadata

This makes the runtime extensible for future skill-based tools or MCP-based tools.

### 5. Failure Recovery

If a tool fails, the recovery manager can apply deterministic fallback strategies.

Example:

    list_files("./project") fails
    → retry list_files(".")

### 6. Execution Review and Replanning

After execution, the reviewer checks whether plan steps were completed, failed, skipped, or remain.

If meaningful progress is still possible, the replanner may generate revised next steps.

### 7. Observability

Each run logs:

- decisions
- plans
- tool calls
- recovery attempts
- reviews
- replan decisions
- final answer
- runtime metrics

This makes the system easier to debug and evaluate.

## Setup

### 1. Clone the repository

    git clone https://github.com/YixinHu7/desktop-assistant-agent.git
    cd desktop-assistant-agent

### 2. Create a virtual environment

    python3 -m venv .venv
    source .venv/bin/activate

### 3. Install dependencies

    pip install -r requirements.txt

### 4. Configure environment variables

Copy the example env file:

    cp .env.example .env

Then add your API key:

    OPENAI_API_KEY=your_api_key_here

## Run the Agent

    python main.py

Example prompts:

    Explain what an AI agent is in simple terms.

    Read main.py and summarize it.

    Create a note titled "Agent Architecture" with a short overview of this project.

    Remember that I prefer concise technical explanations.

## Runtime Metrics

The runtime logs each run into:

    data/traces.jsonl

To generate a metrics report:

    python scripts/report_metrics.py

The report summarizes:

- total runs
- route distribution
- tool usage
- tool success rate
- recovery attempts
- replanning activity
- possible failure signals

## Example Metrics Report

    === Agent Runtime Metrics Report ===

    Total runs: 12
    Tool-using runs: 7
    Grounding-required runs: 3

    Routes:
      - chat: 4
      - plan: 5
      - tool: 3

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

## Current Tools

| Tool | Purpose |
|---|---|
| `list_files` | List files in a directory |
| `read_file` | Read local file contents |
| `create_note` | Create a markdown note |
| `save_memory_fact` | Save durable user memory |
| `open_app` | Open a desktop application |

## Roadmap

### Runtime Improvements

- [ ] Add stronger step-level execution tracking
- [ ] Add retry limits per tool
- [ ] Add richer file search
- [ ] Add task completion scoring
- [ ] Add config-based tool permissions

### Skills Layer

Planned future addition:

    skills/
      repo_review/
        SKILL.md
      interview_prep/
        SKILL.md
      project_planning/
        SKILL.md

Skills will package reusable task instructions, resources, and scripts for specialized workflows.

### MCP Integration

Planned future addition:

- MCP-ready tool adapter layer
- support for external MCP tool sources
- unified execution path for local and MCP tools

The current `ToolDefinition` design is intended to make future MCP integration easier.

## Project Status

This project is currently a CLI-based agent runtime prototype.

The focus is backend agent architecture, not UI.

Future UI layers could include:

- terminal dashboard
- local web interface
- desktop assistant panel