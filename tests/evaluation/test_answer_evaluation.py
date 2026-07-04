import unittest

from app.evaluation.models import EvalCase
from app.evaluation.scorers import score_eval_case


def build_case(case_id: str, expected: dict) -> EvalCase:
    return EvalCase.model_validate(
        {
            "id": case_id,
            "suite": "end_to_end",
            "description": "Synthetic answer evaluation test.",
            "input": "Read main.py.",
            "expected": expected,
        }
    )


class AnswerEvaluationTests(unittest.TestCase):
    def test_answer_requirements_pass(self):
        case = build_case(
            "answer_requirements_pass",
            {
                "answer": {
                    "contains_all": ["entry point"],
                    "contains_any": ["main.py", "application"],
                    "excludes": ["I guessed"],
                    "min_characters": 20,
                }
            },
        )

        run_summary = {
            "final_answer": "main.py is the application entry point."
        }

        result = score_eval_case(case, run_summary)

        self.assertTrue(result.passed)

    def test_answer_requirements_fail(self):
        case = build_case(
            "answer_requirements_fail",
            {
                "answer": {
                    "contains_all": ["entry point"],
                    "excludes": ["probably"],
                }
            },
        )

        run_summary = {
            "final_answer": "This is probably a helper module."
        }

        result = score_eval_case(case, run_summary)

        self.assertFalse(result.passed)

    def test_grounding_passes_with_observed_file(self):
        case = build_case(
            "answer_grounding_pass",
            {
                "answer": {
                    "grounding": {
                        "required": True,
                        "require_successful_tool": True,
                        "require_evidence_reference": True,
                        "forbid_unobserved_file_claims": True,
                    }
                }
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "read_file",
                    "status": "completed",
                    "result": {
                        "ok": True,
                        "data": {
                            "path": "main.py",
                            "content": "print('hello')",
                        },
                    },
                }
            ],
            "final_answer": "main.py prints a greeting.",
        }

        result = score_eval_case(case, run_summary)

        self.assertTrue(result.passed)

    def test_grounding_rejects_unobserved_file(self):
        case = build_case(
            "answer_grounding_unobserved",
            {
                "answer": {
                    "grounding": {
                        "required": True,
                        "require_successful_tool": True,
                        "require_evidence_reference": True,
                        "forbid_unobserved_file_claims": True,
                    }
                }
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "read_file",
                    "status": "completed",
                    "result": {
                        "ok": True,
                        "data": {
                            "path": "main.py",
                            "content": "print('hello')",
                        },
                    },
                }
            ],
            "final_answer": (
                "main.py prints a greeting, and database.py stores the data."
            ),
        }

        result = score_eval_case(case, run_summary)

        self.assertFalse(result.passed)

        grounding_check = next(
            check
            for check in result.checks
            if check.name == "answer_grounding"
        )

        self.assertIn(
            "database.py",
            grounding_check.details["unsupported_files"],
        )

    def test_grounding_requires_successful_tool(self):
        case = build_case(
            "answer_grounding_no_success",
            {
                "answer": {
                    "grounding": {
                        "required": True,
                        "require_successful_tool": True,
                    }
                }
            },
        )

        run_summary = {
            "tool_calls": [
                {
                    "tool": "read_file",
                    "status": "failed",
                    "result": {"ok": False},
                }
            ],
            "final_answer": "main.py appears to be the entry point.",
        }

        result = score_eval_case(case, run_summary)

        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()