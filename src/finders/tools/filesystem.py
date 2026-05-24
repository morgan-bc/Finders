"""File system tools for finders."""
from pathlib import Path
from langchain_core.tools import tool


def safe_read(path_str: str, max_chars: int = 20000) -> str:
    """安全读取文件。"""
    path = Path(path_str)
    if not path.exists():
        return f"Error: File not found: {path_str}"
    if not path.is_file():
        return f"Error: Not a file: {path_str}"
    content = path.read_text(encoding="utf-8")
    if len(content) > max_chars:
        return content[:max_chars] + "\n\n... [truncated]"
    return content


def safe_write(path_str: str, content: str) -> str:
    """安全写入文件（需审批）。"""
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} chars to {path_str}"


@tool
async def read_file(path: str) -> str:
    """Read a local file by path. Returns file content as text."""
    return safe_read(path)


@tool
async def write_file(path: str, content: str) -> str:
    """Create or overwrite a file. Requires user approval."""
    return safe_write(path, content)
