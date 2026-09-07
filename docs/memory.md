# Memory Design

The project includes a lightweight memory layer for durable facts, preferences, and recent conversation history.

The memory system is intentionally simple. It is designed to be transparent, testable, and safe rather than a full semantic memory system.

## Goals

The memory layer supports:

* durable facts
* durable preferences
* recent conversation history
* memory context injection into downstream agent decisions
* conservative memory write gating
* stable JSON persistence
* eval/demo isolation through environment-configured paths

## Non-Goals

The current memory system does not implement:

* vector memory
* semantic retrieval
* memory ranking
* memory decay
* multi-user memory
* memory conflict resolution
* memory dashboards

These are intentionally out of scope for the current project.

## Data Shape

Memory is stored as JSON:

```json
{
  "facts": {},
  "preferences": {},
  "history": []
}
```

The store normalizes this structure on load. If the file is missing, malformed, or has invalid field types, it falls back to a safe default structure.

## MemoryStore

`MemoryStore` provides helper methods for:

* loading memory
* saving memory
* setting facts
* setting preferences
* retrieving facts
* retrieving preferences
* adding recent history
* generating memory context text

Important methods:

```text
set_fact
set_preference
get_fact
get_preference
add_history
get_recent_history
get_context_text
```

## MemoryPolicy

`MemoryPolicy` decides whether a user message requires a memory action.

Supported actions:

```text
none
read
write
```

A memory write is only allowed when the user clearly asks the assistant to remember durable information.

The policy rejects memory writes when:

* the key is missing
* the value is missing
* the user did not clearly ask to remember durable information

## Runtime Flow

```text
User input
   ↓
MemoryStore.add_history(user)
   ↓
MemoryStore.get_context_text()
   ↓
MemoryPolicy.decide(...)
   ↓
optional MemoryStore.set_fact(...)
   ↓
updated memory context
   ↓
router / planner / executor prompts
```

## Testing

Memory behavior is covered by unit tests:

```bash
PYTHONPATH=. python -m unittest tests.evaluation.test_memory_store -v
PYTHONPATH=. python -m unittest tests.evaluation.test_memory_policy -v
```

The tests cover:

* default memory loading
* malformed memory normalization
* invalid JSON recovery
* fact persistence
* preference persistence
* history truncation
* context text generation
* memory key normalization
* conservative memory write sanitization

## Design Rationale

The memory layer is deliberately conservative. Agent memory can create long-term state, so writes should be explicit, durable, and easy to inspect.

This design keeps memory behavior predictable while still allowing the runtime to preserve useful project and user preferences across turns.
