"""Memory types for finders."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemoryChunk:
    """单个记忆分块。"""

    id: Optional[int] = None
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    content: str = ""
    content_hash: str = ""
    updated_at: Optional[int] = None


@dataclass
class MemorySearchResult:
    """记忆搜索结果。"""

    snippet: str = ""
    path: str = ""
    start_line: int = 0
    end_line: int = 0
    score: float = 0.0
