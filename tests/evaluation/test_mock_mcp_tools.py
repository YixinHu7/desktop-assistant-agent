import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tools.mock_mcp_tools import (
    mcp_list_resources,
    mcp_read_ticket,
    mcp_search_docs,
)


class MockMCPToolsTests(unittest.TestCase):
    def test_search_docs_returns_matching_documents(self):
        test_config = SimpleNamespace(
            eval_mode=True,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = mcp_search_docs("agent runtime architecture")

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["data"]["match_count"], 1)

    def test_read_ticket_returns_known_ticket(self):
        test_config = SimpleNamespace(
            eval_mode=True,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = mcp_read_ticket("TICKET-123")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["ticket"]["ticket_id"], "TICKET-123")

    def test_read_ticket_fails_for_missing_ticket(self):
        test_config = SimpleNamespace(
            eval_mode=True,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = mcp_read_ticket("TICKET-999")

        self.assertFalse(result["ok"])
        self.assertIn("Ticket not found", result["error"])
        self.assertEqual(result["metadata"]["ticket_id"], "TICKET-999")

    def test_mock_mcp_tools_are_disabled_outside_eval_mode(self):
        test_config = SimpleNamespace(
            eval_mode=False,
            enable_mock_mcp_tools=True,
        )

        with patch("app.mcp.mock_provider.config", test_config):
            result = mcp_list_resources()

        self.assertFalse(result["ok"])
        self.assertTrue(result["metadata"]["mock_mcp_disabled"])


if __name__ == "__main__":
    unittest.main()