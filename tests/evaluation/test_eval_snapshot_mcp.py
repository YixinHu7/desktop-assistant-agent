import unittest

from app.evaluation.snapshot import RuntimeEvalSnapshot


class EvalSnapshotMCPTests(unittest.TestCase):
    def test_extracts_mcp_tool_call_telemetry(self):
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
                ],
                "final_answer": "TICKET-123 is in progress.",
            }
        )

        self.assertEqual(len(snapshot.tool_calls), 1)

        call = snapshot.tool_calls[0]
        self.assertEqual(call.name, "mcp_read_ticket")
        self.assertEqual(
            call.mcp,
            {
                "provider": "mock_mcp",
                "original_tool": "mcp_read_ticket",
                "exposed_tool": "mcp_read_ticket",
            },
        )


if __name__ == "__main__":
    unittest.main()