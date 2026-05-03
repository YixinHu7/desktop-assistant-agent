from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI


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
        prompt = f"""
You are a tool-use policy module for a desktop assistant agent.

Your job is to decide whether tools should be used for this request.

Available tools:
- list_files: list files in a directory
- read_file: read a local file
- create_note: create a markdown note
- save_memory_fact: save durable user memory
- open_app: open a desktop application

Rules:
- Use tools when the user asks to create, read, inspect, save, remember, open, or analyze local files/apps.
- Do not use tools for simple explanations, definitions, brainstorming, or casual chat.
- If the task involves reading, inspecting, or summarizing local files, requires_grounding should be true unless the file path has already been confirmed by a previous tool result in the current run.
- If the user explicitly asks to remember durable information, likely_tools should include save_memory_fact.
- If the user asks to create or save a note, likely_tools should include create_note.
- If the user asks to inspect a repository, project, directory, or files, likely_tools should include list_files and possibly read_file.
- If the user asks to open an application, likely_tools should include open_app.
- If requires_grounding is true for a file task, likely_tools should include list_files before read_file.
- Avoid tools that are unrelated to the user's request.

Route:
{route}

Memory context:
{memory_context}

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": "Return a structured tool-use decision."},
                {"role": "user", "content": prompt},
            ],
            text_format=ToolUseDecision,
        )

        return response.output_parsed