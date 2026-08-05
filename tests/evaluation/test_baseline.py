import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.baseline import (
    create_eval_baseline,
    normalize_baseline_name,
    render_baseline_summary,
)
from app.evaluation.results import EvalRunReport


def build_report() -> EvalRunReport:
    return EvalRunReport(
        run_id="eval-test",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        requested_suite="regression",
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        error_cases=0,
        pass_rate=1.0,
        average_score=1.0,
        results=[],
    )


class EvalBaselineTests(unittest.TestCase):
    def test_normalize_baseline_name(self):
        self.assertEqual(
            normalize_baseline_name("Pre MCP Baseline!"),
            "Pre-MCP-Baseline",
        )

    def test_render_baseline_summary(self):
        summary = render_baseline_summary(build_report(), source_path="result.json")

        self.assertIn("Evaluation Baseline", summary)
        self.assertIn("Pass rate: 100.0%", summary)
        self.assertIn("No failed cases", summary)

    def test_create_eval_baseline_writes_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            input_path = temp_root / "result.json"
            baselines_dir = temp_root / "baselines"

            input_path.write_text(
                build_report().model_dump_json(indent=2),
                encoding="utf-8",
            )

            baseline = create_eval_baseline(
                input_path=input_path,
                name="test-baseline",
                baselines_dir=baselines_dir,
            )

            self.assertTrue(baseline.result_path.exists())
            self.assertTrue(baseline.summary_path.exists())
            self.assertTrue(baseline.metadata_path.exists())

            metadata = json.loads(
                baseline.metadata_path.read_text(encoding="utf-8")
            )

            self.assertEqual(metadata["name"], "test-baseline")
            self.assertEqual(metadata["run_id"], "eval-test")


if __name__ == "__main__":
    unittest.main()