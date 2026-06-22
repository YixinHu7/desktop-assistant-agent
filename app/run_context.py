from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class RunContext:
    run_id: str = field(default_factory=lambda: str(uuid4()))
    user_input: str = ""

    memory_decision: Optional[Dict[str, Any]] = None
    route_decision: Optional[Dict[str, Any]] = None
    tool_use_decision: Optional[Dict[str, Any]] = None
    
    skill_decision: Optional[Dict[str, Any]] = None
    selected_skill: Optional[str] = None

    plan: Optional[Dict[str, Any]] = None
    revised_plan: Optional[Dict[str, Any]] = None

    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    approval_decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    recovery_events: List[Dict[str, Any]] = field(default_factory=list)

    step_review: Optional[Dict[str, Any]] = None
    replan_decision: Optional[Dict[str, Any]] = None

    final_answer: str = ""

    def to_summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_input": self.user_input,
            "memory_decision": self.memory_decision,
            "route_decision": self.route_decision,
            "tool_use_decision": self.tool_use_decision,
            "skill_decision": self.skill_decision,
            "selected_skill": self.selected_skill,
            "plan": self.plan,
            "revised_plan": self.revised_plan,
            "tool_calls_count": len(self.tool_calls),
            "tool_calls": self.tool_calls,
            
            "approval_decisions_count": len(
                self.approval_decisions
            ),
            "approval_decisions": self.approval_decisions,
            "recovery_events_count": len(
                self.recovery_events
            ),
            "recovery_events": self.recovery_events,
            # Compatibility field used by evaluation scorers.
            "recovery_attempts": self.recovery_events,
            "step_review": self.step_review,
            "replan_decision": self.replan_decision,
            "final_answer": self.final_answer,
        }