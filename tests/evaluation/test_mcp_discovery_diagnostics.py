import shutil
import sys
import unittest
from pathlib import Path

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig


class MCPDiscoveryDiagnosticsTests(unittest.TestCase):
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

    def test_records_successful_discovery_counts(self):
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
        diagnostics = provider.discovery_diagnostics()

        self.assertEqual([spec.name for spec in specs], ["mcp_tiny_echo"])
        self.assertEqual(diagnostics["status"], "ok")
        self.assertEqual(diagnostics["total_tools"], 2)
        self.assertEqual(diagnostics["allowed_tools"], ["echo"])
        self.assertIn("echo", diagnostics["discovered_tools"])
        self.assertIn("get_status", diagnostics["discovered_tools"])
        self.assertEqual(diagnostics["registered_tools"], ["mcp_tiny_echo"])
        self.assertEqual(diagnostics["filtered_tools"], ["get_status"])
        self.assertIsNone(diagnostics["error_type"])
        self.assertIsNone(diagnostics["error_message"])

    def test_records_error_when_server_cannot_start(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="missing",
                command="definitely-not-a-real-command",
                args=[],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

        specs = provider.list_tool_specs()
        diagnostics = provider.discovery_diagnostics()

        self.assertEqual(specs, [])
        self.assertEqual(diagnostics["status"], "error")
        self.assertEqual(diagnostics["provider_name"], "mcp:missing")
        self.assertEqual(diagnostics["server_name"], "missing")
        self.assertEqual(diagnostics["allowed_tools"], ["echo"])
        self.assertIsNotNone(diagnostics["error_type"])
        self.assertIsNotNone(diagnostics["error_message"])

    def test_records_empty_registration_when_allowlist_is_empty(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
                allowed_tools=[],
            )
        )

        specs = provider.list_tool_specs()
        diagnostics = provider.discovery_diagnostics()

        self.assertEqual(specs, [])
        self.assertEqual(diagnostics["status"], "ok")
        self.assertEqual(diagnostics["total_tools"], 2)
        self.assertEqual(diagnostics["registered_tools"], [])
        self.assertEqual(set(diagnostics["filtered_tools"]), {"echo", "get_status"})


if __name__ == "__main__":
    unittest.main()