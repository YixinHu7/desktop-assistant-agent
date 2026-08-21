import unittest

from app.mcp.telemetry import build_mcp_telemetry


class MCPExecutionTelemetryTests(unittest.TestCase):
    def test_builds_real_mcp_telemetry(self):
        telemetry = build_mcp_telemetry(
            tool_name="mcp_tiny_echo",
            tool_source="mcp:tiny",
            result_metadata={
                "provider": "mcp:tiny",
                "server": "tiny",
                "original_tool": "echo",
                "exposed_tool": "mcp_tiny_echo",
            },
        )

        self.assertEqual(
            telemetry,
            {
                "provider": "mcp:tiny",
                "server": "tiny",
                "original_tool": "echo",
                "exposed_tool": "mcp_tiny_echo",
            },
        )

    def test_builds_mock_mcp_telemetry(self):
        telemetry = build_mcp_telemetry(
            tool_name="mcp_read_ticket",
            tool_source="mock_mcp",
            result_metadata={
                "provider": "mock_mcp",
                "tool": "mcp_read_ticket",
            },
        )

        self.assertEqual(
            telemetry,
            {
                "provider": "mock_mcp",
                "original_tool": "mcp_read_ticket",
                "exposed_tool": "mcp_read_ticket",
            },
        )

    def test_returns_none_for_local_tool(self):
        telemetry = build_mcp_telemetry(
            tool_name="read_file",
            tool_source="local",
            result_metadata={
                "tool": "read_file",
            },
        )

        self.assertIsNone(telemetry)

    def test_treats_mcp_prefixed_tool_as_mcp_even_without_provider(self):
        telemetry = build_mcp_telemetry(
            tool_name="mcp_unknown_tool",
            tool_source=None,
            result_metadata={},
        )

        self.assertEqual(
            telemetry,
            {
                "provider": None,
                "original_tool": "mcp_unknown_tool",
                "exposed_tool": "mcp_unknown_tool",
            },
        )


if __name__ == "__main__":
    unittest.main()