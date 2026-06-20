from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvalCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvalCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: EvalCheckStatus
    score: float = Field(ge=0.0, le=1.0)
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    suite: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    checks: list[EvalCheckResult]