"""Local sandbox with secure file system operations for Finders."""

from finders.sandbox.sandbox import (
    LocalSandbox,
    GrepMatch,
    IGNORE_PATTERNS,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_LINE_SUMMARY_LENGTH,
    should_ignore_name,
    should_ignore_path,
    path_matches,
    truncate_line,
    is_binary_file,
    find_glob_matches,
    find_grep_matches,
    list_dir,
)

__all__ = [
    "LocalSandbox",
    "GrepMatch",
    "IGNORE_PATTERNS",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_LINE_SUMMARY_LENGTH",
    "should_ignore_name",
    "should_ignore_path",
    "path_matches",
    "truncate_line",
    "is_binary_file",
    "find_glob_matches",
    "find_grep_matches",
    "list_dir",
]
