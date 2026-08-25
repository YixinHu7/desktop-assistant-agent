# MCP Developer Guide

This project supports both mock MCP tools for deterministic evals and real MCP stdio servers for external tool integration.

The MCP layer is designed around explicit safety boundaries:

- MCP tools are disabled by default.
- Real MCP servers must be enabled through feature flags.
- Real MCP tools are exposed only when listed in `allowed_tools`.
- Real MCP tool names are namespaced as `mcp_<server>_<tool>`.
- Tool approval metadata comes from explicit `tool_policies`.
- Real MCP discovery and execution have timeout boundaries.
- MCP execution emits telemetry for evaluation and debugging.

## Runtime Architecture

MCP tools enter the runtime through the same `ToolDefinition` path as local tools.

```text
config/mcp_servers.json
   ↓
load_mcp_server_configs()
   ↓
build_mcp_providers()
   ↓
RealMCPProvider.list_tool_specs()
   ↓
build_tool_definitions()
   ↓
ToolDefinition
   ↓
ToolExecutor
   ↓
Run Summary + Eval Snapshot
```

The important design choice is that MCP tools do not get a separate execution path. They are adapted into the existing tool registry, approval policy, executor, telemetry, and eval system.

## Feature Flags

MCP is controlled by these environment variables:

```env
ENABLE_MCP_TOOLS=false
ENABLE_MOCK_MCP_TOOLS=false
ENABLE_REAL_MCP_TOOLS=false
MCP_SERVER_CONFIG_PATH=config/mcp_servers.json
```

### Mock MCP Tools

Mock MCP tools are used for deterministic eval cases.

Enable them with:

```bash
ENABLE_MCP_TOOLS=true \
ENABLE_MOCK_MCP_TOOLS=true \
ENABLE_REAL_MCP_TOOLS=false \
PYTHONPATH=. make eval-mcp
```

Mock MCP tools currently include:

| Tool | Purpose |
| --- | --- |
| `mcp_search_docs` | Search mock documentation |
| `mcp_read_ticket` | Read mock ticket records |
| `mcp_list_resources` | List mock MCP resources |

### Real MCP Tools

Real MCP tools are disabled by default.

Enable them with:

```bash
ENABLE_MCP_TOOLS=true \
ENABLE_REAL_MCP_TOOLS=true \
ENABLE_MOCK_MCP_TOOLS=false \
MCP_SERVER_CONFIG_PATH=config/mcp_servers.json \
PYTHONPATH=. python scripts/mcp_discover.py
```

## Real MCP Server Config

Create a local config file:

```bash
cp config/mcp_servers.example.json config/mcp_servers.json
```

`config/mcp_servers.json` should not be committed. It may contain local paths, server commands, or environment-specific values.

Example:

```json
{
  "servers": [
    {
      "name": "tiny",
      "command": "python",
      "args": ["tests/fixtures/mcp_servers/tiny_mcp_server.py"],
      "env": {},
      "enabled": true,
      "allowed_tools": ["echo", "get_status"],
      "list_timeout_seconds": 5.0,
      "call_timeout_seconds": 10.0,
      "tool_policies": {
        "echo": {
          "requires_approval": false,
          "risk_level": "low",
          "reason": "Read-only tiny test echo tool."
        },
        "get_status": {
          "requires_approval": false,
          "risk_level": "low",
          "reason": "Read-only tiny test status tool."
        }
      }
    }
  ]
}
```

## Config Fields

| Field | Required | Purpose |
| --- | --- | --- |
| `name` | Yes | Local server identifier used for namespacing |
| `command` | Yes | Command used to start the MCP stdio server |
| `args` | No | Command arguments |
| `env` | No | Environment variables for the server process |
| `enabled` | No | Whether this server should be loaded |
| `allowed_tools` | No | Original MCP tool names allowed to register and execute |
| `list_timeout_seconds` | No | Timeout for MCP tool discovery |
| `call_timeout_seconds` | No | Timeout for MCP tool execution |
| `tool_policies` | No | Approval and risk metadata per allowed tool |

## Safety Model

### 1. MCP Is Disabled by Default

No MCP provider is built unless:

```env
ENABLE_MCP_TOOLS=true
```

Real MCP providers also require:

```env
ENABLE_REAL_MCP_TOOLS=true
```

### 2. `allowed_tools` Is the Main Safety Boundary

Real MCP tools are exposed only if the original MCP tool name is listed in `allowed_tools`.

For example:

```json
"allowed_tools": ["echo"]
```

This registers:

```text
mcp_tiny_echo
```

It does not register:

```text
mcp_tiny_get_status
```

### 3. Runtime Calls Are Also Guarded

The registry allowlist prevents unsafe tools from being exposed to the model.

The runtime guardrail prevents direct calls to unregistered or non-allowed tools.

Blocked calls return a normalized `tool_error` with metadata:

```json
{
  "real_mcp_error": true,
  "mcp_guardrail_blocked": true,
  "error_type": "MCPToolNotAllowed"
}
```

### 4. Tool Names Are Namespaced

Real MCP tools are exposed as:

```text
mcp_<server>_<tool>
```

For example:

```text
mcp_tiny_echo
```

This prevents collisions with local tools such as:

```text
read_file
open_app
```

It also prevents collisions between MCP servers that expose tools with the same original name.

### 5. Approval Metadata Comes From `tool_policies`

Example:

```json
"tool_policies": {
  "echo": {
    "requires_approval": false,
    "risk_level": "low",
    "reason": "Read-only tiny test echo tool."
  }
}
```

Supported risk levels:

```text
low
medium
high
```

If a real MCP tool has no explicit policy, it defaults to requiring approval and high risk.

### 6. Timeouts Prevent Hanging Servers

Discovery is bounded by:

```json
"list_timeout_seconds": 5.0
```

Tool execution is bounded by:

```json
"call_timeout_seconds": 10.0
```

If discovery fails or times out, the provider records diagnostics and returns no tools.

If execution fails or times out, the provider returns a normalized `tool_error`.

## Schema Normalization

Real MCP tool schemas are normalized before registration.

The normalized schema is always an object schema suitable for strict tool registration:

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

Normalization handles:

- missing `type`
- missing `properties`
- missing `required`
- non-object top-level schemas
- invalid `required` fields
- `additionalProperties` not being explicitly disabled
- nested object schemas

This prevents malformed MCP schemas from breaking the registry or model-facing tool schema surface.

## Discovery Diagnostics

Use the discovery script to inspect configured MCP providers:

```bash
ENABLE_MCP_TOOLS=true \
ENABLE_REAL_MCP_TOOLS=true \
ENABLE_MOCK_MCP_TOOLS=false \
MCP_SERVER_CONFIG_PATH=config/mcp_servers.json \
PYTHONPATH=. python scripts/mcp_discover.py
```

Example output shape:

```json
{
  "config": {
    "enable_mcp_tools": true,
    "enable_mock_mcp_tools": false,
    "enable_real_mcp_tools": true,
    "mcp_server_config_path": "config/mcp_servers.json"
  },
  "provider_count": 1,
  "providers": [
    {
      "provider_name": "mcp:tiny",
      "tool_specs": ["mcp_tiny_echo"],
      "diagnostics": {
        "status": "ok",
        "allowed_tools": ["echo"],
        "discovered_tools": ["echo", "get_status"],
        "registered_tools": ["mcp_tiny_echo"],
        "filtered_tools": ["get_status"]
      }
    }
  ]
}
```

Diagnostics distinguish:

| Field | Meaning |
| --- | --- |
| `discovered_tools` | Tools exposed by the MCP server |
| `allowed_tools` | Tools allowed by config |
| `registered_tools` | Namespaced tools registered into the agent |
| `filtered_tools` | Discovered tools excluded by allowlist |
| `error_type` | Discovery error type if discovery failed |
| `error_message` | Discovery error message if discovery failed |

## MCP Telemetry

MCP tool calls include telemetry in the run summary.

Example:

```json
{
  "tool": "mcp_tiny_echo",
  "source": "mcp:tiny",
  "mcp": {
    "provider": "mcp:tiny",
    "server": "tiny",
    "original_tool": "echo",
    "exposed_tool": "mcp_tiny_echo"
  }
}
```

This telemetry is used by evals to verify that the correct MCP provider and tool were used.

## Eval Coverage

Run MCP evals:

```bash
PYTHONPATH=. make eval-mcp
```

Run one MCP eval case:

```bash
PYTHONPATH=. make eval-case-report CASE=mcp_read_ticket_001
```

Run all evals:

```bash
PYTHONPATH=. make eval-all
```

MCP evals check:

- required tool selection
- tool arguments
- MCP telemetry
- answer requirements
- task completion when applicable

## Unit Tests

Useful MCP-related test commands:

```bash
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_factory -v
PYTHONPATH=. python -m unittest tests.evaluation.test_real_mcp_provider -v
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_provider_timeouts -v
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_provider_isolation -v
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_registry_integration -v
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_schema_normalization -v
PYTHONPATH=. python -m unittest tests.evaluation.test_mcp_telemetry_scorer -v
```

Run all evaluation tests:

```bash
PYTHONPATH=. make test-evaluation
```

## Common Troubleshooting

### No MCP providers are loaded

Check:

```env
ENABLE_MCP_TOOLS=true
ENABLE_REAL_MCP_TOOLS=true
MCP_SERVER_CONFIG_PATH=config/mcp_servers.json
```

Then run:

```bash
PYTHONPATH=. python scripts/mcp_discover.py
```

### Provider exists but no tools are registered

Check that `allowed_tools` contains the original MCP tool names, not the namespaced tool names.

Correct:

```json
"allowed_tools": ["echo"]
```

Incorrect:

```json
"allowed_tools": ["mcp_tiny_echo"]
```

### Tool appears in `filtered_tools`

The server exposed the tool, but the config did not allow it.

Add the original tool name to `allowed_tools` only if the tool is intended to be available.

### Tool policy validation fails

Every key in `tool_policies` must also appear in `allowed_tools`.

Correct:

```json
"allowed_tools": ["echo"],
"tool_policies": {
  "echo": {
    "requires_approval": false,
    "risk_level": "low",
    "reason": "Read-only echo tool."
  }
}
```

### Discovery times out

Increase:

```json
"list_timeout_seconds": 10.0
```

Also verify that the server command works directly from the project root.

### Tool execution times out

Increase:

```json
"call_timeout_seconds": 30.0
```

For long-running tools, prefer making the MCP server return progress or smaller bounded operations.

## Development Notes

The MCP implementation currently supports stdio MCP servers.

Key files:

| File | Purpose |
| --- | --- |
| `app/mcp/provider.py` | Provider protocol and `MCPToolSpec` |
| `app/mcp/mock_provider.py` | Deterministic mock MCP provider |
| `app/mcp/real_provider.py` | Real stdio MCP provider |
| `app/mcp/server_config.py` | Config parsing and validation |
| `app/mcp/factory.py` | Provider construction |
| `app/mcp/schema.py` | Tool schema normalization |
| `app/mcp/diagnostics.py` | Discovery diagnostics model |
| `app/mcp/telemetry.py` | MCP execution telemetry helpers |
| `app/tools/registry.py` | Registers MCP tools as `ToolDefinition`s |
| `scripts/mcp_discover.py` | CLI discovery/debugging helper |
| `evals/cases/mcp.jsonl` | MCP eval cases |

## Current Limitations

- Only stdio MCP servers are supported.
- Real MCP tools must be configured manually.
- The runtime does not yet provide an interactive approval UI.
- Long-running tools should be bounded by server design and client timeouts.
- `config/mcp_servers.json` is environment-specific and should remain local.