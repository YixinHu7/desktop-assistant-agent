from dataclasses import asdict, dataclass, field
from typing import Literal


DiscoveryStatus = Literal["not_started", "ok", "error"]


@dataclass
class MCPDiscoveryDiagnostics:
    provider_name: str
    server_name: str
    status: DiscoveryStatus = "not_started"
    total_tools: int = 0
    allowed_tools: list[str] = field(default_factory=list)
    discovered_tools: list[str] = field(default_factory=list)
    registered_tools: list[str] = field(default_factory=list)
    filtered_tools: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)