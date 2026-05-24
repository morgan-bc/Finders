"""Tests for finders filesystem tools."""
from finders.tools.filesystem import safe_read, safe_write


def test_safe_read_file_not_found(tmp_path):
    result = safe_read(str(tmp_path / "nonexistent.txt"))
    assert "Error: File not found" in result


def test_safe_write_and_read(tmp_path):
    path = str(tmp_path / "test.txt")
    write_result = safe_write(path, "Hello world")
    assert "Successfully wrote" in write_result

    read_result = safe_read(path)
    assert read_result == "Hello world"


def test_safe_read_truncate(tmp_path):
    path = str(tmp_path / "large.txt")
    safe_write(path, "x" * 30000)
    result = safe_read(path, max_chars=20000)
    assert "[truncated]" in result
    assert len(result) <= 20100
