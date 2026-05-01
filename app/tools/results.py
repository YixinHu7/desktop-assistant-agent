from typing import Any, Dict, Optional


def tool_success(data: Any = None, metadata: Optional[Dict] = None):
    return {
        "ok": True,
        "data": data,
        "error": None,
        "metadata": metadata or {}
    }


def tool_error(message: str, metadata: Optional[Dict] = None):
    return {
        "ok": False,
        "data": None,
        "error": message,
        "metadata": metadata or {}
    }