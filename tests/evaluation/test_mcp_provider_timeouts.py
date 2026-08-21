import asyncio
import unittest

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig


class SlowCallProvider(RealMCPProvider):
    async def _call_tool_async(self, tool_name, arguments):
        await asyncio.sleep(2.0)
        return {
            "ok": True,
            "data": {"unexpected": True},
            "error": None,
            "metadata": {},
        }


class SlowListProvider(RealMCPProvider):
    async def _list_tool_specs_async(self):
        await asyncio.sleep(2.0)
        return []


class MCPProviderTimeoutTests(unittest.TestCase):
    def test_call_tool_times_out(self):
        provider = SlowCallProvider(
            MCPServerConfig(
                name="slow",
                command="unused",
                args=[],
                enabled=True,
                allowed_tools=["slow_echo"],
                list_timeout_seconds=5.0,
                call_timeout_seconds=0.1,
            )
        )

        provider._tool_name_map["mcp_slow_slow_echo"] = "slow_echo"

        result = provider.call_tool(
            "mcp_slow_slow_echo",
            {"message": "hello"},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"],
            "MCP tool execution timed out or failed.",
        )
        self.assertTrue(result["metadata"]["real_mcp_error"])
        self.assertEqual(result["metadata"]["provider"], "mcp:slow")
        self.assertEqual(result["metadata"]["server"], "slow")
        self.assertEqual(result["metadata"]["original_tool"], "slow_echo")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_slow_slow_echo")
        self.assertEqual(result["metadata"]["error_type"], "TimeoutError")

    def test_list_tool_specs_times_out_and_records_diagnostics(self):
        provider = SlowListProvider(
            MCPServerConfig(
                name="slow-list",
                command="unused",
                args=[],
                enabled=True,
                allowed_tools=["echo"],
                list_timeout_seconds=0.1,
                call_timeout_seconds=5.0,
            )
        )

        specs = provider.list_tool_specs()
        diagnostics = provider.discovery_diagnostics()

        self.assertEqual(specs, [])
        self.assertEqual(diagnostics["status"], "error")
        self.assertEqual(diagnostics["provider_name"], "mcp:slow-list")
        self.assertEqual(diagnostics["server_name"], "slow-list")
        self.assertEqual(diagnostics["allowed_tools"], ["echo"])
        self.assertEqual(diagnostics["error_type"], "TimeoutError")
        self.assertEqual(
            diagnostics["error_message"],
            "MCP tool listing timed out or failed.",
        )

    def test_list_tool_specs_records_error_for_missing_command(self):
        provider = RealMCPProvider(
            MCPServerConfig(
                name="missing",
                command="definitely-not-a-real-command",
                args=[],
                enabled=True,
                allowed_tools=["echo"],
                list_timeout_seconds=0.1,
                call_timeout_seconds=0.1,
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


if __name__ == "__main__":
    unittest.main()