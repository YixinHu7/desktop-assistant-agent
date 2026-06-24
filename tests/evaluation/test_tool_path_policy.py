import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.tools.path_policy import (
    ToolPathPolicyError,
    display_tool_path,
    resolve_tool_path,
)


class ToolPathPolicyTests(unittest.TestCase):
    def test_eval_relative_path_uses_fixture_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_root = Path(temp_dir)
            sample_file = fixture_root / "main.py"
            sample_file.write_text("print('hello')", encoding="utf-8")

            test_config = SimpleNamespace(
                eval_mode=True,
                eval_fixture_root=str(fixture_root),
            )

            with patch("app.tools.path_policy.config", test_config):
                resolved = resolve_tool_path("main.py")

                self.assertEqual(resolved, sample_file.resolve())
                self.assertEqual(display_tool_path(resolved), "main.py")

    def test_eval_path_cannot_escape_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_root = Path(temp_dir) / "fixture"
            fixture_root.mkdir()

            test_config = SimpleNamespace(
                eval_mode=True,
                eval_fixture_root=str(fixture_root),
            )

            with patch("app.tools.path_policy.config", test_config):
                with self.assertRaises(ToolPathPolicyError):
                    resolve_tool_path("../outside.txt")

    def test_normal_mode_resolves_current_directory(self):
        test_config = SimpleNamespace(
            eval_mode=False,
            eval_fixture_root=None,
        )

        with patch("app.tools.path_policy.config", test_config):
            resolved = resolve_tool_path(".")

            self.assertTrue(resolved.is_absolute())


if __name__ == "__main__":
    unittest.main()