import asyncio
import json
import re
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.mcp.provider import MCPProvider, MCPToolSpec
from app.mcp.server_config import MCPServerConfig
from app.tools.results import tool_error, tool_success


class RealMCPProvider(MCPProvider):
    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.provider_name = f"mcp:{server_config.name}"
        self._tool_name_map: dict[str, str] = {}

    def list_tool_specs(self) -> list[MCPToolSpec]:
        try:
            return asyncio.run(self._list_tool_specs_async())
        except Exception as exc:
            return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]):
        try:
            return asyncio.run(self._call_tool_async(tool_name, arguments))
        except Exception as exc:
            return tool_error(
                message=str(exc),
                metadata={
                    "tool": tool_name,
                    "provider": self.provider_name,
                    "server": self.server_config.name,
                    "real_mcp_error": True,
                    "error_type": type(exc).__name__,
                },
            )

    async def _list_tool_specs_async(self) -> list[MCPToolSpec]:
        async with self._open_session() as session:
            tools_response = await session.list_tools()

        specs = []

        for tool in tools_response.tools:
            original_name = str(tool.name)
            
            if not self._is_tool_allowed(original_name):
                continue
            
            exposed_name = self._exposed_tool_name(original_name)
            self._tool_name_map[exposed_name] = original_name
            tool_policy = self._tool_policy_for(original_name)

            input_schema = getattr(tool, "inputSchema", None) or getattr(
                tool,
                "input_schema",
                None,
            )

            specs.append(
                MCPToolSpec(
                    name=exposed_name,
                    original_name=original_name,
                    provider_name=self.provider_name,
                    description=self._build_tool_description(tool, original_name),
                    parameters=input_schema or {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                    requires_approval=(
                        tool_policy.requires_approval if tool_policy else True
                    ),
                    risk_level=tool_policy.risk_level if tool_policy else "high",
                    permission_reason=(
                        tool_policy.reason
                        if tool_policy
                        else (
                            "Real MCP tool requires approval by default because "
                            "no explicit tool policy was configured."
                        )
                    ),
                )
            )

        return specs

    async def _call_tool_async(self, tool_name: str, arguments: dict[str, Any]):
        original_name = self._tool_name_map.get(tool_name)

        if original_name is None:
            original_name = self._original_name_from_exposed_name(tool_name)

        async with self._open_session() as session:
            result = await session.call_tool(original_name, arguments=arguments)

        normalized_result = self._normalize_tool_result(result)

        if normalized_result["is_error"]:
            return tool_error(
                message=normalized_result["text"] or "MCP tool returned an error.",
                metadata={
                    "tool": tool_name,
                    "original_tool": original_name,
                    "provider": self.provider_name,
                    "server": self.server_config.name,
                    "mcp_is_error": True,
                    "raw_result": normalized_result["raw"],
                },
            )

        return tool_success(
            data={
                "tool": tool_name,
                "original_tool": original_name,
                "text": normalized_result["text"],
                "structured_content": normalized_result["structured_content"],
                "content": normalized_result["content"],
            },
            metadata={
                "tool": tool_name,
                "original_tool": original_name,
                "provider": self.provider_name,
                "server": self.server_config.name,
            },
        )

    def _open_session(self):
        server_params = StdioServerParameters(
            command=self.server_config.command,
            args=self.server_config.args,
            env=self.server_config.env or None,
        )

        return _MCPStdioSession(server_params)

    def _exposed_tool_name(self, original_name: str) -> str:
        server = _sanitize_identifier(self.server_config.name)
        tool = _sanitize_identifier(original_name)
        return f"mcp_{server}_{tool}"

    def _original_name_from_exposed_name(self, exposed_name: str) -> str:
        prefix = f"mcp_{_sanitize_identifier(self.server_config.name)}_"

        if exposed_name.startswith(prefix):
            return exposed_name[len(prefix) :]

        return exposed_name

    def _build_tool_description(self, tool, original_name: str) -> str:
        description = getattr(tool, "description", None) or ""
        title = getattr(tool, "title", None)

        parts = [
            f"Real MCP tool from server '{self.server_config.name}'.",
            f"Original tool name: {original_name}.",
        ]

        if title:
            parts.append(f"Title: {title}.")

        if description:
            parts.append(description)

        parts.append("Requires approval by default.")

        return " ".join(parts)

    def _normalize_tool_result(self, result) -> dict[str, Any]:
        is_error = bool(getattr(result, "isError", False) or getattr(result, "is_error", False))
        content = getattr(result, "content", None) or []
        structured_content = (
            getattr(result, "structuredContent", None)
            or getattr(result, "structured_content", None)
        )

        text_parts = []

        for item in content:
            item_type = getattr(item, "type", None)

            if item_type == "text" and hasattr(item, "text"):
                text_parts.append(str(item.text))
            else:
                text_parts.append(_safe_json_dump(_object_to_data(item)))

        return {
            "is_error": is_error,
            "text": "\n".join(part for part in text_parts if part).strip(),
            "structured_content": _object_to_data(structured_content),
            "content": [_object_to_data(item) for item in content],
            "raw": _object_to_data(result),
        }
    
    def _is_tool_allowed(self, original_name: str) -> bool:
        return original_name in set(self.server_config.allowed_tools)

    def _tool_policy_for(self, original_name: str):
        return self.server_config.tool_policies.get(original_name)


class _MCPStdioSession:
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self._stdio_context = None
        self._session_context = None
        self.session = None

    async def __aenter__(self) -> ClientSession:
        self._stdio_context = stdio_client(self.server_params)
        read, write = await self._stdio_context.__aenter__()

        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()

        await self.session.initialize()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        if self._session_context is not None:
            await self._session_context.__aexit__(exc_type, exc, tb)

        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(exc_type, exc, tb)


def _sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip()).strip("_").lower()
    return sanitized or "tool"


def _object_to_data(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_object_to_data(item) for item in value]

    if isinstance(value, tuple):
        return [_object_to_data(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _object_to_data(child) for key, child in value.items()}

    if hasattr(value, "model_dump"):
        return _object_to_data(value.model_dump())

    if hasattr(value, "dict"):
        return _object_to_data(value.dict())

    return str(value)


def _safe_json_dump(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)