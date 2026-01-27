import re
from pathlib import Path

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    """Return a deterministic, filesystem-safe filename (no traversal).

    - Reject path traversal and absolute path attempts.
    - Replace separators with underscores and collapse unsafe chars.
    - Remove leading dots to avoid hidden files.
    - Return 'export' if result is empty.
    """
    raw = str(name or "").strip()
    normalized = raw.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("Path traversal not allowed")
    cleaned_join = "_".join(parts)
    cleaned = SAFE_FILENAME_RE.sub("_", cleaned_join)
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    cleaned = cleaned.lstrip(".")
    return cleaned or "export"


def build_export_path(base_dir: Path, filename: str) -> Path:
    safe = sanitize_filename(filename)
    path = base_dir / safe
    # Ensure the final path stays within base_dir
    resolved_base = base_dir.resolve()
    resolved_path = path.resolve()
    if not str(resolved_path).startswith(str(resolved_base)):
        raise ValueError("Export path escapes base directory")
    return resolved_path
