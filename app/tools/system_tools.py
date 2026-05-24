import platform
import subprocess
import os

from pathlib import Path
from app.tools.results import tool_success, tool_error
from app.config import config


def create_note(title: str, content: str):
    import os
    from datetime import datetime
    
    try:
        notes_dir = config.notes_dir
        os.makedirs(notes_dir, exist_ok=True)
    
        safe_title = title.replace("/", "_").replace("\\", "_")
        filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
        path = os.path.join(notes_dir, filename)
    
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}\n")
    
        return tool_success(
            data={"title": title, "path": path},
            metadata={"tool": "create_note"}
        )
    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "create_note", "title": title}
        )
        
def open_app(app_name: str):
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
        files = os.listdir(path)
        return tool_success(
            data={"path": path, "files": files},
            metadata={"tool": "list_files"}
        )
    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "list_files", "path": path}
        )
    
def read_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return tool_success(
            data={
                "path": path,
                "content": content[:config.max_file_read_chars],
                "truncated": len(content) > config.max_file_read_chars
            },
            metadata={"tool": "read_file"}
        )
    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "read_file", "path": path}
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
        root = Path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "get_project_tree", "path": path}
            )

        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}

        lines = []

        def walk(current_path: Path, prefix: str, depth: int):
            if depth > max_depth:
                return

            try:
                children = sorted(
                    current_path.iterdir(),
                    key=lambda p: (p.is_file(), p.name.lower())
                )
            except PermissionError:
                lines.append(f"{prefix}[permission denied] {current_path.name}")
                return

            for child in children:
                if child.name in ignore_dirs:
                    continue

                rel_name = child.name + ("/" if child.is_dir() else "")
                lines.append(f"{prefix}{rel_name}")

                if child.is_dir():
                    walk(child, prefix + "  ", depth + 1)

        lines.append(f"{root.resolve().name}/")
        walk(root, "  ", 1)

        return tool_success(
            data={
                "path": path,
                "tree": "\n".join(lines),
                "max_depth": max_depth
            },
            metadata={"tool": "get_project_tree"}
        )

    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "get_project_tree", "path": path}
        )

def find_file(filename: str, path: str = "."):
    try:
        root = Path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "find_file", "path": path}
            )

        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
        matches = []

        for current_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if filename.lower() in file.lower():
                    matches.append(str(Path(current_root) / file))

        return tool_success(
            data={
                "query": filename,
                "matches": matches[:50],
                "match_count": len(matches)
            },
            metadata={"tool": "find_file"}
        )

    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "find_file", "filename": filename}
        )

def search_files(query: str, path: str = ".", max_results: int = 20):
    try:
        root = Path(path)

        if not root.exists():
            return tool_error(
                message=f"Path does not exist: {path}",
                metadata={"tool": "search_files", "path": path}
            )

        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
        allowed_suffixes = {
            ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
            ".js", ".ts", ".tsx", ".jsx", ".html", ".css"
        }

        matches = []

        for current_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                file_path = Path(current_root) / file

                if file_path.suffix.lower() not in allowed_suffixes:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, start=1):
                            if query.lower() in line.lower():
                                matches.append({
                                    "path": str(file_path),
                                    "line": line_num,
                                    "text": line.strip()[:300]
                                })

                                if len(matches) >= max_results:
                                    return tool_success(
                                        data={
                                            "query": query,
                                            "matches": matches,
                                            "truncated": True
                                        },
                                        metadata={"tool": "search_files"}
                                    )
                except UnicodeDecodeError:
                    continue
                except PermissionError:
                    continue

        return tool_success(
            data={
                "query": query,
                "matches": matches,
                "truncated": False
            },
            metadata={"tool": "search_files"}
        )

    except Exception as e:
        return tool_error(
            message=str(e),
            metadata={"tool": "search_files", "query": query}
        )

def read_multiple_files(paths: list[str]):
    results = []

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            results.append({
                "path": path,
                "ok": True,
                "content": content[:config.max_file_read_chars],
                "truncated": len(content) > config.max_file_read_chars
            })

        except Exception as e:
            results.append({
                "path": path,
                "ok": False,
                "error": str(e)
            })

    return tool_success(
        data={"files": results},
        metadata={"tool": "read_multiple_files"}
    )

