import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.tools.registry import build_tool_definitions


def _disabled_permission(
    requires_approval: bool = False,
    risk_level: str = "low",
    reason: str = "Disabled in test.",
):
    return {
        "enabled": False,
        "requires_approval": requires_approval,
        "risk_level": risk_level,
        "reason": reason,
    }


def _test_permissions():
    return {
        "list_files": _disabled_permission(),
        "read_file": _disabled_permission(),
        "get_project_tree": _disabled_permission(),
        "find_file": _disabled_permission(),
        "search_files": _disabled_permission(),
        "read_multiple_files": _disabled_permission(),
        "create_note": _disabled_permission(
            requires_approval=True,
            risk_level="medium",
            reason="Creates a note.",
        ),
        "save_memory_fact": _disabled_permission(
            requires_approval=True,
            risk_level="medium",
            reason="Writes memory.",
        ),
        "open_app": _disabled_permission(
            requires_approval=True,
            risk_level="medium",
            reason="Opens an application.",
        ),
    }


class MCPRegistryIntegrationTests(unittest.TestCase):
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

    def _write_server_config(self, servers: list[dict]) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        config_path = Path(temp_dir.name) / "mcp_servers.json"
        config_path.write_text(
            json.dumps({"servers": servers}),
            encoding="utf-8",
        )

        return str(config_path)

    def _build_tools_with_config(self, config_path: str):
        registry_config = SimpleNamespace(
            tool_permissions=_test_permissions,
        )

        factory_config = SimpleNamespace(
            enable_mcp_tools=True,
            enable_mock_mcp_tools=False,
            enable_real_mcp_tools=True,
            mcp_server_config_path=config_path,
        )

        with patch("app.tools.registry.config", registry_config), patch(
            "app.mcp.factory.config",
            factory_config,
        ):
            return build_tool_definitions(memory_store=None)

    def test_registers_real_mcp_tool_from_config(self):
        config_path = self._write_server_config(
            [
                {
                    "name": "tiny",
                    "command": sys.executable,
                    "args": [str(self.server_path)],
                    "enabled": True,
                    "allowed_tools": ["echo"],
                    "list_timeout_seconds": 5.0,
                    "call_timeout_seconds": 10.0,
                    "tool_policies": {
                        "echo": {
                            "requires_approval": False,
                            "risk_level": "low",
                            "reason": "Read-only registry integration echo.",
                        }
                    },
                }
            ]
        )

        tools = self._build_tools_with_config(config_path)

        self.assertEqual(sorted(tools.keys()), ["mcp_tiny_echo"])

        tool = tools["mcp_tiny_echo"]
        self.assertEqual(tool.name, "mcp_tiny_echo")
        self.assertEqual(tool.source, "mcp:tiny")
        self.assertFalse(tool.requires_approval)
        self.assertEqual(tool.risk_level, "low")
        self.assertEqual(
            tool.permission_reason,
            "Read-only registry integration echo.",
        )

        self.assertEqual(tool.schema["type"], "function")
        self.assertEqual(tool.schema["name"], "mcp_tiny_echo")
        self.assertTrue(tool.schema["strict"])

        parameters = tool.schema["parameters"]
        self.assertEqual(parameters["type"], "object")
        self.assertIn("properties", parameters)
        self.assertIn("required", parameters)
        self.assertFalse(parameters["additionalProperties"])

    def test_registered_real_mcp_tool_function_executes_provider_call(self):
        config_path = self._write_server_config(
            [
                {
                    "name": "tiny",
                    "command": sys.executable,
                    "args": [str(self.server_path)],
                    "enabled": True,
                    "allowed_tools": ["echo"],
                    "tool_policies": {
                        "echo": {
                            "requires_approval": False,
                            "risk_level": "low",
                            "reason": "Read-only registry integration echo.",
                        }
                    },
                }
            ]
        )

        tools = self._build_tools_with_config(config_path)

        result = tools["mcp_tiny_echo"].function(message="hello")

        self.assertTrue(result["ok"])
        self.assertIn("Echo: hello", result["data"]["text"])
        self.assertEqual(result["metadata"]["provider"], "mcp:tiny")
        self.assertEqual(result["metadata"]["server"], "tiny")
        self.assertEqual(result["metadata"]["original_tool"], "echo")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_tiny_echo")

    def test_does_not_register_tools_from_disabled_server(self):
        config_path = self._write_server_config(
            [
                {
                    "name": "disabled",
                    "command": sys.executable,
                    "args": [str(self.server_path)],
                    "enabled": False,
                    "allowed_tools": ["echo"],
                    "tool_policies": {
                        "echo": {
                            "requires_approval": False,
                            "risk_level": "low",
                            "reason": "Disabled server echo.",
                        }
                    },
                },
                {
                    "name": "tiny",
                    "command": sys.executable,
                    "args": [str(self.server_path)],
                    "enabled": True,
                    "allowed_tools": ["echo"],
                    "tool_policies": {
                        "echo": {
                            "requires_approval": False,
                            "risk_level": "low",
                            "reason": "Enabled server echo.",
                        }
                    },
                },
            ]
        )

        tools = self._build_tools_with_config(config_path)

        self.assertIn("mcp_tiny_echo", tools)
        self.assertNotIn("mcp_disabled_echo", tools)

    def test_does_not_register_tools_not_in_allowlist(self):
        config_path = self._write_server_config(
            [
                {
                    "name": "tiny",
                    "command": sys.executable,
                    "args": [str(self.server_path)],
                    "enabled": True,
                    "allowed_tools": ["echo"],
                    "tool_policies": {
                        "echo": {
                            "requires_approval": False,
                            "risk_level": "low",
                            "reason": "Allowed echo.",
                        }
                    },
                }
            ]
        )

        tools = self._build_tools_with_config(config_path)

        self.assertIn("mcp_tiny_echo", tools)
        self.assertNotIn("mcp_tiny_get_status", tools)


if __name__ == "__main__":
    unittest.main()
