import platform
import subprocess

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