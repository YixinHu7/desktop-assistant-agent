import shutil
import sys
import unittest
from pathlib import Path

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig


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
            )
        )

        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertIn("mcp_tiny_echo", names)
        self.assertIn("mcp_tiny_get_status", names)

    def test_calls_tool_from_stdio_server(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command=sys.executable,
                args=[str(self.server_path)],
                enabled=True,
            )
        )

        provider.list_tool_specs()

        result = provider.call_tool(
            "mcp_tiny_echo",
            {"message": "hello"},
        )

        self.assertTrue(result["ok"])
        self.assertIn("Echo: hello", result["data"]["text"])


if __name__ == "__main__":
    unittest.main()