import shutil
import sys
import unittest
from pathlib import Path

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig, MCPToolPolicy

class RealMCPProviderTests(unittest.TestCase):
    def setUp(self):
        if shutil.which(sys.executable) is None:
            self.skipTest("Python executable is not available.")

        self.server_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "mcp_servers"
            / "tiny_mcp_server.py"
        )

        if not self.server_path.exists():
            self.skipTest("Tiny MCP server fixture is missing.")

    def test_lists_tools_from_stdio_server(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo", "get_status"],
            )
        )

        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertIn("mcp_tiny_echo", names)
        self.assertIn("mcp_tiny_get_status", names)
        
        for spec in specs:
            self.assertEqual(spec.parameters["type"], "object")
            self.assertIn("properties", spec.parameters)
            self.assertIn("required", spec.parameters)
            self.assertFalse(spec.parameters["additionalProperties"])

    def test_calls_tool_from_stdio_server(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo", "get_status"],
            )
        )

        provider.list_tool_specs()

        result = provider.call_tool(
            "mcp_tiny_echo",
            {"message": "hello"},
        )

        self.assertTrue(result["ok"])
        self.assertIn("Echo: hello", result["data"]["text"])
    
    def test_allowed_tool_policy_metadata_is_applied(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
                tool_policies={
                    "echo": MCPToolPolicy(
                        requires_approval=False,
                        risk_level="low",
                        reason="Read-only echo test tool.",
                    )
                },
            )
        )

        specs = provider.list_tool_specs()
        self.assertEqual(len(specs), 1)

        spec = specs[0]
        self.assertEqual(spec.name, "mcp_tiny_echo")
        self.assertFalse(spec.requires_approval)
        self.assertEqual(spec.risk_level, "low")
        self.assertEqual(spec.permission_reason, "Read-only echo test tool.")
    
    def test_filters_out_tools_not_in_allowlist(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertEqual(names, {"mcp_tiny_echo"})
        self.assertNotIn("mcp_tiny_get_status", names)
    
    def test_blocks_non_namespaced_original_tool_call(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        result = provider.call_tool(
            "echo",
            {"message": "hello"},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["metadata"]["error_type"], "MCPToolNotAllowed")
        self.assertTrue(result["metadata"]["mcp_guardrail_blocked"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["exposed_tool"], "echo")
        self.assertEqual(result["metadata"]["original_tool"], "echo")

    def test_blocks_namespaced_tool_not_in_allowlist(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        result = provider.call_tool(
            "mcp_tiny_get_status",
            {},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["metadata"]["error_type"], "MCPToolNotAllowed")
        self.assertTrue(result["metadata"]["mcp_guardrail_blocked"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_tiny_get_status")
        self.assertEqual(result["metadata"]["original_tool"], "get_status")

    def test_blocks_tool_for_different_server_namespace(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        result = provider.call_tool(
            "mcp_other_echo",
            {"message": "hello"},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["metadata"]["error_type"], "MCPToolNotAllowed")
        self.assertTrue(result["metadata"]["mcp_guardrail_blocked"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_other_echo")
        self.assertEqual(result["metadata"]["original_tool"], "mcp_other_echo")

    def test_allows_namespaced_allowed_tool_before_discovery(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        result = provider.call_tool(
            "mcp_tiny_echo",
            {"message": "hello"},
        )

        self.assertTrue(result["ok"])
        self.assertIn("Echo: hello", result["data"]["text"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_tiny_echo")
        self.assertEqual(result["metadata"]["original_tool"], "echo")

    def test_registered_allowed_tool_still_executes(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        provider.list_tool_specs()

        result = provider.call_tool(
            "mcp_tiny_echo",
            {"message": "hello"},
        )

        self.assertTrue(result["ok"])
        self.assertIn("Echo: hello", result["data"]["text"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_tiny_echo")
        self.assertEqual(result["metadata"]["original_tool"], "echo")


if __name__ == "__main__":
    unittest.main()