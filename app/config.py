import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    data_dir: str = os.getenv("DATA_DIR", "data")
    memory_path: str = os.getenv("MEMORY_PATH", "data/memory.json")
    trace_path: str = os.getenv("TRACE_PATH", "data/traces.jsonl")
    notes_dir: str = os.getenv("NOTES_DIR", "data/notes")

    max_file_read_chars: int = int(os.getenv("MAX_FILE_READ_CHARS", "4000"))
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
    max_replan_cycles: int = int(os.getenv("MAX_REPLAN_CYCLES", "1"))

    enable_open_app: bool = os.getenv("ENABLE_OPEN_APP", "true").lower() == "true"
    enable_file_tools: bool = os.getenv("ENABLE_FILE_TOOLS", "true").lower() == "true"
    enable_memory_tools: bool = os.getenv("ENABLE_MEMORY_TOOLS", "true").lower() == "true"
    
    skills_dir: str = os.getenv("SKILLS_DIR", "skills")
    enable_skills: bool = os.getenv("ENABLE_SKILLS", "true").lower() == "true"

    def tool_permissions(self):
        return {
            "list_files": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Listing local files is low risk in this local assistant context.",
            },
            "read_file": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Reading local project files is allowed in this local assistant context.",
            },
            "create_note": {
                "enabled": True,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Creating a markdown note is low risk and reversible.",
            },
            "save_memory_fact": {
                "enabled": self.enable_memory_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Saving explicit user memory is allowed when requested.",
            },
            "open_app": {
                "enabled": self.enable_open_app,
                "requires_approval": True,
                "risk_level": "medium",
                "reason": "Opening desktop applications changes the user's local environment.",
            },
            "get_project_tree": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Reading local project structure is allowed in this local assistant context.",
            },
            "find_file": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Finding local project files is allowed in this local assistant context.",
            },
            "search_files": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Searching local project files is allowed in this local assistant context.",
            },
            "read_multiple_files": {
                "enabled": self.enable_file_tools,
                "requires_approval": False,
                "risk_level": "low",
                "reason": "Reading multiple local project files is allowed in this local assistant context.",
            },
        }
        
    def enabled_tool_names(self):
        permissions = self.tool_permissions()
        return [
            tool_name
            for tool_name, policy in permissions.items()
            if policy["enabled"]
        ]

    def disabled_tool_names(self):
        permissions = self.tool_permissions()
        return [
            tool_name
            for tool_name, policy in permissions.items()
            if not policy["enabled"]
        ]

config = AppConfig()