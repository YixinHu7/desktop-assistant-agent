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


config = AppConfig()