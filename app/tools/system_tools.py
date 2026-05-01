import platform
import subprocess
import os

from app.tools.results import tool_success, tool_error

def create_note(title: str, content: str):
    import os
    from datetime import datetime
    
    try:
        notes_dir = "data/notes"
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
                "content": content[:4000],
                "truncated": len(content) > 4000
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