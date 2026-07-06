from datetime import datetime
from enum import Enum
from typing import Any, Optional

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


class EvalExecutionError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: str
    message: str
    traceback: Optional[str] = None


class EvalJudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    score: Optional[float] = None
    passed: Optional[bool] = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: Optional[EvalExecutionError] = None


class EvalCaseRunResult(BaseModel):
    """
    Complete result for one end-to-end evaluation case.

    This includes both deterministic scorer output and runtime
    execution information.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    suite: str
    description: str

    source_path: str
    line_number: int

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    duration_ms: int = Field(ge=0)

    final_answer: str = ""

    checks: list[EvalCheckResult] = Field(
        default_factory=list
    )

    run_summary: dict[str, Any] = Field(
        default_factory=dict
    )

    error: Optional[EvalExecutionError] = None
    
    judge: Optional[EvalJudgeResult] = None


class EvalRunReport(BaseModel):
    """
    Complete report for one evaluation runner invocation.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str

    started_at: datetime
    completed_at: datetime

    requested_suite: Optional[str] = None

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    error_cases: int = Field(ge=0)

    pass_rate: float = Field(ge=0.0, le=1.0)
    average_score: float = Field(ge=0.0, le=1.0)

    results: list[EvalCaseRunResult] = Field(
        default_factory=list
    )