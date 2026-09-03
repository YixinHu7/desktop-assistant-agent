import json
import tempfile
import unittest
from pathlib import Path

from scripts.inspect_run import (
    load_run_summaries,
    render_run_summary,
    select_run,
)


class InspectRunTests(unittest.TestCase):
    def test_loads_run_summary_events_from_trace_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "traces.jsonl"

            trace_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "event_type": "route_decision",
                                "payload": {"route": "chat"},
                            }
                        ),
                        json.dumps(
                            {
                                "event_type": "run_summary",
                                "payload": {
                                    "run_id": "run-1",
                                    "final_answer": "First answer.",
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "event_type": "run_summary",
                                "payload": {
                                    "run_id": "run-2",
                                    "final_answer": "Second answer.",
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            summaries = load_run_summaries(trace_path)

        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["run_id"], "run-1")
        self.assertEqual(summaries[1]["run_id"], "run-2")

    def test_select_run_defaults_to_latest(self):
        run = select_run(
            [
                {"run_id": "run-1"},
                {"run_id": "run-2"},
            ]
        )

        self.assertEqual(run["run_id"], "run-2")

    def test_select_run_by_id(self):
        run = select_run(
            [
                {"run_id": "run-1"},
                {"run_id": "run-2"},
            ],
            run_id="run-1",
        )

        self.assertEqual(run["run_id"], "run-1")

    def test_render_run_summary_includes_key_sections(self):
        markdown = render_run_summary(
            {
                "run_id": "run-1",
                "user_input": "Analyze this repo.",
                "route_decision": {
                    "route": "plan",
                    "reason": "Repository analysis requires tools.",
                },
                "tool_use_decision": {
                    "should_use_tools": True,
                    "likely_tools": ["get_project_tree"],
                    "avoid_tools": ["open_app"],
                    "requires_grounding": True,
                },
                "skill_decision": {
                    "should_use_skill": True,
                    "selected_skill": "repo_review",
                },
                "selected_skill": "repo_review",
                "plan": {
                    "goal": "Analyze architecture.",
                    "steps": [
                        {"step": "Inspect project tree."},
                        {"step": "Summarize main components."},
                    ],
                },
                "tool_calls": [
                    {
                        "tool": "get_project_tree",
                        "kind": "primary",
                        "status": "completed",
                        "ok": True,
                        "source": "local",
                        "arguments": {
                            "path": ".",
                            "max_depth": 3,
                        },
                        "result": {
                            "ok": True,
                            "data": {
                                "tree": "app/\nmain.py",
                            },
                            "error": None,
                        },
                    },
                    {
                        "tool": "mcp_tiny_echo",
                        "kind": "primary",
                        "status": "completed",
                        "ok": True,
                        "source": "mcp:tiny",
                        "arguments": {
                            "message": "hello",
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
                        },
                    },
                ],
                "approval_decisions": [
                    {
                        "tool": "get_project_tree",
                        "required": False,
                        "approved": True,
                        "risk_level": "low",
                        "reason": "Low risk.",
                    }
                ],
                "recovery_events": [],
                "step_review": {
                    "completed_steps": ["Inspect project tree."],
                    "failed_steps": [],
                    "skipped_steps": [],
                    "remaining_steps": ["Read key files."],
                    "summary": "Partial progress.",
                },
                "replan_decision": {
                    "should_replan": False,
                    "reason": "No useful next tool action.",
                },
                "final_answer": "This project is a desktop assistant agent runtime.",
            }
        )

        self.assertIn("Run Summary", markdown)
        self.assertIn("Route: plan", markdown)
        self.assertIn("Skill selected: repo_review", markdown)
        self.assertIn("Plan", markdown)
        self.assertIn("get_project_tree", markdown)
        self.assertIn("mcp.provider: mcp:tiny", markdown)
        self.assertIn("Approvals", markdown)
        self.assertIn("Execution Review", markdown)
        self.assertIn("Remaining_steps".lower(), markdown.lower())
        self.assertIn("Final Answer", markdown)


if __name__ == "__main__":
    unittest.main()