"""Tests for finders memory search pipeline."""
import tempfile
from pathlib import Path
from finders.memory.database import MemoryDatabase
from finders.memory.store import MemoryStore
from finders.memory.search import search_memory, _time_decay_score, _mmr_deduplicate
from finders.memory.types import MemorySearchResult
from finders.memory.indexer import MemoryIndexer
from datetime import datetime, timedelta


def test_time_decay_score():
    recent = datetime.now() - timedelta(days=1)
    old = datetime.now() - timedelta(days=90)

    score_recent = _time_decay_score(1.0, recent, half_life_days=30)
    score_old = _time_decay_score(1.0, old, half_life_days=30)

    assert score_recent > score_old


def test_time_decay_score_no_date():
    assert _time_decay_score(1.0, None) == 1.0


def test_mmr_deduplicate():
    results = [
        MemorySearchResult(snippet="A", path="file1.md", score=0.9),
        MemorySearchResult(snippet="B", path="file1.md", score=0.8),
        MemorySearchResult(snippet="C", path="file2.md", score=0.7),
        MemorySearchResult(snippet="D", path="file3.md", score=0.6),
    ]

    result = _mmr_deduplicate(results, k=3, lam=0.7)
    assert len(result) == 3


def test_mmr_no_dedup_needed():
    results = [
        MemorySearchResult(snippet="A", path="file1.md", score=0.9),
    ]
    result = _mmr_deduplicate(results, k=3)
    assert len(result) == 1


def test_search_memory_integration():
    """Full pipeline test: index + search."""
    with tempfile.TemporaryDirectory() as tmp:
        store = MemoryStore(base_dir=Path(tmp))
        database = MemoryDatabase(store.get_memory_dir() / "memory.db")
        indexer = MemoryIndexer(database)

        # Index some test content
        content = """## Session Notes
Analyzed Apple stock performance. Revenue growth is strong.
The company's services segment is expanding.
"""
        store.write_memory_file("2026-05-20.md", content)
        indexer.index_text("2026-05-20.md", content)

        # Search
        results = search_memory("Apple revenue growth", database, store)
        assert len(results) >= 1
        assert "Apple" in results[0].snippet or "revenue" in results[0].snippet

        database.close()
