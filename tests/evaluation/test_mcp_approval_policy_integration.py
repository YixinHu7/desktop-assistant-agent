import unittest
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.memory import MemoryStore
from app.tools.registry import build_tool_definitions
from app.approval_policy import ApprovalPolicy
from app.tools.base import ToolDefinition


def dummy_tool(**kwargs):
    return {
        "ok": True,
        "data": kwargs,
        "error": None,
        "metadata": {},
    }


class MCPApprovalPolicyIntegrationTests(unittest.TestCase):
    def test_uses_dynamic_tool_definition_policy_for_real_mcp_tool(self):
        tool_definitions = {
            "mcp_tiny_echo": ToolDefinition(
                name="mcp_tiny_echo",
                schema={
                    "type": "function",
                    "name": "mcp_tiny_echo",
                    "description": "Test MCP echo tool.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                        },
                        "required": ["message"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
                function=dummy_tool,
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only tiny test echo tool.",
                source="mcp:tiny",
            )
        }

        policy = ApprovalPolicy(tool_definitions)
        decision = policy.decide("mcp_tiny_echo", {"message": "hello"})

        self.assertFalse(decision.required)
        self.assertEqual(decision.risk_level, "low")
        self.assertEqual(decision.reason, "Read-only tiny test echo tool.")

    def test_unknown_mcp_tool_still_requires_high_risk_approval(self):
        policy = ApprovalPolicy({})
        decision = policy.decide("mcp_unknown_delete_everything", {})

        self.assertTrue(decision.required)
        self.assertEqual(decision.risk_level, "high")
        self.assertEqual(decision.reason, "Unknown tools require approval by default.")

    def test_dynamic_high_risk_mcp_tool_requires_approval(self):
        tool_definitions = {
            "mcp_issue_create_ticket": ToolDefinition(
                name="mcp_issue_create_ticket",
                schema={
                    "type": "function",
                    "name": "mcp_issue_create_ticket",
                    "description": "Create a ticket through a real MCP server.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                        },
                        "required": ["title"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
                function=dummy_tool,
                requires_approval=True,
                risk_level="high",
                permission_reason="Creates external issue tracker state.",
                source="mcp:issue",
            )
        }

        policy = ApprovalPolicy(tool_definitions)
        decision = policy.decide("mcp_issue_create_ticket", {"title": "Bug"})

        self.assertTrue(decision.required)
        self.assertEqual(decision.risk_level, "high")
        self.assertEqual(decision.reason, "Creates external issue tracker state.")
    
    def test_registry_exposes_real_mcp_tool_approval_metadata(self):
        if shutil.which(sys.executable) is None:
            self.skipTest("Python executable is not available.")

        server_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "mcp_servers"
            / "tiny_mcp_server.py"
        )

        if not server_path.exists():
            self.skipTest("Tiny MCP server fixture is missing.")

        test_config = SimpleNamespace(
            enable_mcp_tools=True,
            enable_mock_mcp_tools=False,
            enable_real_mcp_tools=True,
            mcp_server_config_path="unused.json",
            tool_permissions=lambda: {
                "list_files": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only file listing.",
                },
                "read_file": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only file access.",
                },
                "create_note": {
                    "enabled": True,
                    "requires_approval": True,
                    "risk_level": "medium",
                    "reason": "Creates a local note.",
                },
                "open_app": {
                    "enabled": False,
                    "requires_approval": True,
                    "risk_level": "medium",
                    "reason": "Opens an app.",
                },
                "save_memory_fact": {
                    "enabled": True,
                    "requires_approval": True,
                    "risk_level": "medium",
                    "reason": "Saves memory.",
                },
                "get_project_tree": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only project tree.",
                },
                "find_file": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only file search.",
                },
                "search_files": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only file search.",
                },
                "read_multiple_files": {
                    "enabled": True,
                    "requires_approval": False,
                    "risk_level": "low",
                    "reason": "Read-only file access.",
                },
            },
        )

        from app.mcp.server_config import MCPServerConfig, MCPToolPolicy
        from app.mcp.real_provider import RealMCPProvider

        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(server_path)],
                enabled=True,
                allowed_tools=["echo"],
                tool_policies={
                    "echo": MCPToolPolicy(
                        requires_approval=False,
                        risk_level="low",
                        reason="Read-only tiny echo through registry.",
                    )
                },
            )
        )

        with patch("app.tools.registry.config", test_config), patch(
            "app.tools.registry.build_mcp_providers",
            return_value=[provider],
        ):
            tools = build_tool_definitions(MemoryStore())

        self.assertIn("mcp_tiny_echo", tools)

        tool = tools["mcp_tiny_echo"]
        self.assertFalse(tool.requires_approval)
        self.assertEqual(tool.risk_level, "low")
        self.assertEqual(
            tool.permission_reason,
            "Read-only tiny echo through registry.",
        )


if __name__ == "__main__":
    unittest.main()