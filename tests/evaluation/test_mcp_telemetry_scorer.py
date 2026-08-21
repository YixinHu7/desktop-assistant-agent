import unittest
from types import SimpleNamespace

from app.evaluation.models import MCPTelemetryExpectation
from app.evaluation.scorers import score_mcp_telemetry
from app.evaluation.snapshot import RuntimeEvalSnapshot


class MCPTelemetryScorerTests(unittest.TestCase):
    def test_passes_when_mcp_telemetry_matches(self):
        case = SimpleNamespace(
            expected=SimpleNamespace(
                mcp=[
                    MCPTelemetryExpectation(
                        tool="mcp_read_ticket",
                        provider="mock_mcp",
                        original_tool="mcp_read_ticket",
                        exposed_tool="mcp_read_ticket",
                    )
                ]
            )
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "tool_calls": [
                    {
                        "tool": "mcp_read_ticket",
                        "arguments": {
                            "ticket_id": "TICKET-123",
                        },
                        "status": "completed",
                        "result": {
                            "ok": True,
                        },
                        "mcp": {
                            "provider": "mock_mcp",
                            "original_tool": "mcp_read_ticket",
                            "exposed_tool": "mcp_read_ticket",
                        },
                    }
                ]
            }
        )

        result = score_mcp_telemetry(case, snapshot)

        self.assertEqual(result.status.value, "passed")
        self.assertEqual(result.score, 1.0)

    def test_fails_when_provider_does_not_match(self):
        case = SimpleNamespace(
            expected=SimpleNamespace(
                mcp=[
                    MCPTelemetryExpectation(
                        tool="mcp_read_ticket",
                        provider="wrong_provider",
                        original_tool="mcp_read_ticket",
                        exposed_tool="mcp_read_ticket",
                    )
                ]
            )
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "tool_calls": [
                    {
                        "tool": "mcp_read_ticket",
                        "result": {
                            "ok": True,
                        },
                        "mcp": {
                            "provider": "mock_mcp",
                            "original_tool": "mcp_read_ticket",
                            "exposed_tool": "mcp_read_ticket",
                        },
                    }
                ]
            }
        )

        result = score_mcp_telemetry(case, snapshot)

        self.assertEqual(result.status.value, "failed")
        self.assertEqual(result.score, 0.0)

    def test_skips_when_no_mcp_expectations_are_defined(self):
        case = SimpleNamespace(
            expected=SimpleNamespace(
                mcp=[],
            )
        )

        snapshot = RuntimeEvalSnapshot.from_run_summary(
            {
                "tool_calls": [],
            }
        )

        result = score_mcp_telemetry(case, snapshot)

        self.assertEqual(result.status.value, "skipped")
        self.assertEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()