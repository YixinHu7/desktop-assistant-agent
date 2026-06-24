import platform
import subprocess
import os

from pathlib import Path
from app.tools.results import tool_success, tool_error
from app.config import config
from app.tools.path_policy import (
    ToolPathPolicyError,
    display_tool_path,
    resolve_tool_path,
)


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
}

SEARCHABLE_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
}


def create_note(title: str, content: str):
    try:
        notes_dir = Path(config.notes_dir)
        notes_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(
            char if char.isalnum() or char in {"-", "_"} else "_"
            for char in title
        ).strip("_")

        note_path = notes_dir / f"{safe_title or 'note'}.md"
        note_path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")

        return tool_success(
            data={
                "title": title,
                "path": str(note_path),
            },
            metadata={
                "tool": "create_note",
                "eval_mode": config.eval_mode,
            },
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={"tool": "create_note", "title": title},
        )
        
                
def open_app(app_name: str):
    if config.eval_mode and not config.eval_allow_real_side_effects:
        return tool_success(
            data={
                "app_name": app_name,
                "opened": False,
                "mocked": True,
                "message": "Application launch was simulated in evaluation mode.",
            },
            metadata={
                "tool": "open_app",
                "eval_mode": True,
                "side_effect_prevented": True,
            },
        )
        
    current_os = platform.system()

    if current_os == "Darwin":
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return tool_success(
                data={"opened": app_name},
                metadata={"tool": "open_app"}
            )
            
        return tool_error(
            message=result.stderr.strip(),
            metadata={"tool": "open_app", "app_name": app_name}
        )

    return tool_error(
        message="Unsupported OS",
        metadata={"tool": "open_app", "os": current_os}
    )

def list_files(path: str):
    try:
        resolved_path = resolve_tool_path(path)

        if not resolved_path.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "list_files", "path": path},
            )

        if not resolved_path.is_dir():
            return tool_error(
                message=f"Path is not a directory: {path}",
                metadata={"tool": "list_files", "path": path},
            )

        entries = []

        for name in sorted(os.listdir(resolved_path), key=str.lower):
            item = resolved_path / name

            entries.append(
                {
                    "name": name,
                    "path": display_tool_path(item),
                    "type": "directory" if item.is_dir() else "file",
                }
            )

        return tool_success(
            data={
                "path": display_tool_path(resolved_path),
                "entries": entries,
            },
            metadata={
                "tool": "list_files",
                "eval_mode": config.eval_mode,
            },
        )

    except ToolPathPolicyError as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "list_files",
                "path": path,
                "policy_error": True,
            },
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={"tool": "list_files", "path": path},
        )
    

def read_file(path: str):
    try:
        resolved_path = resolve_tool_path(path)

        if not resolved_path.exists():
            return tool_error(
                message=f"File does not exist: {path}",
                metadata={"tool": "read_file", "path": path},
            )

        if not resolved_path.is_file():
            return tool_error(
                message=f"Path is not a file: {path}",
                metadata={"tool": "read_file", "path": path},
            )

        content = resolved_path.read_text(encoding="utf-8")

        return tool_success(
            data={
                "path": display_tool_path(resolved_path),
                "content": content[: config.max_file_read_chars],
                "truncated": len(content) > config.max_file_read_chars,
            },
            metadata={
                "tool": "read_file",
                "eval_mode": config.eval_mode,
            },
        )

    except ToolPathPolicyError as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "read_file",
                "path": path,
                "policy_error": True,
            },
        )

    except UnicodeDecodeError:
        return tool_error(
            message=f"File is not valid UTF-8 text: {path}",
            metadata={"tool": "read_file", "path": path},
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={"tool": "read_file", "path": path},
        )
        

def save_memory_fact(memory_store, key: str, value: str):
    
    try:
        memory_store.data["facts"][key] = value
        memory_store.save()
    
        return tool_success(
            data={"saved": {key: value}},
            metadata={"tool": "save_memory_fact"}
        )
    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "save_memory_fact", "key": key}
        )


def get_project_tree(path: str = ".", max_depth: int = 3):
    try:
        root = resolve_tool_path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "get_project_tree", "path": path},
            )

        if not root.is_dir():
            return tool_error(
                message=f"Path is not a directory: {path}",
                metadata={"tool": "get_project_tree", "path": path},
            )

        lines = [f"{root.name}/"]

        def walk(current: Path, prefix: str, depth: int) -> None:
            if depth > max_depth:
                return

            children = sorted(
                current.iterdir(),
                key=lambda item: (item.is_file(), item.name.lower()),
            )

            for child in children:
                if child.name in IGNORED_DIRECTORIES:
                    continue

                suffix = "/" if child.is_dir() else ""
                lines.append(f"{prefix}{child.name}{suffix}")

                if child.is_dir():
                    walk(child, prefix + "  ", depth + 1)

        walk(root, "  ", 1)

        return tool_success(
            data={
                "path": display_tool_path(root),
                "tree": "\n".join(lines),
                "max_depth": max_depth,
            },
            metadata={
                "tool": "get_project_tree",
                "eval_mode": config.eval_mode,
            },
        )

    except ToolPathPolicyError as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "get_project_tree",
                "path": path,
                "policy_error": True,
            },
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={"tool": "get_project_tree", "path": path},
        )
        
        
def find_file(filename: str, path: str = "."):
    try:
        root = resolve_tool_path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "find_file", "path": path},
            )

        if not root.is_dir():
            return tool_error(
                message=f"Path is not a directory: {path}",
                metadata={"tool": "find_file", "path": path},
            )

        matches = []

        for current_root, directories, files in os.walk(root):
            directories[:] = [
                name for name in directories if name not in IGNORED_DIRECTORIES
            ]

            for file_name in files:
                if filename.lower() not in file_name.lower():
                    continue

                file_path = Path(current_root) / file_name
                matches.append(display_tool_path(file_path))

        return tool_success(
            data={
                "query": filename,
                "matches": matches[:50],
                "match_count": len(matches),
            },
            metadata={
                "tool": "find_file",
                "eval_mode": config.eval_mode,
            },
        )

    except ToolPathPolicyError as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "find_file",
                "path": path,
                "policy_error": True,
            },
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "find_file",
                "filename": filename,
                "path": path,
            },
        )
        
        
def search_files(query: str, path: str = ".", max_results: int = 20):
    try:
        root = resolve_tool_path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "search_files", "path": path},
            )

        matches = []

        for current_root, directories, files in os.walk(root):
            directories[:] = [
                name for name in directories if name not in IGNORED_DIRECTORIES
            ]

            for file_name in files:
                file_path = Path(current_root) / file_name

                if file_path.suffix.lower() not in SEARCHABLE_SUFFIXES:
                    continue

                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except (UnicodeDecodeError, PermissionError):
                    continue

                for line_number, line in enumerate(lines, start=1):
                    if query.lower() not in line.lower():
                        continue

                    matches.append(
                        {
                            "path": display_tool_path(file_path),
                            "line": line_number,
                            "text": line.strip()[:300],
                        }
                    )

                    if len(matches) >= max_results:
                        return tool_success(
                            data={
                                "query": query,
                                "matches": matches,
                                "truncated": True,
                            },
                            metadata={
                                "tool": "search_files",
                                "eval_mode": config.eval_mode,
                            },
                        )

        return tool_success(
            data={
                "query": query,
                "matches": matches,
                "truncated": False,
            },
            metadata={
                "tool": "search_files",
                "eval_mode": config.eval_mode,
            },
        )

    except ToolPathPolicyError as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "search_files",
                "path": path,
                "policy_error": True,
            },
        )

    except Exception as exc:
        return tool_error(
            message=str(exc),
            metadata={
                "tool": "search_files",
                "query": query,
                "path": path,
            },
        )
        
        
def read_multiple_files(paths: list[str]):
    results = []

    for path in paths:
        try:
            resolved_path = resolve_tool_path(path)

            if not resolved_path.exists():
                results.append(
                    {
                        "path": path,
                        "ok": False,
                        "error": "File does not exist.",
                    }
                )
                continue

            if not resolved_path.is_file():
                results.append(
                    {
                        "path": path,
                        "ok": False,
                        "error": "Path is not a file.",
                    }
                )
                continue

            content = resolved_path.read_text(encoding="utf-8")

            results.append(
                {
                    "path": display_tool_path(resolved_path),
                    "ok": True,
                    "content": content[: config.max_file_read_chars],
                    "truncated": len(content) > config.max_file_read_chars,
                }
            )

        except Exception as exc:
            results.append(
                {
                    "path": path,
                    "ok": False,
                    "error": str(exc),
                }
            )

    return tool_success(
        data={"files": results},
        metadata={
            "tool": "read_multiple_files",
            "eval_mode": config.eval_mode,
        },
    )