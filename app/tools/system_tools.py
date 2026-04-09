import platform
import subprocess
import os

def create_note(title: str, content: str):
    import os
    from datetime import datetime
    
    notes_dir = "data/notes"
    os.makedirs(notes_dir, exist_ok=True)
    
    safe_title = title.replace("/", "_").replace("\\", "_")
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
    path = os.path.join(notes_dir, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{content}\n")
    
    return {"ok": True, "path": path}

def open_app(app_name: str):
    current_os = platform.system()

    if current_os == "Darwin":
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return {"ok": True, "opened": app_name}
        return {"ok": False, "error": result.stderr.strip()}

    return {"ok": False, "error": "Unsupported OS"}

def list_files(path: str):
    try:
        files = os.listdir(path)
        return {"ok": True, "files": files}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    
def read_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"ok": True, "content": content[:4000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def save_memory_fact(memory_store, key: str, value: str):
    from app.memory import MemoryStore
    
    memory_store.data["facts"][key] = value
    memory_store.save()
    
    return {"ok": True, "saved": {key: value}}