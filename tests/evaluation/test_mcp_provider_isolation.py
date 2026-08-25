import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.mcp.provider import MCPToolSpec
from app.tools.registry import build_tool_definitions
from app.tools.results import tool_success


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


class BrokenProvider:
    provider_name = "mcp:broken"

    def list_tool_specs(self):
        raise RuntimeError("MCP discovery failed.")

    def call_tool(self, tool_name: str, arguments: dict):
        return {
            "ok": False,
            "error": "Should not be called.",
            "metadata": {
                "provider": self.provider_name,
                "tool": tool_name,
            },
        }


class EmptyProvider:
    provider_name = "mcp:empty"

    def list_tool_specs(self):
        return []

    def call_tool(self, tool_name: str, arguments: dict):
        return {
            "ok": False,
            "error": "Should not be called.",
            "metadata": {
                "provider": self.provider_name,
                "tool": tool_name,
            },
        }


class WorkingProvider:
    provider_name = "mcp:working"

    def list_tool_specs(self):
        return [
            MCPToolSpec(
                name="mcp_working_echo",
                description="Working MCP echo tool.",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                        }
                    },
                    "required": ["message"],
                    "additionalProperties": False,
                },
                requires_approval=False,
                risk_level="low",
                permission_reason="Read-only working MCP test tool.",
                provider_name=self.provider_name,
                original_name="echo",
            )
        ]

    def call_tool(self, tool_name: str, arguments: dict):
        return tool_success(
            data={
                "message": arguments.get("message"),
            },
            metadata={
                "tool": tool_name,
                "exposed_tool": tool_name,
                "original_tool": "echo",
                "provider": self.provider_name,
                "server": "working",
            },
        )


class MCPProviderIsolationTests(unittest.TestCase):
    def test_broken_provider_does_not_block_working_provider_registration(self):
        test_config = SimpleNamespace(
            tool_permissions=_test_permissions,
        )

        with patch("app.tools.registry.config", test_config), patch(
            "app.tools.registry.build_mcp_providers",
            return_value=[
                BrokenProvider(),
                WorkingProvider(),
            ],
        ):
            tools = build_tool_definitions(memory_store=None)

        self.assertIn("mcp_working_echo", tools)

        tool = tools["mcp_working_echo"]
        self.assertEqual(tool.source, "mcp:working")
        self.assertFalse(tool.requires_approval)
        self.assertEqual(tool.risk_level, "low")
        self.assertEqual(
            tool.permission_reason,
            "Read-only working MCP test tool.",
        )

    def test_empty_provider_does_not_block_working_provider_registration(self):
        test_config = SimpleNamespace(
            tool_permissions=_test_permissions,
        )

        with patch("app.tools.registry.config", test_config), patch(
            "app.tools.registry.build_mcp_providers",
            return_value=[
                EmptyProvider(),
                WorkingProvider(),
            ],
        ):
            tools = build_tool_definitions(memory_store=None)

        self.assertEqual(
            sorted(tools.keys()),
            ["mcp_working_echo"],
        )

    def test_registered_tool_still_calls_own_provider(self):
        test_config = SimpleNamespace(
            tool_permissions=_test_permissions,
        )

        provider = WorkingProvider()

        with patch("app.tools.registry.config", test_config), patch(
            "app.tools.registry.build_mcp_providers",
            return_value=[provider],
        ):
            tools = build_tool_definitions(memory_store=None)

        result = tools["mcp_working_echo"].function(
            message="hello",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["message"], "hello")
        self.assertEqual(result["metadata"]["provider"], "mcp:working")
        self.assertEqual(result["metadata"]["original_tool"], "echo")
        self.assertEqual(result["metadata"]["exposed_tool"], "mcp_working_echo")


if __name__ == "__main__":
    unittest.main()