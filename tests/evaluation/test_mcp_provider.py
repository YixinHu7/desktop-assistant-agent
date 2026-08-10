import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.mcp.mock_provider import MockMCPProvider


class MockMCPProviderTests(unittest.TestCase):
    def test_lists_tool_specs(self):
        provider = MockMCPProvider()
        specs = provider.list_tool_specs()
        names = {spec.name for spec in specs}

        self.assertIn("mcp_search_docs", names)
        self.assertIn("mcp_read_ticket", names)
        self.assertIn("mcp_list_resources", names)

    def test_call_tool_dispatches_to_search_docs(self):
        provider = MockMCPProvider()
        test_config = SimpleNamespace(
            eval_mode=True,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = provider.call_tool(
                "mcp_search_docs",
                {
                    "query": "agent runtime architecture",
                    "max_results": 5,
                },
            )

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["data"]["match_count"], 1)

    def test_call_tool_rejects_unknown_tool(self):
        provider = MockMCPProvider()
        test_config = SimpleNamespace(
            eval_mode=True,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = provider.call_tool("mcp_unknown_tool", {})

        self.assertFalse(result["ok"])
        self.assertIn("Unknown mock MCP tool", result["error"])


if __name__ == "__main__":
    unittest.main()