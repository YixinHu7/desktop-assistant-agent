import unittest
from types import SimpleNamespace

from app.mcp.real_provider import RealMCPProvider
from app.mcp.server_config import MCPServerConfig


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def model_dump(self):
        return self.kwargs


class MCPResultNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.provider = RealMCPProvider(
            MCPServerConfig(
                name="tiny",
                command="python",
                args=[],
                enabled=True,
                allowed_tools=["echo"],
            )
        )

    def test_normalizes_text_content(self):
        result = SimpleNamespace(
            isError=False,
            content=[
                SimpleNamespace(
                    type="text",
                    text="Echo: hello",
                )
            ],
            structuredContent=None,
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertEqual(normalized["text"], "Echo: hello")
        self.assertIsNone(normalized["structured_content"])
        self.assertEqual(len(normalized["content"]), 1)

    def test_normalizes_multiple_text_content_items(self):
        result = SimpleNamespace(
            isError=False,
            content=[
                SimpleNamespace(type="text", text="Line one."),
                SimpleNamespace(type="text", text="Line two."),
            ],
            structuredContent=None,
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertEqual(normalized["text"], "Line one.\nLine two.")

    def test_normalizes_structured_content(self):
        result = SimpleNamespace(
            isError=False,
            content=[
                SimpleNamespace(
                    type="text",
                    text="status=ok",
                )
            ],
            structuredContent={
                "status": "ok",
                "service": "tiny-test-server",
            },
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertEqual(normalized["text"], "status=ok")
        self.assertEqual(
            normalized["structured_content"],
            {
                "status": "ok",
                "service": "tiny-test-server",
            },
        )

    def test_supports_snake_case_sdk_fields(self):
        result = SimpleNamespace(
            is_error=False,
            content=[
                SimpleNamespace(
                    type="text",
                    text="snake case result",
                )
            ],
            structured_content={
                "format": "snake_case",
            },
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertEqual(normalized["text"], "snake case result")
        self.assertEqual(
            normalized["structured_content"],
            {
                "format": "snake_case",
            },
        )

    def test_normalizes_error_result(self):
        result = SimpleNamespace(
            isError=True,
            content=[
                SimpleNamespace(
                    type="text",
                    text="Tool failed.",
                )
            ],
            structuredContent=None,
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertTrue(normalized["is_error"])
        self.assertEqual(normalized["text"], "Tool failed.")

    def test_normalizes_empty_content(self):
        result = SimpleNamespace(
            isError=False,
            content=[],
            structuredContent=None,
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertEqual(normalized["text"], "")
        self.assertEqual(normalized["content"], [])
        self.assertIsNone(normalized["structured_content"])

    def test_normalizes_non_text_content_with_model_dump(self):
        result = SimpleNamespace(
            isError=False,
            content=[
                FakeModel(
                    type="image",
                    mimeType="image/png",
                    data="base64-placeholder",
                )
            ],
            structuredContent=None,
        )

        normalized = self.provider._normalize_tool_result(result)

        self.assertFalse(normalized["is_error"])
        self.assertIn('"type": "image"', normalized["text"])
        self.assertEqual(
            normalized["content"],
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "data": "base64-placeholder",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()