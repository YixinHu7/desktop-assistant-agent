from pydantic import BaseModel, Field
from typing import Literal, List, Any, Dict

class RouteDecision(BaseModel):
    route: Literal["chat", "tool", "plan"]
    requires_memory: bool = False
    requires_approval: bool = False
    reason: str

class PlanStep(BaseModel):
    step: str

class PlanOutput(BaseModel):
    goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    
class ExecutionStepResult(BaseModel):
    step: str
    status: Literal["pending", "completed", "failed"]
    note: str = ""

class ExecutionReview(BaseModel):
    completed_steps: List[ExecutionStepResult] = Field(default_factory=list)
    remaining_steps: List[ExecutionStepResult] = Field(default_factory=list)