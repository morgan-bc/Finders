"""Tests for finders memory middleware."""
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from finders.middleware.memory import MemoryMiddleware


def test_memory_middleware_init():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        assert mw.flush_threshold == 140_000
        assert mw._already_flushed is False
        assert (Path(tmp) / "memory").exists()


def test_memory_middleware_load_empty():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        result = mw._load_permanent_memories()
        assert result == ""


def test_memory_middleware_load_permanent():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        # Create permanent memory file
        permanent = Path(tmp) / "memory" / "MEMORY.md"
        permanent.write_text("User prefers tech stocks.", encoding="utf-8")

        result = mw._load_permanent_memories()
        assert "Long-term Memory" in result
        assert "tech stocks" in result


def test_memory_middleware_load_daily():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        # Create yesterday's daily file
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        daily = Path(tmp) / "memory" / f"{yesterday.strftime('%Y-%m-%d')}.md"
        daily.write_text("Analyzed AAPL earnings.", encoding="utf-8")

        result = mw._load_permanent_memories()
        assert "Analyzed AAPL" in result


def test_memory_middleware_before_model_no_memories():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        state = {"messages": []}
        runtime = MagicMock()
        result = mw.before_model(state, runtime)
        assert result is None


def test_memory_middleware_before_model_with_memories():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        permanent = Path(tmp) / "memory" / "MEMORY.md"
        permanent.write_text("User is risk-averse.", encoding="utf-8")

        from langchain_core.messages import SystemMessage
        state = {"messages": [SystemMessage(content="You are Dexter.")]}
        runtime = MagicMock()
        result = mw.before_model(state, runtime)

        assert result is not None
        updated_messages = result["messages"]
        assert "Memory Context" in updated_messages[0].content


def test_memory_middleware_daily_file_append():
    with tempfile.TemporaryDirectory() as tmp:
        mw = MemoryMiddleware(memory_dir=tmp)
        mw._append_to_daily("Test fact")

        today = Path(tmp) / "memory" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        assert today.exists()
        content = today.read_text(encoding="utf-8")
        assert "Test fact" in content
        assert "Pre-compaction memory flush" in content
