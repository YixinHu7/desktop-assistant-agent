import shutil
import sys
import unittest
from pathlib import Path

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig, MCPToolPolicy


class MCPToolNamespacingTests(unittest.TestCase):
    def setUp(self):
        if shutil.which(sys.executable) is None:
            self.skipTest("Python executable is not available.")

        fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "mcp_servers"

        self.tiny_server_path = fixtures_root / "tiny_mcp_server.py"
        self.collision_server_path = fixtures_root / "collision_mcp_server.py"

        if not self.tiny_server_path.exists():
            self.skipTest("Tiny MCP server fixture is missing.")

        if not self.collision_server_path.exists():
            self.skipTest("Collision MCP server fixture is missing.")

    def test_same_tool_name_from_different_servers_gets_distinct_names(self):
        provider_a = RealMCPProvider(
            MCPServerConfig(
                name="tiny-a",
                command=sys.executable,
                args=[str(self.tiny_server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )
        provider_b = RealMCPProvider(
            MCPServerConfig(
                name="tiny-b",
                command=sys.executable,
                args=[str(self.tiny_server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        specs_a = provider_a.list_tool_specs()
        specs_b = provider_b.list_tool_specs()

        names_a = {spec.name for spec in specs_a}
        names_b = {spec.name for spec in specs_b}

        self.assertEqual(names_a, {"mcp_tiny_a_echo"})
        self.assertEqual(names_b, {"mcp_tiny_b_echo"})
        self.assertTrue(names_a.isdisjoint(names_b))

    def test_mcp_tool_names_do_not_collide_with_local_tool_names(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="collision",
                command=sys.executable,
                args=[str(self.collision_server_path)],
                enabled=True,
                allowed_tools=["read_file", "open_app"],
                tool_policies={
                    "read_file": MCPToolPolicy(
                        requires_approval=True,
                        risk_level="high",
                        reason="Collision test tool should still be namespaced.",
                    ),
                    "open_app": MCPToolPolicy(
                        requires_approval=True,
                        risk_level="high",
                        reason="Collision test tool should still be namespaced.",
                    ),
                },
            )
        )

        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertIn("mcp_collision_read_file", names)
        self.assertIn("mcp_collision_open_app", names)
        self.assertNotIn("read_file", names)
        self.assertNotIn("open_app", names)

    def test_sanitizes_server_and_tool_names_in_exposed_name(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="Tiny Server!",
                command=sys.executable,
                args=[str(self.tiny_server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertEqual(names, {"mcp_tiny_server_echo"})

    def test_call_tool_uses_original_tool_name_after_namespacing(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny-a",
                command=sys.executable,
                args=[str(self.tiny_server_path)],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        provider.list_tool_specs()

        result = provider.call_tool(
            "mcp_tiny_a_echo",
            {"message": "hello"},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["original_tool"], "echo")
        self.assertIn("Echo: hello", result["data"]["text"])


if __name__ == "__main__":
    unittest.main()