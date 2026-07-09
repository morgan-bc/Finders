"""Local sandbox with secure file system operations for Finders."""

import errno
import fnmatch
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

IGNORE_PATTERNS = [
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    "node_modules",
    "__pycache__",
    ".env",
    "env",
    ".tox",
    ".nox",
    ".eggs",
    "*.egg-info",
    "site-packages",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    "target",
    "out",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~",
    ".project",
    ".classpath",
    ".settings",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "*.lnk",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.cache",
    ".cache",
    "logs",
    ".coverage",
    "coverage",
    ".nyc_output",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

DEFAULT_MAX_FILE_SIZE_BYTES = 1_000_000
DEFAULT_LINE_SUMMARY_LENGTH = 200


@dataclass(frozen=True)
class GrepMatch:
    """A single grep match result."""

    path: str
    line_number: int
    line: str


def should_ignore_name(name: str) -> bool:
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def should_ignore_path(path: str) -> bool:
    return any(should_ignore_name(segment) for segment in path.replace("\\", "/").split("/") if segment)


def path_matches(pattern: str, rel_path: str) -> bool:
    path = PurePosixPath(rel_path)
    if path.match(pattern):
        return True
    if pattern.startswith("**/"):
        return path.match(pattern[3:])
    return False


def truncate_line(line: str, max_chars: int = DEFAULT_LINE_SUMMARY_LENGTH) -> str:
    line = line.rstrip("\n\r")
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 3] + "..."


def is_binary_file(path: Path, sample_size: int = 8192) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(sample_size)
    except OSError:
        return True


def find_glob_matches(
    root: Path, pattern: str, *, include_dirs: bool = False, max_results: int = 200
) -> tuple[list[str], bool]:
    matches: list[str] = []
    truncated = False
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not should_ignore_name(name)]
        rel_dir = Path(current_root).relative_to(root)

        if include_dirs:
            for name in dirs:
                rel_path = (rel_dir / name).as_posix()
                if path_matches(pattern, rel_path):
                    matches.append(str(Path(current_root) / name))
                    if len(matches) >= max_results:
                        truncated = True
                        return matches, truncated

        for name in files:
            if should_ignore_name(name):
                continue
            rel_path = (rel_dir / name).as_posix()
            if path_matches(pattern, rel_path):
                matches.append(str(Path(current_root) / name))
                if len(matches) >= max_results:
                    truncated = True
                    return matches, truncated

    return matches, truncated


def find_grep_matches(
    root: Path,
    pattern: str,
    *,
    glob_pattern: str | None = None,
    literal: bool = False,
    case_sensitive: bool = False,
    max_results: int = 100,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    line_summary_length: int = DEFAULT_LINE_SUMMARY_LENGTH,
) -> tuple[list[GrepMatch], bool]:
    matches: list[GrepMatch] = []
    truncated = False
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    regex_source = re.escape(pattern) if literal else pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(regex_source, flags)

    _max_line_chars = line_summary_length * 10

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not should_ignore_name(name)]
        rel_dir = Path(current_root).relative_to(root)

        for name in files:
            if should_ignore_name(name):
                continue

            candidate_path = Path(current_root) / name
            rel_path = (rel_dir / name).as_posix()

            if glob_pattern is not None and not path_matches(glob_pattern, rel_path):
                continue

            try:
                if candidate_path.is_symlink():
                    continue
                file_path = candidate_path.resolve()
                if not file_path.is_relative_to(root):
                    continue
                if file_path.stat().st_size > max_file_size or is_binary_file(file_path):
                    continue
                with file_path.open(encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if len(line) > _max_line_chars:
                            continue
                        if regex.search(line):
                            matches.append(
                                GrepMatch(
                                    path=str(file_path),
                                    line_number=line_number,
                                    line=truncate_line(line, line_summary_length),
                                )
                            )
                            if len(matches) >= max_results:
                                truncated = True
                                return matches, truncated
            except OSError:
                continue

    return matches, truncated


def list_dir(path: str, max_depth: int = 2) -> list[str]:
    """List files and directories up to max_depth levels deep."""
    result: list[str] = []
    root_path = Path(path).resolve()

    if not root_path.is_dir():
        return result

    def _traverse(current_path: Path, current_depth: int) -> None:
        if current_depth > max_depth:
            return

        try:
            for item in current_path.iterdir():
                if should_ignore_name(item.name):
                    continue

                post_fix = "/" if item.is_dir() else ""
                result.append(str(item.resolve()) + post_fix)

                if item.is_dir() and current_depth < max_depth:
                    _traverse(item, current_depth + 1)
        except PermissionError:
            pass

    _traverse(root_path, 1)
    return sorted(result)


class LocalSandbox:
    """Local sandbox using real filesystem paths.

    Write operations (write_file, edit_file) are restricted to workspace,
    user_skill_dir, and project_skill_dir. All other paths are read-only.
    """

    def __init__(
        self,
        workspace: Path | None = None,
        user_skill_dir: Path | None = None,
        project_skill_dir: Path | None = None,
    ):
        if workspace is None:
            ws_env = os.environ.get("FINDERS_WORKSPACE")
            workspace = Path(ws_env).expanduser() if ws_env else Path.home() / ".finders" / "workspace"
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.user_skill_dir = Path(user_skill_dir).expanduser().resolve() if user_skill_dir else None
        self.project_skill_dir = Path(project_skill_dir).expanduser().resolve() if project_skill_dir else None

        # Build list of allowed write roots
        self._allowed_write_roots: list[Path] = [self.workspace]
        if self.user_skill_dir is not None:
            self._allowed_write_roots.append(self.user_skill_dir)
        if self.project_skill_dir is not None:
            self._allowed_write_roots.append(self.project_skill_dir)

    def _is_writable(self, resolved_path: Path) -> bool:
        """Check if a resolved path is under an allowed write root."""
        for root in self._allowed_write_roots:
            if resolved_path == root or resolved_path.is_relative_to(root):
                return True
        return False

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path to an absolute real path.

        Relative paths are treated as workspace-relative.
        Absolute paths are used directly.
        """
        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self.workspace / path).resolve()
        return resolved

    def read_file(self, path: str, max_chars: int = 20000) -> str:
        """Read a file. All paths are readable."""
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(errno.ENOENT, "File not found", path)
        if not resolved.is_file():
            raise IsADirectoryError(errno.EISDIR, "Is a directory", path)
        content = resolved.read_text(encoding="utf-8")
        if len(content) > max_chars:
            return content[:max_chars] + "\n\n... [truncated]"
        return content

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        """Write content to a file. Restricted to allowed write directories."""
        resolved = self._resolve_path(path)
        if not self._is_writable(resolved):
            raise PermissionError(
                errno.EACCES, "Path is read-only, writes restricted to workspace and skill directories", path
            )
        dir_path = resolved.parent
        if dir_path:
            dir_path.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(resolved, mode, encoding="utf-8") as f:
            f.write(content)

    def edit_file(self, path: str, old_string: str, new_string: str) -> None:
        """Replace old_string with new_string in a file. Restricted to allowed write directories."""
        resolved = self._resolve_path(path)
        if not self._is_writable(resolved):
            raise PermissionError(
                errno.EACCES, "Path is read-only, writes restricted to workspace and skill directories", path
            )
        if not resolved.exists():
            raise FileNotFoundError(errno.ENOENT, "File not found", path)
        if not resolved.is_file():
            raise IsADirectoryError(errno.EISDIR, "Is a directory", path)
        content = resolved.read_text(encoding="utf-8")
        if old_string not in content:
            raise ValueError(f"old_string not found in file: {path}")
        content = content.replace(old_string, new_string, 1)
        resolved.write_text(content, encoding="utf-8")

    def list_dir(self, path: str, max_depth: int = 2) -> list[str]:
        """List directory contents."""
        resolved = self._resolve_path(path)
        if not resolved.is_dir():
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", path)
        return list_dir(str(resolved), max_depth)

    def glob(
        self, path: str, pattern: str, *, include_dirs: bool = False, max_results: int = 200
    ) -> tuple[list[str], bool]:
        """Find paths matching a glob pattern under a directory."""
        resolved = self._resolve_path(path)
        return find_glob_matches(resolved, pattern, include_dirs=include_dirs, max_results=max_results)

    def grep(
        self,
        path: str,
        pattern: str,
        *,
        glob: str | None = None,
        literal: bool = False,
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> tuple[list[GrepMatch], bool]:
        """Search for matches inside text files under a directory."""
        resolved = self._resolve_path(path)
        return find_grep_matches(
            resolved,
            pattern,
            glob_pattern=glob,
            literal=literal,
            case_sensitive=case_sensitive,
            max_results=max_results,
        )

    @staticmethod
    def _shell_name(shell: str) -> str:
        return shell.replace("\\", "/").rsplit("/", 1)[-1].lower()

    @staticmethod
    def _is_powershell(shell: str) -> bool:
        return LocalSandbox._shell_name(shell) in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}

    @staticmethod
    def _is_cmd_shell(shell: str) -> bool:
        return LocalSandbox._shell_name(shell) in {"cmd", "cmd.exe"}

    @staticmethod
    def _find_first_available_shell(candidates: tuple[str, ...]) -> str | None:
        for shell in candidates:
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
                continue
            shell_from_path = shutil.which(shell)
            if shell_from_path is not None:
                return shell_from_path
        return None

    @staticmethod
    def _get_shell() -> str:
        shell = LocalSandbox._find_first_available_shell(("/bin/zsh", "/bin/bash", "/bin/sh", "sh"))
        if shell is not None:
            return shell

        if os.name == "nt":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            shell = LocalSandbox._find_first_available_shell(
                (
                    "pwsh",
                    "pwsh.exe",
                    "powershell",
                    "powershell.exe",
                    os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
                    "cmd.exe",
                )
            )
            if shell is not None:
                return shell
            raise RuntimeError("No suitable shell executable found on Windows.")

        raise RuntimeError("No suitable shell executable found.")

    def execute(self, command: str, timeout: int = 600) -> str:
        """Execute a shell command and return its output."""
        shell = self._get_shell()

        if os.name == "nt":
            if self._is_powershell(shell):
                args = [shell, "-NoProfile", "-Command", command]
            elif self._is_cmd_shell(shell):
                args = [shell, "/c", command]
            else:
                args = [shell, "-c", command]
            result = subprocess.run(
                args, shell=False, capture_output=True, text=True, timeout=timeout
            )
        else:
            args = [shell, "-c", command]
            result = subprocess.run(
                args, shell=False, capture_output=True, text=True, timeout=timeout
            )

        output = result.stdout
        if result.stderr:
            output += f"\nStd Error:\n{result.stderr}" if output else result.stderr
        if result.returncode != 0:
            output += f"\nExit Code: {result.returncode}"

        return output if output else "(no output)"
