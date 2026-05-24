"""Tests for finders memory chunker."""
from finders.memory.chunker import split_into_paragraphs, chunk_memory_text


def test_split_into_paragraphs():
    text = "Para 1\n\nPara 2\n\nPara 3"
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) == 3
    assert paragraphs[0][2] == "Para 1"


def test_chunk_memory_text():
    text = "Content A\n\nContent B\n\nContent C"
    chunks = chunk_memory_text("test.md", text, chunk_tokens=1000)
    assert len(chunks) >= 1
    assert chunks[0].file_path == "test.md"
    assert chunks[0].content_hash


def test_chunk_empty_text():
    chunks = chunk_memory_text("test.md", "", chunk_tokens=100)
    assert len(chunks) == 0
