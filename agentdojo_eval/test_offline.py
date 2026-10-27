"""Offline checks for query_guard.py. No API key and no network are needed.

Run:  python test_offline.py

What is checked:
  1. QueryToolPolicy parses decisions, fails closed on bad output and never mutates shared state.
  2. Advisory mode only changes the system prompt; it does not block anything.
  3. GatedToolsExecutor executes allowed calls, denies the others (order preserved), and a denied
     send_email really leaves the environment untouched, while an allowed one changes it.
  4. The whole pipeline runs through AgentDojo's real benchmark functions with a scripted fake LLM.
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from agentdojo.agent_pipeline import (
    AgentPipeline,
    BasePipelineElement,
    InitQuery,
    SystemMessage,
    ToolsExecutionLoop,
    ToolsExecutor,
)
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import (
    ChatAssistantMessage,
    ChatSystemMessage,
    ChatUserMessage,
    get_text_content_as_str,
    text_content_block_from_string,
)

from query_guard import ALLOWED_TOOLS_KEY, GatedToolsExecutor, QueryToolPolicy

VERSION, SUITE = "v1.2.2", "workspace"
MODEL = "gpt-4o-mini-2024-07-18"
SEND_ARGS = {"recipients": ["someone@example.com"], "subject": "hi", "body": "test"}


class FakeClient:
    """Mimics openai.OpenAI().chat.completions.create and returns a fixed message content."""

    def __init__(self, content: str) -> None:
        message = SimpleNamespace(content=content)
        completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **_: completion))


class ScriptedLLM(BasePipelineElement):
    """Stand-in LLM: first it asks for get_current_day AND send_email, then it answers."""

    name = "scripted"

    def query(self, query, runtime, env=EmptyEnv(), messages=[], extra_args={}):
        if messages[-1]["role"] == "tool":
            reply = ChatAssistantMessage(role="assistant", content=[text_content_block_from_string("Done.")], tool_calls=None)
        else:
            calls = [
                FunctionCall(function="get_current_day", args={}, id="call_1"),
                FunctionCall(function="send_email", args=SEND_ARGS, id="call_2"),
            ]
            reply = ChatAssistantMessage(role="assistant", content=None, tool_calls=calls)
        return query, runtime, env, [*messages, reply], extra_args


def policy_json(tools: list[str], should_use: bool = True) -> str:
    return json.dumps({"should_use_tools": should_use, "likely_tools": tools, "avoid_tools": [], "reason": "test"})


def base_messages() -> list:
    return [
        ChatSystemMessage(role="system", content=[text_content_block_from_string("SYS")]),
        ChatUserMessage(role="user", content=[text_content_block_from_string("What day is it?")]),
    ]


def test_policy_parsing_and_shared_state(suite) -> None:
    runtime = FunctionsRuntime(suite.tools)
    shared_default: dict = {}

    policy = QueryToolPolicy(FakeClient(policy_json(["get_current_day", "not_a_tool", "get_current_day"])), MODEL, "enforce")
    _, _, _, messages, extra = policy.query("q", runtime, EmptyEnv(), base_messages(), shared_default)
    assert extra[ALLOWED_TOOLS_KEY] == ["get_current_day"], extra  # unknown dropped, duplicates removed
    assert shared_default == {}, "the shared default extra_args dict must not be mutated"
    assert get_text_content_as_str(messages[0]["content"]) == "SYS", "enforce mode must not touch the prompt"

    bad = QueryToolPolicy(FakeClient("this is not json"), MODEL, "enforce")
    _, _, _, _, extra = bad.query("q", runtime, EmptyEnv(), base_messages(), {})
    assert extra[ALLOWED_TOOLS_KEY] == [] and extra["policy_parsed_ok"] is False  # fails closed

    nothing = QueryToolPolicy(FakeClient(policy_json([], should_use=False)), MODEL, "enforce")
    _, _, _, _, extra = nothing.query("q", runtime, EmptyEnv(), base_messages(), {})
    assert extra[ALLOWED_TOOLS_KEY] == []
    print("ok: policy parsing, fail-closed, no shared-state mutation")


def test_advisory_changes_prompt_only(suite) -> None:
    runtime = FunctionsRuntime(suite.tools)
    policy = QueryToolPolicy(FakeClient(policy_json(["get_current_day"])), MODEL, "advisory")
    _, _, _, messages, extra = policy.query("q", runtime, EmptyEnv(), base_messages(), {})
    system_text = get_text_content_as_str(messages[0]["content"])
    assert system_text.startswith("SYS") and "likely_tools: ['get_current_day']" in system_text
    assert len(messages[0]["content"]) == 1, "hint must be merged into a single content block"
    print("ok: advisory mode adds a hint and nothing else")


def test_gate_on_real_environment(suite) -> None:
    def run(allowed: list[str]):
        env = suite.load_and_inject_default_environment({})
        before = env.model_dump()
        calls = [
            FunctionCall(function="get_current_day", args={}, id="c1"),
            FunctionCall(function="send_email", args=SEND_ARGS, id="c2"),
        ]
        assistant = ChatAssistantMessage(role="assistant", content=None, tool_calls=calls)
        messages = [*base_messages(), assistant]
        runtime = FunctionsRuntime(suite.tools)
        _, _, env_out, out, _ = GatedToolsExecutor().query("q", runtime, env, messages, {ALLOWED_TOOLS_KEY: allowed})
        return before, env_out.model_dump(), out

    before, after, out = run(["get_current_day"])  # send_email NOT allowed
    assert len(out) == 5 and [m.get("tool_call_id") for m in out[3:]] == ["c1", "c2"]
    assert out[3]["error"] is None and "denied by policy" in out[4]["error"]
    assert before == after, "a denied send_email must not change the environment"

    before, after, out = run(["get_current_day", "send_email"])  # control: both allowed
    assert all(m["error"] is None for m in out[3:])
    assert before != after, "control failed: an allowed send_email should change the environment"

    try:
        GatedToolsExecutor().query("q", FunctionsRuntime(suite.tools), EmptyEnv(), [*base_messages(), assistant_with_call()], {})
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing policy decision must raise, not silently allow")
    print("ok: gate executes allowed calls, denies the rest, keeps order, protects the environment")


def test_read_only_classification_and_allow_reads(suite) -> None:
    """The read/write heuristic must match the real workspace tools, and allow_reads must only open reads."""
    from query_guard import is_read_only

    reads = sorted(t.name for t in suite.tools if is_read_only(t.name))
    writes = sorted(t.name for t in suite.tools if not is_read_only(t.name))
    expected_writes = {
        "send_email", "delete_email", "create_calendar_event", "cancel_calendar_event",
        "reschedule_calendar_event", "add_calendar_event_participants", "append_to_file",
        "create_file", "delete_file", "share_file",
    }
    assert set(writes) == expected_writes, f"unexpected write set: {writes}"
    assert len(reads) == len(suite.tools) - len(expected_writes)

    env = suite.load_and_inject_default_environment({})
    calls = [
        FunctionCall(function="search_files", args={"query": "x"}, id="c1"),  # read, not in allowed set
        FunctionCall(function="send_email", args=SEND_ARGS, id="c2"),  # write, not in allowed set
    ]
    messages = [*base_messages(), ChatAssistantMessage(role="assistant", content=None, tool_calls=calls)]
    allowed = {ALLOWED_TOOLS_KEY: ["get_current_day"]}

    _, _, _, strict, _ = GatedToolsExecutor().query("q", FunctionsRuntime(suite.tools), env, messages, dict(allowed))
    assert all("denied by policy" in (m["error"] or "") for m in strict[3:]), "strict gate should deny both"

    env = suite.load_and_inject_default_environment({})
    before = env.model_dump()
    _, _, env_out, loose, _ = GatedToolsExecutor(allow_reads=True).query(
        "q", FunctionsRuntime(suite.tools), env, messages, dict(allowed)
    )
    assert loose[3]["error"] is None, "a read-only tool should run when allow_reads=True"
    assert "denied by policy" in loose[4]["error"], "send_email must stay denied when allow_reads=True"
    assert before == env_out.model_dump(), "denied send_email must not change the environment"
    print(f"ok: read/write split ({len(reads)} read-only, {len(writes)} state-changing); allow_reads opens reads only")


def assistant_with_call() -> ChatAssistantMessage:
    call = FunctionCall(function="get_current_day", args={}, id="c1")
    return ChatAssistantMessage(role="assistant", content=None, tool_calls=[call])


def test_through_real_benchmark(suite) -> None:
    """Run AgentDojo's own benchmark functions on one task with the scripted LLM."""
    with tempfile.TemporaryDirectory() as tmp:
        logdir = Path(tmp)
        llm = ScriptedLLM()
        policy = QueryToolPolicy(FakeClient(policy_json(["get_current_day"])), MODEL, "enforce")
        pipeline = AgentPipeline(
            [SystemMessage("SYS"), InitQuery(), policy, llm, ToolsExecutionLoop([GatedToolsExecutor(), llm])]
        )
        pipeline.name = f"{MODEL}-policy-enforce"
        with OutputLogger(str(logdir)):
            clean = benchmark_suite_without_injections(
                pipeline, suite, logdir=logdir, force_rerun=True, user_tasks=["user_task_0"], benchmark_version=VERSION
            )
            attacker = load_attack("important_instructions", suite, pipeline)
            attacked = benchmark_suite_with_injections(
                pipeline,
                suite,
                attacker,
                logdir=logdir,
                force_rerun=True,
                user_tasks=["user_task_0"],
                injection_tasks=["injection_task_0"],
                benchmark_version=VERSION,
            )
        assert list(clean["utility_results"]) == [("user_task_0", "")]
        assert list(attacked["security_results"]) == [("user_task_0", "injection_task_0")]
        traces = [p.read_text() for p in logdir.rglob("*.json")]
        assert traces and any("denied by policy" in t for t in traces), "denial should appear in the saved traces"
        print(f"ok: benchmark plumbing ({len(traces)} trace files written, denial visible in traces)")


if __name__ == "__main__":
    suite_ = get_suite(VERSION, SUITE)
    test_policy_parsing_and_shared_state(suite_)
    test_advisory_changes_prompt_only(suite_)
    test_gate_on_real_environment(suite_)
    test_read_only_classification_and_allow_reads(suite_)
    test_through_real_benchmark(suite_)
    print("\nAll offline checks passed.")