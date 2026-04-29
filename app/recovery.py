class ToolRecoveryManager:
    def maybe_recover(self, tool_name: str, arguments: dict, result: dict):
        """
        Decide whether a failed tool call should trigger a recovery attempt.

        Returns:
            {
                "should_retry": bool,
                "retry_tool": str | None,
                "retry_arguments": dict | None,
                "reason": str
            }
        """
        if result.get("ok", True):
            return {
                "should_retry": False,
                "retry_tool": None,
                "retry_arguments": None,
                "reason": "Tool succeeded; no recovery needed."
            }

        if tool_name == "list_files":
            original_path = arguments.get("path", "")
            if original_path != ".":
                return {
                    "should_retry": True,
                    "retry_tool": "list_files",
                    "retry_arguments": {"path": "."},
                    "reason": f"Path '{original_path}' failed; retrying with current directory '.'"
                }

        if tool_name == "read_file":
            return {
                "should_retry": True,
                "retry_tool": "list_files",
                "retry_arguments": {"path": "."},
                "reason": "read_file failed; listing current directory to recover context."
            }

        return {
            "should_retry": False,
            "retry_tool": None,
            "retry_arguments": None,
            "reason": "No recovery strategy available."
        }