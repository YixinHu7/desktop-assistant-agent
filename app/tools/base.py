from dataclasses import dataclass
from typing import Callable, Dict, Any


@dataclass
class ToolDefinition:
    name: str
    schema: Dict[str, Any]
    function: Callable[..., Dict[str, Any]]
    requires_approval: bool = False
    source: str = "local"