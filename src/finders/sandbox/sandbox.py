"""Local sandbox with secure file system operations for Finders."""

import errno
import fnmatch
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

IGNORE_PATTERNS = [
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
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
class PathMapping:
    """A path mapping from a container path to a local path with optional read-only flag."""

    container_path: str
    local_path: str
    read_only: bool = False


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
    """Local sandbox restricting file operations to a workspace directory.

    Supports path mappings between container paths (seen by the agent) and local
    filesystem paths. All operations are restricted to mapped paths for security.
    """

    def __init__(
        self,
        workspace: Path | None = None,
        user_skill_dir: Path | None = None,
        project_skill_dir: Path | None = None,
        path_mappings: Optional[list[PathMapping]] = None,
    ):
        if workspace is None:
            ws_env = os.environ.get("FINDERS_WORKSPACE")
            workspace = Path(ws_env).expanduser() if ws_env else Path.home() / ".finders" / "workspace"
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Default mapping: /workspace -> actual workspace directory (read-write)
        mappings = [PathMapping("/workspace", str(self.workspace))]

        # /user_skill -> user-level skills directory (read-write)
        if user_skill_dir is not None:
            user_resolved = Path(user_skill_dir).expanduser().resolve()
            mappings.append(PathMapping("/user_skill", str(user_resolved)))

        # /proj_skill -> project-level skills directory (read-write)
        if project_skill_dir is not None:
            project_resolved = Path(project_skill_dir).expanduser().resolve()
            mappings.append(PathMapping("/proj_skill", str(project_resolved)))

        if path_mappings:
            mappings.extend(path_mappings)
        self.path_mappings = mappings

        # Track files written through write_file so read_file can reverse-resolve
        # paths in agent-authored content.
        self._agent_written_paths: set[str] = set()

    def _is_read_only_path(self, resolved_path: str) -> bool:
        """Check if a resolved path is under a read-only mapping.

        When multiple mappings match (nested mounts), prefer the most specific
        mapping (i.e. the one whose local_path is the longest prefix of the
        resolved path).
        """
        resolved = str(Path(resolved_path).resolve())

        best_mapping: Optional[PathMapping] = None
        best_prefix_len = -1

        for mapping in self.path_mappings:
            local_resolved = str(Path(mapping.local_path).resolve())
            if resolved == local_resolved or resolved.startswith(local_resolved + os.sep):
                prefix_len = len(local_resolved)
                if prefix_len > best_prefix_len:
                    best_prefix_len = prefix_len
                    best_mapping = mapping

        if best_mapping is None:
            return False

        return best_mapping.read_only

    def _resolve_path(self, path: str) -> str:
        """Resolve container path to actual local path using mappings.

        Args:
            path: Path that might be a container path

        Returns:
            Resolved local path
        """
        path_str = str(path)

        # Try each mapping (longest prefix first for more specific matches)
        for mapping in sorted(self.path_mappings, key=lambda m: len(m.container_path), reverse=True):
            container_path = mapping.container_path
            local_path = mapping.local_path
            if path_str == container_path or path_str.startswith(container_path + "/"):
                # Replace the container path prefix with local path
                relative = path_str[len(container_path):].lstrip("/")
                resolved = str(Path(local_path) / relative) if relative else local_path
                return resolved

        # No mapping found, return original path
        return path_str

    def _reverse_resolve_path(self, path: str) -> str:
        """Reverse resolve local path back to container path using mappings.

        Args:
            path: Local path that might need to be mapped to container path

        Returns:
            Container path if mapping exists, otherwise original path
        """
        # Normalize to forward slashes and resolve
        normalized_path = path.replace("\\", "/")
        path_str = str(Path(normalized_path).resolve()).replace("\\", "/")

        # Try each mapping (longest local path first for more specific matches)
        for mapping in sorted(self.path_mappings, key=lambda m: len(m.local_path), reverse=True):
            local_path_resolved = str(Path(mapping.local_path).resolve()).replace("\\", "/")
            if path_str == local_path_resolved or path_str.startswith(local_path_resolved + "/"):
                # Replace the local path prefix with container path
                relative = path_str[len(local_path_resolved):].lstrip("/")
                resolved = f"{mapping.container_path}/{relative}" if relative else mapping.container_path
                return resolved

        # No mapping found, return original path
        return path_str

    def _reverse_resolve_paths_in_output(self, output: str) -> str:
        """Reverse resolve local paths back to container paths in output string.

        Args:
            output: Output string that may contain local paths

        Returns:
            Output with local paths resolved to container paths
        """
        sorted_mappings = sorted(self.path_mappings, key=lambda m: len(m.local_path), reverse=True)

        if not sorted_mappings:
            return output

        result = output
        for mapping in sorted_mappings:
            # Get resolved local path and create pattern that matches both
            # forward and backslash separators (Windows compatibility)
            local_resolved = str(Path(mapping.local_path).resolve())
            # Escape the path, then replace escaped backslashes with a pattern
            # that matches either separator
            escaped_local = re.escape(local_resolved).replace("\\\\", r"[\\/]")
            # Match path followed by optional path components with either separator
            pattern = re.compile(escaped_local + r"(?:[\\/][^\s\"';&|<>()]*)?")

            def replace_match(match: re.Match) -> str:
                matched_path = match.group(0).replace("\\", "/")
                return self._reverse_resolve_path(matched_path)

            result = pattern.sub(replace_match, result)

        return result

    def _resolve_paths_in_command(self, command: str) -> str:
        """Resolve container paths to local paths in a command string.

        Args:
            command: Command string that may contain container paths

        Returns:
            Command with container paths resolved to local paths
        """
        sorted_mappings = sorted(self.path_mappings, key=lambda m: len(m.container_path), reverse=True)

        if not sorted_mappings:
            return command

        patterns = [
            re.escape(m.container_path) + r"(?=/|$|[\s\"';&|<>()])(?:/[^\s\"';&|<>()]*)?"
            for m in sorted_mappings
        ]
        pattern = re.compile("|".join(f"({p})" for p in patterns))

        def replace_match(match: re.Match) -> str:
            matched_path = match.group(0)
            return self._resolve_path(matched_path)

        return pattern.sub(replace_match, command)

    def _resolve_paths_in_content(self, content: str) -> str:
        """Resolve container paths to local paths in arbitrary file content.

        Unlike `_resolve_paths_in_command` which uses shell-aware boundary
        characters, this method treats the content as plain text and resolves
        every occurrence of a container path prefix. Resolved paths are
        normalized to forward slashes to avoid backslash-escape issues on
        Windows hosts.

        Args:
            content: File content that may contain container paths.

        Returns:
            Content with container paths resolved to local paths (forward slashes).
        """
        sorted_mappings = sorted(self.path_mappings, key=lambda m: len(m.container_path), reverse=True)
        if not sorted_mappings:
            return content

        patterns = [
            re.escape(m.container_path) + r"(?=/|$|[^\w./-])(?:/[^\s\"';&|<>()]*)?"
            for m in sorted_mappings
        ]
        pattern = re.compile("|".join(f"({p})" for p in patterns))

        def replace_match(match: re.Match) -> str:
            matched_path = match.group(0)
            resolved = self._resolve_path(matched_path)
            return resolved.replace("\\", "/")

        return pattern.sub(replace_match, content)

    def _resolve_and_secure(self, path: str) -> Path:
        """Resolve a path (virtual or relative) and ensure it lies within an allowed root.

        Virtual paths (e.g. /workspace, /user_skill, /proj_skill) are resolved via the
        path mappings and validated against their mapped local roots. Relative
        paths are treated as workspace-relative and secured against the workspace.
        """
        resolved_str = self._resolve_path(path)
        if resolved_str != path:
            # Path matched a virtual mapping — validate against mapped roots.
            resolved = Path(resolved_str).resolve()
            for mapping in self.path_mappings:
                local = Path(mapping.local_path).resolve()
                if resolved == local or resolved.is_relative_to(local):
                    return resolved
            raise PermissionError(
                errno.EACCES, "Path outside allowed roots", path
            )
        # Relative path — secure against the workspace root.
        target = self.workspace / path
        resolved = target.resolve()
        if not resolved.is_relative_to(self.workspace):
            raise PermissionError(
                errno.EACCES, "Path outside workspace", path
            )
        return resolved

    def read_file(self, path: str, max_chars: int = 20000) -> str:
        """Read a file within the workspace."""
        resolved = self._resolve_and_secure(path)
        if not resolved.exists():
            raise FileNotFoundError(errno.ENOENT, "File not found", path)
        if not resolved.is_file():
            raise IsADirectoryError(errno.EISDIR, "Is a directory", path)
        content = resolved.read_text(encoding="utf-8")
        # Only reverse-resolve paths in files that were previously written
        # by write_file (agent-authored content).
        if str(resolved) in self._agent_written_paths:
            content = self._reverse_resolve_paths_in_output(content)
        if len(content) > max_chars:
            return content[:max_chars] + "\n\n... [truncated]"
        return content

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        """Write content to a file within the workspace."""
        resolved = self._resolve_and_secure(path)
        if self._is_read_only_path(resolved):
            raise OSError(errno.EROFS, "Read-only file system", path)
        dir_path = resolved.parent
        if dir_path:
            dir_path.mkdir(parents=True, exist_ok=True)
        # Resolve container paths in content to local paths
        resolved_content = self._resolve_paths_in_content(content)
        mode = "a" if append else "w"
        with open(resolved, mode, encoding="utf-8") as f:
            f.write(resolved_content)
        # Track this path so read_file knows to reverse-resolve on read.
        self._agent_written_paths.add(str(resolved))

    def edit_file(self, path: str, old_string: str, new_string: str) -> None:
        """Replace old_string with new_string in a file within the workspace."""
        resolved = self._resolve_and_secure(path)
        if self._is_read_only_path(resolved):
            raise OSError(errno.EROFS, "Read-only file system", path)
        if not resolved.exists():
            raise FileNotFoundError(errno.ENOENT, "File not found", path)
        if not resolved.is_file():
            raise IsADirectoryError(errno.EISDIR, "Is a directory", path)
        content = resolved.read_text(encoding="utf-8")
        if old_string not in content:
            raise ValueError(f"old_string not found in file: {path}")
        content = content.replace(old_string, new_string, 1)
        resolved.write_text(content, encoding="utf-8")
        # Track this path as agent-authored
        self._agent_written_paths.add(str(resolved))

    def list_dir(self, path: str, max_depth: int = 2) -> list[str]:
        """List directory contents within the workspace."""
        resolved = self._resolve_and_secure(path)
        if not resolved.is_dir():
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", path)
        entries = list_dir(str(resolved), max_depth)
        # Reverse resolve local paths back to container paths in output
        return [self._reverse_resolve_paths_in_output(entry) for entry in entries]

    def glob(
        self, path: str, pattern: str, *, include_dirs: bool = False, max_results: int = 200
    ) -> tuple[list[str], bool]:
        """Find paths matching a glob pattern under a directory in the workspace."""
        resolved = self._resolve_and_secure(path)
        matches, truncated = find_glob_matches(
            resolved, pattern, include_dirs=include_dirs, max_results=max_results
        )
        return [self._reverse_resolve_path(match) for match in matches], truncated

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
        """Search for matches inside text files under a directory in the workspace."""
        resolved = self._resolve_and_secure(path)
        matches, truncated = find_grep_matches(
            resolved,
            pattern,
            glob_pattern=glob,
            literal=literal,
            case_sensitive=case_sensitive,
            max_results=max_results,
        )
        return [
            GrepMatch(
                path=self._reverse_resolve_path(match.path),
                line_number=match.line_number,
                line=match.line,
            )
            for match in matches
        ], truncated

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
        # Resolve container paths in command before execution
        resolved_command = self._resolve_paths_in_command(command)
        shell = self._get_shell()

        if os.name == "nt":
            if self._is_powershell(shell):
                args = [shell, "-NoProfile", "-Command", resolved_command]
            elif self._is_cmd_shell(shell):
                args = [shell, "/c", resolved_command]
            else:
                args = [shell, "-c", resolved_command]
            result = subprocess.run(
                args, shell=False, capture_output=True, text=True, timeout=timeout
            )
        else:
            args = [shell, "-c", resolved_command]
            result = subprocess.run(
                args, shell=False, capture_output=True, text=True, timeout=timeout
            )

        output = result.stdout
        if result.stderr:
            output += f"\nStd Error:\n{result.stderr}" if output else result.stderr
        if result.returncode != 0:
            output += f"\nExit Code: {result.returncode}"

        final_output = output if output else "(no output)"
        # Reverse resolve local paths back to container paths in output
        return self._reverse_resolve_paths_in_output(final_output)
