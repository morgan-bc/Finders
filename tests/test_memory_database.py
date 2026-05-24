"""Tests for finders memory database."""
import tempfile
from pathlib import Path
from finders.memory.database import MemoryDatabase
from finders.memory.types import MemoryChunk


def test_database_init():
    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryDatabase(Path(tmp) / "test.db")
        db.close()


def test_database_upsert_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryDatabase(Path(tmp) / "test.db")
        chunk = MemoryChunk(file_path="test.md", start_line=1, end_line=5, content="Hello world", content_hash="abc123")
        chunk_id = db.upsert_chunk(chunk)
        assert chunk_id > 0

        result = db.get_chunk(chunk_id)
        assert result is not None
        assert "Hello world" in result.snippet
        db.close()


def test_database_search_keyword():
    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryDatabase(Path(tmp) / "test.db")
        chunk = MemoryChunk(file_path="test.md", start_line=1, end_line=5, content="Apple revenue growth analysis", content_hash="hash1")
        db.upsert_chunk(chunk)

        results = db.search_keyword("Apple revenue", k=5)
        assert len(results) >= 1
        assert results[0]["chunk_id"] > 0
        db.close()


def test_database_delete_chunks():
    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryDatabase(Path(tmp) / "test.db")
        chunk = MemoryChunk(file_path="test.md", start_line=1, end_line=5, content="Test content", content_hash="del1")
        db.upsert_chunk(chunk)

        deleted = db.delete_chunks_for_file("test.md")
        assert deleted == 1

        # Search should return empty
        results = db.search_keyword("Test", k=5)
        assert len(results) == 0
        db.close()


def test_database_list_indexed_files():
    with tempfile.TemporaryDirectory() as tmp:
        db = MemoryDatabase(Path(tmp) / "test.db")
        db.upsert_chunk(MemoryChunk(file_path="file1.md", content="A", content_hash="f1"))
        db.upsert_chunk(MemoryChunk(file_path="file2.md", content="B", content_hash="f2"))

        files = db.list_indexed_files()
        assert "file1.md" in files
        assert "file2.md" in files
        db.close()
