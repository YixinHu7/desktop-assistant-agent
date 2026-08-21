from enum import Enum
from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictEvalModel(BaseModel):
    """
    Base model for evaluation data.

    extra="forbid" ensures misspelled or unsupported fields
    fail validation instead of being silently ignored.
    """

    model_config = ConfigDict(extra="forbid")


class EvalSuite(str, Enum):
    ROUTING = "routing"
    SKILLS = "skills"
    TOOLS = "tools"
    RECOVERY = "recovery"
    SAFETY = "safety"
    REGRESSION = "regression"
    MCP = "mcp"
    END_TO_END = "end_to_end"


class ExpectedRoute(str, Enum):
    CHAT = "chat"
    TOOL = "tool"
    PLAN = "plan"


class CompletionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"


class ToolArgumentExpectation(StrictEvalModel):
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)

    # subset:
    # Actual arguments may contain extra fields.
    #
    # exact:
    # Actual arguments must exactly match expected arguments.
    match: Literal["subset", "exact"] = "subset"


class MCPTelemetryExpectation(StrictEvalModel):
    tool: str = Field(min_length=1)
    provider: Optional[str] = None
    server: Optional[str] = None
    original_tool: Optional[str] = None
    exposed_tool: Optional[str] = None
    

class GroundingExpectation(StrictEvalModel):
    required: bool = False
    require_successful_tool: bool = True
    require_evidence_reference: bool = False
    forbid_unobserved_file_claims: bool = False
    
    
class AnswerExpectation(StrictEvalModel):
    contains_all: list[str] = Field(default_factory=list)
    contains_any: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    min_characters: Optional[int] = Field(default=None, ge=1)
    grounding: GroundingExpectation = Field(default_factory=GroundingExpectation)


class JudgeExpectation(StrictEvalModel):
    enabled: bool = False
    min_overall_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rubric: Optional[str] = None


class EvalEnvironment(StrictEvalModel):
    """
    Environment configuration used for one evaluation case.

    Values remain strings because they will eventually be applied
    similarly to environment variables.
    """

    env: dict[str, str] = Field(default_factory=dict)
    fixture_root: Optional[str] = None
    memory_seed: dict[str, Any] = Field(default_factory=dict)

    # Evaluation cases should not perform real side effects unless
    # explicitly allowed.
    allow_real_side_effects: bool = False


class EvalExpectedOutcome(StrictEvalModel):
    route: Optional[ExpectedRoute] = None

    should_use_skill: Optional[bool] = None
    skill: Optional[str] = None

    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)

    tool_arguments: list[ToolArgumentExpectation] = Field(
        default_factory=list
    )
    
    mcp: list[MCPTelemetryExpectation] = Field(default_factory=list)

    approval_required_tools: list[str] = Field(default_factory=list)

    recovery_expected: Optional[bool] = None
    completion_status: Optional[CompletionStatus] = None

    minimum_tool_calls: Optional[int] = Field(
        default=None,
        ge=0,
    )
    maximum_tool_calls: Optional[int] = Field(
        default=None,
        ge=0,
    )

    answer: AnswerExpectation = Field(
        default_factory=AnswerExpectation
    )
    
    judge: JudgeExpectation = Field(default_factory=JudgeExpectation)

    @field_validator(
        "required_tools",
        "optional_tools",
        "forbidden_tools",
        "approval_required_tools",
    )
    @classmethod
    def unique_tool_names(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = []

        for value in values:
            name = value.strip()

            if not name:
                raise ValueError("Tool names cannot be empty.")

            if name not in normalized:
                normalized.append(name)

        return normalized

    @model_validator(mode="after")
    def validate_expectation_consistency(self):
        required = set(self.required_tools)
        optional = set(self.optional_tools)
        forbidden = set(self.forbidden_tools)

        required_forbidden_overlap = required & forbidden

        if required_forbidden_overlap:
            raise ValueError(
                "Tools cannot be both required and forbidden: "
                f"{sorted(required_forbidden_overlap)}"
            )

        optional_forbidden_overlap = optional & forbidden

        if optional_forbidden_overlap:
            raise ValueError(
                "Tools cannot be both optional and forbidden: "
                f"{sorted(optional_forbidden_overlap)}"
            )

        if self.should_use_skill is False and self.skill is not None:
            raise ValueError(
                "skill must be null when should_use_skill is false."
            )

        if self.should_use_skill is True and not self.skill:
            raise ValueError(
                "skill is required when should_use_skill is true."
            )

        if (
            self.minimum_tool_calls is not None
            and self.maximum_tool_calls is not None
            and self.minimum_tool_calls > self.maximum_tool_calls
        ):
            raise ValueError(
                "minimum_tool_calls cannot exceed maximum_tool_calls."
            )

        return self


class EvalCase(StrictEvalModel):
    id: str = Field(
        min_length=3,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )

    suite: EvalSuite
    description: str = Field(min_length=1)
    input: str = Field(min_length=1)

    tags: list[str] = Field(default_factory=list)
    environment: EvalEnvironment = Field(
        default_factory=EvalEnvironment
    )
    expected: EvalExpectedOutcome

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def normalize_tags(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = []

        for value in values:
            tag = value.strip().lower()

            if tag and tag not in normalized:
                normalized.append(tag)

        return normalized