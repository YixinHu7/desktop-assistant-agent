import argparse
import shutil
import subprocess
from pathlib import Path


DATA_DIR = Path("data")
TRACES_PATH = DATA_DIR / "traces.jsonl"
MEMORY_PATH = DATA_DIR / "memory.json"
NOTES_DIR = DATA_DIR / "notes"


def run_agent():
    subprocess.run(["python", "main.py"], check=True)


def run_metrics():
    subprocess.run(["python", "scripts/report_metrics.py"], check=True)


def clean_traces():
    TRACES_PATH.unlink(missing_ok=True)
    print("Cleaned traces.")


def clean_notes():
    if NOTES_DIR.exists():
        shutil.rmtree(NOTES_DIR)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (NOTES_DIR / ".gitkeep").touch()
    print("Cleaned notes.")


def clean_memory():
    MEMORY_PATH.unlink(missing_ok=True)
    print("Cleaned memory.")


def reset_data():
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / ".gitkeep").touch()
    (NOTES_DIR / ".gitkeep").touch()
    print("Reset data directory.")


def main():
    parser = argparse.ArgumentParser(description="Developer commands for the agent runtime.")
    parser.add_argument(
        "command",
        choices=[
            "run",
            "metrics",
            "clean-traces",
            "clean-notes",
            "clean-memory",
            "reset-data",
        ],
    )

    args = parser.parse_args()

    if args.command == "run":
        run_agent()
    elif args.command == "metrics":
        run_metrics()
    elif args.command == "clean-traces":
        clean_traces()
    elif args.command == "clean-notes":
        clean_notes()
    elif args.command == "clean-memory":
        clean_memory()
    elif args.command == "reset-data":
        reset_data()


if __name__ == "__main__":
    main()