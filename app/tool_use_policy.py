from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from app.config import config


class ToolUseDecision(BaseModel):
    should_use_tools: bool
    likely_tools: List[str] = Field(default_factory=list)
    avoid_tools: List[str] = Field(default_factory=list)
    requires_grounding: bool = False
    reason: str


class ToolUsePolicy:
    def __init__(self, client: OpenAI):
        self.client = client

    def decide(self, user_input: str, route: str, memory_context: str) -> ToolUseDecision:
        enabled_tools = config.enabled_tool_names()
        disabled_tools = config.disabled_tool_names()
        
        prompt = f"""
You are a tool-use policy module for a desktop assistant agent.

Your job is to decide whether tools should be used for this request.

Enabled tools:
{enabled_tools}

Disabled tools:
{disabled_tools}

Tool meanings:
- list_files: list files in a directory
- read_file: read a local file
- create_note: create a markdown note
- save_memory_fact: save durable user memory
- open_app: open a desktop application
- get_project_tree: show a directory tree for a project
- find_file: find files by filename
- search_files: search text content across files
- read_multiple_files: read several local files at once

Rules:
- Only include enabled tools in likely_tools.
- Never include disabled tools in likely_tools.
- If the user request requires a disabled tool, set should_use_tools to false and explain why.
- Use tools when the user asks to create, read, inspect, save, remember, open, or analyze local files/apps and the required tools are enabled.
- Do not use tools for simple explanations, definitions, brainstorming, or casual chat.
- If the task involves repository structure, code files, directories, local file reading, or file summarization, requires_grounding should be true.
- If requires_grounding is true for a file task, likely_tools should include list_files before read_file, but only if those tools are enabled.
- If the user explicitly asks to remember durable information and save_memory_fact is enabled, likely_tools should include save_memory_fact.
- If the user asks to create or save a note and create_note is enabled, likely_tools should include create_note.
- If the user asks to inspect a repository, project, directory, or files and file tools are enabled, likely_tools should include list_files and possibly read_file.
- If the user asks to open an application and open_app is enabled, likely_tools should include open_app.
- If the user asks to review a repository or project architecture, likely_tools should include get_project_tree, read_multiple_files, and possibly search_files.
- If the user asks to find a specific file, likely_tools should include find_file.
- If the user asks about where something is defined or mentioned, likely_tools should include search_files.
- If the user asks to summarize multiple project files, likely_tools should include read_multiple_files.
- Avoid tools that are unrelated to the user's request.

Route:
{route}

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model=config.model,
            input=[
                {"role": "system", "content": "Return a structured tool-use decision."},
                {"role": "user", "content": prompt},
            ],
            text_format=ToolUseDecision,
        )

        decision = response.output_parsed

        enabled_set = set(enabled_tools)
        disabled_set = set(disabled_tools)

        decision.likely_tools = [
            tool for tool in decision.likely_tools
            if tool in enabled_set
        ]

        decision.avoid_tools = sorted(
            set(decision.avoid_tools).union(disabled_set)
        )

        if decision.should_use_tools and not decision.likely_tools:
            decision.should_use_tools = False
            decision.reason += " No enabled tools are available for the requested action."

        return decision