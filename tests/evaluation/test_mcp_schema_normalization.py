import unittest
from types import SimpleNamespace

from app.mcp.schema import normalize_mcp_tool_parameters


class MCPSchemaNormalizationTests(unittest.TestCase):
    def test_none_schema_becomes_empty_object_schema(self):
        schema = normalize_mcp_tool_parameters(None)

        self.assertEqual(
            schema,
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        )

    def test_non_dict_schema_becomes_empty_object_schema(self):
        schema = normalize_mcp_tool_parameters("not-a-schema")

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"], {})
        self.assertEqual(schema["required"], [])
        self.assertFalse(schema["additionalProperties"])

    def test_non_object_schema_becomes_empty_object_schema(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "string",
            }
        )

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"], {})
        self.assertEqual(schema["required"], [])
        self.assertFalse(schema["additionalProperties"])

    def test_missing_type_is_normalized_to_object(self):
        schema = normalize_mcp_tool_parameters(
            {
                "properties": {
                    "message": {
                        "type": "string",
                    }
                },
                "required": ["message"],
            }
        )

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["message"]["type"], "string")
        self.assertEqual(schema["required"], ["message"])
        self.assertFalse(schema["additionalProperties"])

    def test_missing_properties_and_required_are_filled(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
            }
        )

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"], {})
        self.assertEqual(schema["required"], [])
        self.assertFalse(schema["additionalProperties"])

    def test_non_dict_properties_becomes_empty_properties(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
                "properties": ["message"],
                "required": ["message"],
            }
        )

        self.assertEqual(schema["properties"], {})
        self.assertEqual(schema["required"], [])

    def test_non_list_required_becomes_empty_required(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                    }
                },
                "required": "message",
            }
        )

        self.assertEqual(schema["required"], [])

    def test_required_fields_not_in_properties_are_removed(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                    }
                },
                "required": ["message", "missing"],
            }
        )

        self.assertEqual(schema["required"], ["message"])

    def test_additional_properties_is_forced_false(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                    }
                },
                "required": ["message"],
                "additionalProperties": True,
            }
        )

        self.assertFalse(schema["additionalProperties"])

    def test_nested_object_schema_is_normalized(self):
        schema = normalize_mcp_tool_parameters(
            {
                "type": "object",
                "properties": {
                    "payload": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                            }
                        },
                        "required": ["id", "missing"],
                        "additionalProperties": True,
                    }
                },
                "required": ["payload"],
            }
        )

        payload = schema["properties"]["payload"]

        self.assertEqual(payload["type"], "object")
        self.assertEqual(payload["required"], ["id"])
        self.assertFalse(payload["additionalProperties"])

    def test_pydantic_style_object_is_supported(self):
        raw_schema = SimpleNamespace(
            model_dump=lambda: {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                    }
                },
                "required": ["message"],
            }
        )

        schema = normalize_mcp_tool_parameters(raw_schema)

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["message"]["type"], "string")
        self.assertEqual(schema["required"], ["message"])
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()