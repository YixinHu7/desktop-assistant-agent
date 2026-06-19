import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.evaluation.models import EvalCase, EvalSuite


class EvalCaseLoadError(Exception):
    """Raised when evaluation cases cannot be loaded."""


@dataclass(frozen=True)
class LoadedEvalCase:
    case: EvalCase
    source_path: str
    line_number: int


def _format_validation_error(
    error: ValidationError,
) -> str:
    messages = []

    for item in error.errors():
        location = ".".join(
            str(part)
            for part in item["loc"]
        )

        messages.append(
            f"{location}: {item['msg']}"
        )

    return "; ".join(messages)


def load_eval_file(
    path: str | Path,
) -> list[LoadedEvalCase]:
    file_path = Path(path)

    if not file_path.exists():
        raise EvalCaseLoadError(
            f"Evaluation file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise EvalCaseLoadError(
            f"Evaluation path is not a file: {file_path}"
        )

    loaded: list[LoadedEvalCase] = []

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, raw_line in enumerate(
            file,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                raw_case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvalCaseLoadError(
                    f"{file_path}:{line_number}: "
                    f"Invalid JSON: {exc.msg}"
                ) from exc

            try:
                case = EvalCase.model_validate(raw_case)
            except ValidationError as exc:
                formatted = _format_validation_error(exc)

                raise EvalCaseLoadError(
                    f"{file_path}:{line_number}: "
                    f"Invalid evaluation case: {formatted}"
                ) from exc

            loaded.append(
                LoadedEvalCase(
                    case=case,
                    source_path=str(file_path),
                    line_number=line_number,
                )
            )

    return loaded


def load_eval_cases(
    cases_dir: str | Path = "evals/cases",
    suite: Optional[EvalSuite] = None,
) -> list[LoadedEvalCase]:
    root = Path(cases_dir)

    if not root.exists():
        raise EvalCaseLoadError(
            f"Evaluation cases directory does not exist: {root}"
        )

    case_files = sorted(root.rglob("*.jsonl"))

    if not case_files:
        raise EvalCaseLoadError(
            f"No JSONL evaluation files found in: {root}"
        )

    loaded: list[LoadedEvalCase] = []
    case_locations: dict[str, LoadedEvalCase] = {}

    for case_file in case_files:
        for record in load_eval_file(case_file):
            existing = case_locations.get(record.case.id)

            if existing is not None:
                raise EvalCaseLoadError(
                    f"Duplicate evaluation case ID "
                    f"'{record.case.id}'. First defined at "
                    f"{existing.source_path}:"
                    f"{existing.line_number}, then at "
                    f"{record.source_path}:"
                    f"{record.line_number}."
                )

            case_locations[record.case.id] = record

            if suite is None or record.case.suite == suite:
                loaded.append(record)

    return loaded