"""Tests for finders memory store."""
import pytest
from pathlib import Path
from finders.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(base_dir=tmp_path)


def test_store_write_and_read(store):
    store.write_memory_file("test.md", "Hello")
    assert store.read_memory_file("test.md") == "Hello"


def test_store_append(store):
    store.append_memory_file("test.md", "Line 1")
    store.append_memory_file("test.md", "Line 2")
    content = store.read_memory_file("test.md")
    assert "Line 1" in content
    assert "Line 2" in content


def test_store_list_files(store):
    store.write_memory_file("MEMORY.md", "Long term")
    store.write_memory_file("2026-05-23.md", "Daily")
    store.write_memory_file("notes.txt", "Should not appear")

    files = store.list_memory_files()
    assert "MEMORY.md" in files
    assert "2026-05-23.md" in files
    assert "notes.txt" not in files


def test_store_read_nonexistent(store):
    assert store.read_memory_file("nonexistent.md") == ""
