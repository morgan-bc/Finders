"""Memory file-based store for finders."""
import re
from pathlib import Path
from typing import Optional
from finders.utils.paths import finders_path, ensure_dir


MEMORY_DIRNAME = "memory"
LONG_TERM_FILE = "MEMORY.md"
DAILY_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


class MemoryStore:
    """Memory 文件存储层。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or finders_path()
        self.memory_dir = self.base_dir / MEMORY_DIRNAME
        ensure_dir(self.memory_dir)

    def get_memory_dir(self) -> Path:
        return self.memory_dir

    def read_memory_file(self, path: str) -> str:
        """读取 memory 文件。"""
        file_path = self.memory_dir / path
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def write_memory_file(self, path: str, content: str) -> None:
        """写入 memory 文件。"""
        file_path = self.memory_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def append_memory_file(self, path: str, content: str) -> None:
        """追加到 memory 文件。"""
        existing = self.read_memory_file(path)
        separator = "\n" if existing and not existing.endswith("\n") else ""
        self.write_memory_file(path, existing + separator + content)

    def list_memory_files(self) -> list[str]:
        """列出所有 memory 文件。"""
        if not self.memory_dir.exists():
            return []
        return [
            f.name
            for f in self.memory_dir.iterdir()
            if f.is_file() and (f.name == LONG_TERM_FILE or DAILY_FILE_RE.match(f.name))
        ]
