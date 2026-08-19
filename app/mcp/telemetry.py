def build_mcp_telemetry(
    tool_name: str,
    tool_source: str | None,
    result_metadata: dict | None,
) -> dict | None:
    metadata = result_metadata or {}

    provider = metadata.get("provider") or tool_source
    original_tool = metadata.get("original_tool") or metadata.get("tool") or tool_name
    exposed_tool = metadata.get("exposed_tool") or tool_name
    server = metadata.get("server")

    is_mcp_tool = (
        str(tool_name).startswith("mcp_")
        or str(tool_source or "").startswith("mcp:")
        or tool_source == "mock_mcp"
        or metadata.get("provider") is not None
    )

    if not is_mcp_tool:
        return None

    telemetry = {
        "provider": provider,
        "original_tool": original_tool,
        "exposed_tool": exposed_tool,
    }

    if server is not None:
        telemetry["server"] = server

    return telemetry