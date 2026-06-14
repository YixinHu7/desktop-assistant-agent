---
name: repo_review
description: Use this skill when the user asks to review a repository, analyze project architecture, summarize a codebase, inspect project structure, or create a project overview note.
triggers: repo, repository, codebase, project architecture, project structure, review this project, review this repository
---

# Repo Review Skill

## Purpose

Use this skill to analyze a local repository and produce a clear architecture overview.

## When to Use

Use this skill when the user asks to:

- review this repository
- summarize the project architecture
- explain the codebase structure
- identify main architecture components
- create a project overview note
- inspect the project files

Do not use this skill for general programming explanations that do not require reading local files.

## Recommended Process

1. Start by calling `get_project_tree` with:
   - `path="."`
   - `max_depth=3`

2. Identify key files from the tree. Prioritize files such as:
   - `main.py`
   - `README.md`
   - `app/agent.py`
   - `app/router.py`
   - `app/planner.py`
   - `app/executor.py`
   - `app/tools/registry.py`
   - `app/tools/system_tools.py`
   - `app/memory.py`
   - `app/config.py`

3. Read important files using `read_multiple_files`.

4. Summarize the architecture in these sections:
   - Entry point
   - Agent runtime
   - Routing and planning
   - Tool registry and executor
   - Memory and policies
   - Recovery and replanning
   - Tracing and metrics
   - Current limitations

5. If the user asks to save the result, call `create_note`.

## Rules

- Do not invent files.
- Only mention files confirmed by tool results.
- Prefer concise architecture summaries over line-by-line explanation.
- If a file cannot be read, say so clearly.
- If the repository is too large, summarize the top-level structure first.
- Use tool evidence before making architecture claims.

## Output Style

For a normal answer, use:

1. Short project summary
2. Main components
3. Runtime flow
4. Strengths
5. Suggested next improvements

For a saved note, use a clear title such as:

`Project Architecture Overview`