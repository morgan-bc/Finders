"""SQLite vector database for finders memory (FTS5-based)."""
import sqlite3
from pathlib import Path
from finders.memory.types import MemoryChunk, MemorySearchResult


class MemoryDatabase:
    """SQLite 向量数据库（基础版：仅 FTS5）。"""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content, chunk_id UNINDEXED
            );
        """)

    def upsert_chunk(self, chunk: MemoryChunk) -> int:
        """插入或更新 chunk，返回 chunk ID。"""
        try:
            cursor = self.conn.execute(
                "INSERT INTO chunks (file_path, start_line, end_line, content, content_hash) VALUES (?, ?, ?, ?, ?)",
                (chunk.file_path, chunk.start_line, chunk.end_line, chunk.content, chunk.content_hash),
            )
            self.conn.execute(
                "INSERT INTO chunks_fts (content, chunk_id) VALUES (?, ?)",
                (chunk.content, cursor.lastrowid),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor = self.conn.execute(
                "SELECT id FROM chunks WHERE content_hash = ?", (chunk.content_hash,)
            )
            row = cursor.fetchone()
            if row:
                self.conn.execute(
                    "UPDATE chunks SET file_path=?, start_line=?, end_line=?, content=?, updated_at=strftime('%s', 'now') WHERE id=?",
                    (chunk.file_path, chunk.start_line, chunk.end_line, chunk.content, row["id"]),
                )
                self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["id"],))
                self.conn.execute(
                    "INSERT INTO chunks_fts (content, chunk_id) VALUES (?, ?)",
                    (chunk.content, row["id"]),
                )
                self.conn.commit()
                return row["id"]
            raise

    def search_keyword(self, query: str, k: int = 20) -> list[dict]:
        """关键词搜索（FTS5）。"""
        tokens = [t for t in query.split() if len(t) > 2]
        if not tokens:
            return []
        fts_query = " AND ".join(f'"{t}"' for t in tokens)

        cursor = self.conn.execute(
            "SELECT chunk_id, rank FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, k),
        )
        return [{"chunk_id": row["chunk_id"], "score": 1 / (1 + max(0, row["rank"]))} for row in cursor]

    def get_chunk(self, chunk_id: int) -> MemorySearchResult | None:
        """按 ID 获取 chunk。"""
        cursor = self.conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return MemorySearchResult(
            snippet=row["content"][:700],
            path=row["file_path"],
            start_line=row["start_line"],
            end_line=row["end_line"],
        )

    def delete_chunks_for_file(self, file_path: str) -> int:
        """删除文件的所有 chunks。"""
        cursor = self.conn.execute("SELECT id FROM chunks WHERE file_path = ?", (file_path,))
        ids = [row["id"] for row in cursor]
        for chunk_id in ids:
            self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
        self.conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path,))
        self.conn.commit()
        return len(ids)

    def list_indexed_files(self) -> list[str]:
        """列出已索引文件。"""
        cursor = self.conn.execute("SELECT DISTINCT file_path FROM chunks")
        return [row["file_path"] for row in cursor]

    def close(self):
        self.conn.close()
