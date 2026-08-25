from copy import deepcopy
from typing import Any


DEFAULT_MCP_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}


def normalize_mcp_tool_parameters(input_schema: Any) -> dict[str, Any]:
    schema = _object_to_data(input_schema)

    if not isinstance(schema, dict):
        return deepcopy(DEFAULT_MCP_TOOL_PARAMETERS)

    normalized = deepcopy(schema)

    if normalized.get("type") not in (None, "object"):
        return deepcopy(DEFAULT_MCP_TOOL_PARAMETERS)

    normalized["type"] = "object"

    properties = normalized.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}

    normalized["properties"] = {
        str(name): _normalize_property_schema(property_schema)
        for name, property_schema in properties.items()
    }

    required = normalized.get("required", [])
    if not isinstance(required, list):
        required = []

    property_names = set(normalized["properties"].keys())
    normalized["required"] = [
        str(name)
        for name in required
        if isinstance(name, str) and name in property_names
    ]

    normalized["additionalProperties"] = False

    return normalized


def _normalize_property_schema(schema: Any) -> dict[str, Any]:
    data = _object_to_data(schema)

    if not isinstance(data, dict):
        return {}

    normalized = deepcopy(data)

    if normalized.get("type") == "object":
        nested_properties = normalized.get("properties", {})

        if not isinstance(nested_properties, dict):
            nested_properties = {}

        normalized["properties"] = {
            str(name): _normalize_property_schema(property_schema)
            for name, property_schema in nested_properties.items()
        }

        required = normalized.get("required", [])
        if not isinstance(required, list):
            required = []

        property_names = set(normalized["properties"].keys())
        normalized["required"] = [
            str(name)
            for name in required
            if isinstance(name, str) and name in property_names
        ]

        normalized["additionalProperties"] = False

    return normalized


def _object_to_data(value: Any):
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

    return value