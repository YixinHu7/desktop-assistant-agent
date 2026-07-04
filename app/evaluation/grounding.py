import re
from dataclasses import dataclass, field
from typing import Any

from app.evaluation.models import EvalCase
from app.evaluation.snapshot import RuntimeEvalSnapshot


FILE_TOKEN_PATTERN = re.compile(
    r"(?<![\w.-])"
    r"(?:[\w.-]+/)*"
    r"[\w.-]+\."
    r"(?:py|md|txt|json|yaml|yml|toml|js|jsx|ts|tsx|html|css)"
    r"(?![\w.-])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GroundingAssessment:
    passed: bool
    reason: str
    observed_files: list[str] = field(default_factory=list)
    answer_files: list[str] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)


def normalize_file_token(value: str) -> str:
    return value.strip().replace("\\", "/").lower()


def extract_file_tokens(text: str) -> set[str]:
    return {
        normalize_file_token(match.group(0))
        for match in FILE_TOKEN_PATTERN.finditer(text)
    }


def iter_strings(value: Any):
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
        return

    if isinstance(value, (list, tuple, set)):
        for child in value:
            yield from iter_strings(child)


def collect_observed_file_tokens(snapshot: RuntimeEvalSnapshot) -> set[str]:
    observed = set()

    for call in snapshot.tool_calls:
        successful = call.ok is True or call.status == "completed"

        if not successful:
            continue

        for value in iter_strings(call.result):
            observed.update(extract_file_tokens(value))

    return observed


def assess_answer_grounding(
    case: EvalCase,
    snapshot: RuntimeEvalSnapshot,
) -> GroundingAssessment:
    expectation = case.expected.answer.grounding

    successful_calls = [
        call
        for call in snapshot.tool_calls
        if call.ok is True or call.status == "completed"
    ]

    if expectation.require_successful_tool and not successful_calls:
        return GroundingAssessment(
            passed=False,
            reason="No successful tool call was available to ground the answer.",
        )

    observed_files = collect_observed_file_tokens(snapshot)
    input_files = extract_file_tokens(case.input)
    answer_files = extract_file_tokens(snapshot.final_answer)

    allowed_files = observed_files | input_files
    referenced_evidence = answer_files & observed_files
    unsupported_files = answer_files - allowed_files

    if expectation.require_evidence_reference:
        if not observed_files:
            return GroundingAssessment(
                passed=False,
                reason="Successful tools did not expose any file evidence.",
                observed_files=sorted(observed_files),
                answer_files=sorted(answer_files),
            )

        if not referenced_evidence:
            return GroundingAssessment(
                passed=False,
                reason=(
                    "The answer did not reference any file observed "
                    "in successful tool results."
                ),
                observed_files=sorted(observed_files),
                answer_files=sorted(answer_files),
            )

    if expectation.forbid_unobserved_file_claims and unsupported_files:
        return GroundingAssessment(
            passed=False,
            reason=(
                "The answer mentioned files that were not present in "
                "the user input or successful tool results."
            ),
            observed_files=sorted(observed_files),
            answer_files=sorted(answer_files),
            unsupported_files=sorted(unsupported_files),
        )

    return GroundingAssessment(
        passed=True,
        reason="The answer was supported by observed file-tool evidence.",
        observed_files=sorted(observed_files),
        answer_files=sorted(answer_files),
        unsupported_files=sorted(unsupported_files),
    )