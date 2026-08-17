import unittest

from app.approval_policy import ApprovalPolicy
from app.tools.base import ToolDefinition
from app.tools.results import tool_success


def dummy_readonly_mcp_tool(**kwargs):
    return tool_success(
        data={"message": "readonly ok", "arguments": kwargs},
        metadata={"tool": "mcp_test_readonly", "provider": "mcp:test"},
    )


def dummy_high_risk_mcp_tool(**kwargs):
    return tool_success(
        data={"message": "high risk executed", "arguments": kwargs},
        metadata={"tool": "mcp_test_write", "provider": "mcp:test"},
    )


class MCPExecutionRegressionTests(unittest.TestCase):
    def test_readonly_real_mcp_tool_policy_does_not_require_approval(self):
        tools = {
            "mcp_test_readonly": ToolDefinition(
                name="mcp_test_readonly",
                schema={
                    "type": "function",
                    "name": "mcp_test_readonly",
                    "description": "Read-only MCP test tool.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
                function=dummy_readonly_mcp_tool,
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only MCP regression test tool.",
                source="mcp:test",
            )
        }

        decision = ApprovalPolicy(tools).decide("mcp_test_readonly", {})

        self.assertFalse(decision.required)
        self.assertEqual(decision.risk_level, "low")
        self.assertEqual(decision.reason, "Read-only MCP regression test tool.")

    def test_high_risk_real_mcp_tool_policy_requires_approval(self):
        tools = {
            "mcp_test_write": ToolDefinition(
                name="mcp_test_write",
                schema={
                    "type": "function",
                    "name": "mcp_test_write",
                    "description": "High-risk MCP write test tool.",
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
                function=dummy_high_risk_mcp_tool,
                requires_approval=True,
                risk_level="high",
                permission_reason="Writes to an external MCP system.",
                source="mcp:test",
            )
        }

        decision = ApprovalPolicy(tools).decide(
            "mcp_test_write",
            {"title": "Create external item"},
        )

        self.assertTrue(decision.required)
        self.assertEqual(decision.risk_level, "high")
        self.assertEqual(decision.reason, "Writes to an external MCP system.")

    def test_unknown_mcp_tool_cannot_bypass_approval(self):
        decision = ApprovalPolicy({}).decide(
            "mcp_unknown_external_delete",
            {"id": "123"},
        )

        self.assertTrue(decision.required)
        self.assertEqual(decision.risk_level, "high")
        self.assertEqual(
            decision.reason,
            "Unknown tools require approval by default.",
        )


if __name__ == "__main__":
    unittest.main()