from pydantic import BaseModel
from typing import Literal

class RouteDecision(BaseModel):
    route: Literal["chat", "tool", "plan"]
    requires_memory: bool = False
    requires_approval: bool = False
    reason: str