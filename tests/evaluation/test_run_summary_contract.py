import unittest

from app.run_context import RunContext


class RunSummaryContractTests(unittest.TestCase):
    def test_run_context_summary_contains_stable_top_level_fields(self):
        run = RunContext(user_input="Analyze this repository.")

        run.memory_decision = {
            "action": "none",
            "reason": "No memory update needed.",
        }
        run.route_decision = {
            "route": "plan",
            "reason": "Repository analysis requires planning.",
        }
        run.tool_use_decision = {
            "should_use_tools": True,
            "likely_tools": ["get_project_tree"],
            "avoid_tools": ["open_app"],
            "requires_grounding": True,
            "reason": "Need local repo evidence.",
        }
        run.skill_decision = {
            "should_use_skill": True,
            "selected_skill": "repo_review",
            "reason": "The user asked for codebase architecture analysis.",
        }
        run.selected_skill = "repo_review"
        run.plan = {
            "goal": "Analyze repository architecture.",
            "steps": [
                {"step": "Inspect the project tree."},
                {"step": "Summarize the architecture."},
            ],
        }
        run.tool_calls.append(
            {
                "tool": "get_project_tree",
                "tool_name": "get_project_tree",
                "arguments": {
                    "path": ".",
                    "max_depth": 3,
                },
                "kind": "primary",
                "status": "completed",
                "ok": True,
                "source": "local",
                "requires_approval": False,
                "risk_level": "low",
                "permission_reason": "Read-only project inspection.",
                "metadata": {},
                "result": {
                    "ok": True,
                    "data": {
                        "tree": "app/\nmain.py",
                    },
                    "error": None,
                    "metadata": {},
                },
            }
        )
        run.approval_decisions.append(
            {
                "tool": "get_project_tree",
                "arguments": {
                    "path": ".",
                },
                "required": False,
                "approved": True,
                "risk_level": "low",
                "reason": "Read-only tool.",
                "source": "primary",
            }
        )
        run.recovery_events.append(
            {
                "type": "attempt",
                "original_tool": "read_file",
                "retry_tool": "list_files",
                "reason": "Original path did not exist.",
            }
        )
        run.step_review = {
            "completed_steps": ["Inspect the project tree."],
            "failed_steps": [],
            "skipped_steps": [],
            "remaining_steps": ["Read key files."],
            "summary": "Partial progress.",
        }
        run.replan_decision = {
            "should_replan": False,
            "reason": "No useful next action.",
            "next_steps": [],
        }
        run.final_answer = "This project is a desktop assistant agent runtime."

        summary = run.to_summary()

        expected_fields = {
            "run_id",
            "user_input",
            "memory_decision",
            "route_decision",
            "tool_use_decision",
            "skill_decision",
            "selected_skill",
            "plan",
            "revised_plan",
            "tool_calls_count",
            "tool_calls",
            "approval_decisions_count",
            "approval_decisions",
            "recovery_events_count",
            "recovery_events",
            "recovery_attempts",
            "step_review",
            "replan_decision",
            "final_answer",
        }

        self.assertTrue(expected_fields.issubset(summary.keys()))
        self.assertEqual(summary["user_input"], "Analyze this repository.")
        self.assertEqual(summary["selected_skill"], "repo_review")
        self.assertEqual(summary["tool_calls_count"], 1)
        self.assertEqual(summary["approval_decisions_count"], 1)
        self.assertEqual(summary["recovery_events_count"], 1)
        self.assertEqual(summary["recovery_attempts"], summary["recovery_events"])
        self.assertEqual(
            summary["final_answer"],
            "This project is a desktop assistant agent runtime.",
        )

    def test_tool_call_contract_contains_debug_and_eval_fields(self):
        run = RunContext(user_input="Use MCP echo.")

        run.tool_calls.append(
            {
                "tool": "mcp_tiny_echo",
                "tool_name": "mcp_tiny_echo",
                "arguments": {
                    "message": "hello",
                },
                "kind": "primary",
                "status": "completed",
                "ok": True,
                "source": "mcp:tiny",
                "requires_approval": False,
                "risk_level": "low",
                "permission_reason": "Allowed test MCP tool.",
                "metadata": {
                    "provider": "mcp:tiny",
                    "server": "tiny",
                    "original_tool": "echo",
                    "exposed_tool": "mcp_tiny_echo",
                },
                "mcp": {
                    "provider": "mcp:tiny",
                    "server": "tiny",
                    "original_tool": "echo",
                    "exposed_tool": "mcp_tiny_echo",
                },
                "result": {
                    "ok": True,
                    "data": {
                        "text": "Echo: hello",
                    },
                    "error": None,
                    "metadata": {
                        "provider": "mcp:tiny",
                        "server": "tiny",
                        "original_tool": "echo",
                        "exposed_tool": "mcp_tiny_echo",
                    },
                },
            }
        )

        summary = run.to_summary()
        call = summary["tool_calls"][0]

        expected_call_fields = {
            "tool",
            "tool_name",
            "arguments",
            "kind",
            "status",
            "ok",
            "source",
            "requires_approval",
            "risk_level",
            "permission_reason",
            "metadata",
            "result",
            "mcp",
        }

        self.assertTrue(expected_call_fields.issubset(call.keys()))
        self.assertEqual(call["tool"], "mcp_tiny_echo")
        self.assertEqual(call["tool_name"], "mcp_tiny_echo")
        self.assertEqual(call["status"], "completed")
        self.assertTrue(call["ok"])
        self.assertEqual(call["source"], "mcp:tiny")
        self.assertEqual(call["mcp"]["provider"], "mcp:tiny")
        self.assertEqual(call["mcp"]["server"], "tiny")
        self.assertEqual(call["mcp"]["original_tool"], "echo")
        self.assertEqual(call["mcp"]["exposed_tool"], "mcp_tiny_echo")


if __name__ == "__main__":
    unittest.main()