"""Memory manager for finders — unified entry point for memory sync and search."""
from pathlib import Path
from finders.memory.store import MemoryStore
from finders.memory.database import MemoryDatabase
from finders.memory.indexer import MemoryIndexer
from finders.memory.search import search_memory
from finders.memory.types import MemorySearchResult


class MemoryManager:
    """Memory 系统的统一入口。"""

    def __init__(
        self,
        base_dir: Path | None = None,
        chunk_tokens: int = 400,
        chunk_overlap: int = 80,
        max_results: int = 6,
        min_score: float = 0.1,
        half_life_days: float = 30,
        mmr_lambda: float = 0.7,
    ):
        self.store = MemoryStore(base_dir=base_dir)
        self.database = MemoryDatabase(self.store.get_memory_dir() / "memory.db")
        self.indexer = MemoryIndexer(self.database, chunk_tokens, chunk_overlap)
        self.max_results = max_results
        self.min_score = min_score
        self.half_life_days = half_life_days
        self.mmr_lambda = mmr_lambda

    def sync(self) -> int:
        """同步所有 memory 文件到索引。"""
        total = 0
        for filename in self.store.list_memory_files():
            content = self.store.read_memory_file(filename)
            if content:
                indexed = self.indexer.index_text(filename, content)
                total += indexed
        return total

    def search(self, query: str) -> list[MemorySearchResult]:
        """搜索记忆。"""
        return search_memory(
            query=query,
            database=self.database,
            store=self.store,
            max_results=self.max_results,
            min_score=self.min_score,
            half_life_days=self.half_life_days,
            mmr_lambda=self.mmr_lambda,
        )

    def close(self):
        self.database.close()
