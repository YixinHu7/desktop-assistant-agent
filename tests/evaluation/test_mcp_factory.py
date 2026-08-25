import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.mcp.factory import build_mcp_providers
from app.mcp.mock_provider import MockMCPProvider
from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import load_mcp_server_configs


class MCPFactoryTests(unittest.TestCase):
    def test_returns_no_providers_when_mcp_disabled(self):
        test_config = SimpleNamespace(
            enable_mcp_tools=False,
            enable_mock_mcp_tools=True,
            enable_real_mcp_tools=True,
            mcp_server_config_path="missing.json",
        )

        with patch("app.mcp.factory.config", test_config):
            providers = build_mcp_providers()

        self.assertEqual(providers, [])

    def test_returns_mock_provider_when_enabled(self):
        test_config = SimpleNamespace(
            enable_mcp_tools=True,
            enable_mock_mcp_tools=True,
            enable_real_mcp_tools=False,
            mcp_server_config_path="missing.json",
        )

        with patch("app.mcp.factory.config", test_config):
            providers = build_mcp_providers()

        self.assertEqual(len(providers), 1)
        self.assertIsInstance(providers[0], MockMCPProvider)

    def test_loads_real_provider_configs_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "mcp_servers.json"
            config_path.write_text(
                """
                {
                  "servers": [
                    {
                      "name": "example",
                      "command": "python",
                      "args": ["server.py"],
                      "enabled": true,
                      "allowed_tools": ["echo"],
                      "tool_policies": {
                        "echo": {
                        "requires_approval": false,
                        "risk_level": "low",
                        "reason": "Read-only test tool."
                        }
                      }
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            test_config = SimpleNamespace(
                enable_mcp_tools=True,
                enable_mock_mcp_tools=False,
                enable_real_mcp_tools=True,
                mcp_server_config_path=str(config_path),
            )

            with patch("app.mcp.factory.config", test_config):
                providers = build_mcp_providers()

        self.assertEqual(len(providers), 1)
        self.assertIsInstance(providers[0], RealMCPProvider)
        self.assertEqual(providers[0].server_config.name, "example")
        self.assertEqual(providers[0].server_config.allowed_tools, ["echo"])
        self.assertFalse(providers[0].server_config.tool_policies["echo"].requires_approval)
        self.assertEqual(providers[0].server_config.tool_policies["echo"].risk_level, "low")
        self.assertEqual(providers[0].server_config.list_timeout_seconds, 5.0)
        self.assertEqual(providers[0].server_config.call_timeout_seconds, 10.0)

    def test_load_mcp_server_configs_accepts_missing_file(self):
        configs = load_mcp_server_configs("definitely_missing_mcp_config.json")

        self.assertEqual(configs, [])


if __name__ == "__main__":
    unittest.main()