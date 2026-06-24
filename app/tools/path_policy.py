from pathlib import Path

from app.config import config


class ToolPathPolicyError(ValueError):
    """Raised when a tool path violates the configured path policy."""


def get_eval_fixture_root() -> Path:
    if not config.eval_fixture_root:
        raise ToolPathPolicyError(
            "EVAL_FIXTURE_ROOT is required when EVAL_MODE=true."
        )

    root = Path(config.eval_fixture_root).expanduser().resolve()

    if not root.exists():
        raise ToolPathPolicyError(
            f"Evaluation fixture root does not exist: {root}"
        )

    if not root.is_dir():
        raise ToolPathPolicyError(
            f"Evaluation fixture root is not a directory: {root}"
        )

    return root


def resolve_tool_path(path: str) -> Path:
    raw_path = Path(path).expanduser()

    if not config.eval_mode:
        return raw_path.resolve()

    fixture_root = get_eval_fixture_root()

    if raw_path.is_absolute():
        resolved = raw_path.resolve()
    else:
        resolved = (fixture_root / raw_path).resolve()

    try:
        resolved.relative_to(fixture_root)
    except ValueError as exc:
        raise ToolPathPolicyError(
            f"Evaluation tools cannot access paths outside the fixture root: {path}"
        ) from exc

    return resolved


def display_tool_path(path: Path) -> str:
    resolved = path.resolve()

    if not config.eval_mode:
        return str(resolved)

    fixture_root = get_eval_fixture_root()

    try:
        relative = resolved.relative_to(fixture_root)
    except ValueError:
        return str(resolved)

    return "." if str(relative) == "." else str(relative)