import tempfile
import unittest
from pathlib import Path

from app.mcp.server_config import load_mcp_server_configs


class MCPServerConfigValidationTests(unittest.TestCase):
    def _write_config(self, content: str) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        path = Path(temp_dir.name) / "mcp_servers.json"
        path.write_text(content, encoding="utf-8")

        return str(path)

    def test_loads_valid_config(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "args": ["server.py"],
                  "env": {"A": "B"},
                  "enabled": true,
                  "allowed_tools": ["echo"],
                  "list_timeout_seconds": 3.5,
                  "call_timeout_seconds": 7.0,
                  "tool_policies": {
                    "echo": {
                      "requires_approval": false,
                      "risk_level": "low",
                      "reason": "Read-only echo."
                    }
                  }
                }
              ]
            }
            """
        )

        configs = load_mcp_server_configs(path)

        self.assertEqual(len(configs), 1)

        config = configs[0]
        self.assertEqual(config.name, "tiny")
        self.assertEqual(config.command, "python")
        self.assertEqual(config.args, ["server.py"])
        self.assertEqual(config.env, {"A": "B"})
        self.assertTrue(config.enabled)
        self.assertEqual(config.allowed_tools, ["echo"])
        self.assertEqual(config.list_timeout_seconds, 3.5)
        self.assertEqual(config.call_timeout_seconds, 7.0)
        self.assertFalse(config.tool_policies["echo"].requires_approval)
        self.assertEqual(config.tool_policies["echo"].risk_level, "low")
        self.assertEqual(config.tool_policies["echo"].reason, "Read-only echo.")

    def test_missing_config_file_returns_empty_list(self):
        configs = load_mcp_server_configs("definitely_missing_mcp_config.json")

        self.assertEqual(configs, [])

    def test_rejects_non_list_servers_field(self):
        path = self._write_config(
            """
            {
              "servers": {
                "name": "tiny",
                "command": "python"
              }
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "servers.*list"):
            load_mcp_server_configs(path)

    def test_rejects_non_object_server_entry(self):
        path = self._write_config(
            """
            {
              "servers": [
                "not-an-object"
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "Each MCP server config"):
            load_mcp_server_configs(path)

    def test_rejects_missing_server_name(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "command": "python"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "requires field 'name'"):
            load_mcp_server_configs(path)

    def test_rejects_empty_server_name(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": " ",
                  "command": "python"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "name.*cannot be empty"):
            load_mcp_server_configs(path)

    def test_rejects_missing_command(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "requires field 'command'"):
            load_mcp_server_configs(path)

    def test_rejects_empty_command(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": ""
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "command.*cannot be empty"):
            load_mcp_server_configs(path)

    def test_rejects_non_boolean_enabled(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "enabled": "false"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "enabled.*boolean"):
            load_mcp_server_configs(path)

    def test_rejects_non_list_args(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "args": "server.py"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "args.*list"):
            load_mcp_server_configs(path)

    def test_rejects_non_object_env(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "env": ["A=B"]
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "env.*object"):
            load_mcp_server_configs(path)

    def test_rejects_non_list_allowed_tools(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": "echo"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "allowed_tools.*list"):
            load_mcp_server_configs(path)

    def test_rejects_non_string_allowed_tool_name(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo", 123]
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "allowed_tools.*only strings"):
            load_mcp_server_configs(path)

    def test_rejects_empty_allowed_tool_name(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo", " "]
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "allowed_tools.*empty"):
            load_mcp_server_configs(path)

    def test_deduplicates_allowed_tools(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo", "echo", "get_status"]
                }
              ]
            }
            """
        )

        configs = load_mcp_server_configs(path)

        self.assertEqual(configs[0].allowed_tools, ["echo", "get_status"])

    def test_rejects_non_object_tool_policies(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "tool_policies": ["echo"]
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "tool_policies.*object"):
            load_mcp_server_configs(path)

    def test_rejects_empty_tool_policy_name(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    " ": {
                      "requires_approval": true
                    }
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "policy names cannot be empty"):
            load_mcp_server_configs(path)

    def test_rejects_tool_policy_for_non_allowed_tool(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    "delete_file": {
                      "requires_approval": true,
                      "risk_level": "high"
                    }
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "not allowed"):
            load_mcp_server_configs(path)

    def test_rejects_non_object_tool_policy(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    "echo": "low"
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "policy for 'echo'.*object"):
            load_mcp_server_configs(path)

    def test_rejects_non_boolean_requires_approval(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    "echo": {
                      "requires_approval": "false"
                    }
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "requires_approval.*boolean"):
            load_mcp_server_configs(path)

    def test_rejects_invalid_risk_level(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    "echo": {
                      "risk_level": "dangerous"
                    }
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "risk_level.*must be one of"):
            load_mcp_server_configs(path)

    def test_rejects_empty_policy_reason(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "allowed_tools": ["echo"],
                  "tool_policies": {
                    "echo": {
                      "reason": " "
                    }
                  }
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "reason.*cannot be empty"):
            load_mcp_server_configs(path)

    def test_rejects_negative_list_timeout(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "list_timeout_seconds": -1
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "greater than 0"):
            load_mcp_server_configs(path)

    def test_rejects_zero_call_timeout(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "call_timeout_seconds": 0
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "greater than 0"):
            load_mcp_server_configs(path)

    def test_rejects_non_numeric_timeout(self):
        path = self._write_config(
            """
            {
              "servers": [
                {
                  "name": "tiny",
                  "command": "python",
                  "call_timeout_seconds": "soon"
                }
              ]
            }
            """
        )

        with self.assertRaisesRegex(ValueError, "positive number"):
            load_mcp_server_configs(path)


if __name__ == "__main__":
    unittest.main()