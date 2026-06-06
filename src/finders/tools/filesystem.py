"""File system tools for finders backed by LocalSandbox."""

from langchain_core.tools import tool

from finders.sandbox import LocalSandbox
from finders.utils.config import get_settings


_settings = get_settings()
_sandbox = LocalSandbox(_settings.get_workspace_path())


@tool
async def read_file(path: str) -> str:
    """Read a local file by path within the workspace. Returns file content as text."""
    try:
        return _sandbox.read_file(path)
    except Exception as e:
        return f"Error: {e}"


@tool
async def write_file(path: str, content: str) -> str:
    """Create or overwrite a file within the workspace. Requires user approval."""
    try:
        _sandbox.write_file(path, content)
        return f"Successfully wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
async def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string within the workspace. Requires user approval."""
    try:
        _sandbox.edit_file(path, old_string, new_string)
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
async def list_dir(path: str, max_depth: int = 2) -> str:
    """List files and directories up to max_depth levels deep within the workspace."""
    try:
        entries = _sandbox.list_dir(path, max_depth)
        if not entries:
            return "(empty directory)"
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {e}"


@tool
async def glob(path: str, pattern: str) -> str:
    """Find files matching a glob pattern under a directory in the workspace."""
    try:
        matches, truncated = _sandbox.glob(path, pattern)
        if not matches:
            return "(no matches)"
        result = "\n".join(matches)
        if truncated:
            result += "\n... [truncated]"
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
async def grep(path: str, pattern: str, glob_pattern: str | None = None) -> str:
    """Search for text matches inside files under a directory in the workspace."""
    try:
        matches, truncated = _sandbox.grep(path, pattern, glob=glob_pattern)
        if not matches:
            return "(no matches)"
        lines = []
        for m in matches:
            lines.append(f"{m.path}:{m.line_number}: {m.line}")
        result = "\n".join(lines)
        if truncated:
            result += "\n... [truncated]"
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
async def execute(command: str) -> str:
    """Execute a shell command and return its output."""
    try:
        return _sandbox.execute(command)
    except Exception as e:
        return f"Error: {e}"
