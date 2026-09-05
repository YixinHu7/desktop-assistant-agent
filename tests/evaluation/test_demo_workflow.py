import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_demo_workflow import (
    DEFAULT_REPO_REVIEW_PROMPT,
    configure_demo_environment,
)


class DemoWorkflowTests(unittest.TestCase):
    def test_default_prompt_is_repo_review_prompt(self):
        self.assertIn("codebase", DEFAULT_REPO_REVIEW_PROMPT)
        self.assertIn("architecture", DEFAULT_REPO_REVIEW_PROMPT)

    def test_configure_demo_environment_sets_safe_eval_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_root = Path(temp_dir) / "repo"
            data_dir = Path(temp_dir) / "data"

            fixture_root.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                resolved_data_dir = configure_demo_environment(
                    fixture_root=str(fixture_root),
                    data_dir=str(data_dir),
                )

                self.assertEqual(os.environ["EVAL_MODE"], "true")
                self.assertEqual(
                    os.environ["EVAL_FIXTURE_ROOT"],
                    str(fixture_root.resolve()),
                )
                self.assertEqual(
                    os.environ["EVAL_ALLOW_REAL_SIDE_EFFECTS"],
                    "false",
                )
                self.assertEqual(
                    os.environ["DATA_DIR"],
                    str(data_dir.resolve()),
                )
                self.assertEqual(
                    os.environ["MEMORY_PATH"],
                    str(data_dir.resolve() / "memory.json"),
                )
                self.assertEqual(
                    os.environ["TRACE_PATH"],
                    str(data_dir.resolve() / "traces.jsonl"),
                )
                self.assertEqual(
                    os.environ["NOTES_DIR"],
                    str(data_dir.resolve() / "notes"),
                )
                self.assertEqual(os.environ["ENABLE_SKILLS"], "true")
                self.assertEqual(os.environ["ENABLE_MCP_TOOLS"], "false")
                self.assertEqual(os.environ["ENABLE_REAL_MCP_TOOLS"], "false")
                self.assertEqual(os.environ["ENABLE_MOCK_MCP_TOOLS"], "false")
                self.assertEqual(resolved_data_dir, data_dir.resolve())

    def test_configure_demo_environment_rejects_missing_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_fixture = Path(temp_dir) / "missing"

            with self.assertRaises(ValueError):
                configure_demo_environment(
                    fixture_root=str(missing_fixture),
                    data_dir=str(Path(temp_dir) / "data"),
                )


if __name__ == "__main__":
    unittest.main()
