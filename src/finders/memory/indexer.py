"""Memory indexer for finders."""
from finders.memory.chunker import chunk_memory_text
from finders.memory.database import MemoryDatabase


class MemoryIndexer:
    """将 memory 文本分块并索引到数据库。"""

    def __init__(self, database: MemoryDatabase, chunk_tokens: int = 400, chunk_overlap: int = 80):
        self.database = database
        self.chunk_tokens = chunk_tokens
        self.chunk_overlap = chunk_overlap

    def index_text(self, file_path: str, text: str) -> int:
        """分块并索引文本。"""
        # Remove old chunks for this file
        self.database.delete_chunks_for_file(file_path)

        # Chunk and index
        chunks = chunk_memory_text(file_path, text, self.chunk_tokens, self.chunk_overlap)
        indexed = 0
        for chunk in chunks:
            self.database.upsert_chunk(chunk)
            indexed += 1

        return indexed
