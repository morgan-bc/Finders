"""Full pipeline integration test: config -> factory -> tools -> memory."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_full_pipeline_no_llm(tmp_path):
    """测试不依赖 LLM 的完整 pipeline。"""
    from finders.utils.config import Settings
    from finders.tools.registry import get_core_tools, is_concurrent_safe, requires_approval
    from finders.memory.store import MemoryStore

    settings = Settings()
    settings.memory.enabled = False

    # 1. Tools
    tools = get_core_tools(settings)
    assert len(tools) >= 4

    # 2. Concurrency metadata
    assert is_concurrent_safe("web_search") is True
    assert is_concurrent_safe("read_file") is True
    assert is_concurrent_safe("write_file") is False

    # 3. Approval metadata
    assert requires_approval("write_file") is True
    assert requires_approval("web_search") is False

    # 4. Memory Store
    store = MemoryStore(base_dir=tmp_path)
    store.write_memory_file("MEMORY.md", "Test memory")
    assert store.read_memory_file("MEMORY.md") == "Test memory"


def test_memory_pipeline(tmp_path):
    """测试完整 memory pipeline: store -> indexer -> search."""
    from finders.memory.store import MemoryStore
    from finders.memory.database import MemoryDatabase
    from finders.memory.indexer import MemoryIndexer
    from finders.memory.search import search_memory

    store = MemoryStore(base_dir=tmp_path)
    database = MemoryDatabase(store.get_memory_dir() / "memory.db")
    indexer = MemoryIndexer(database)

    # Write and index memory content
    content = "## Analysis\nUser prefers growth stocks over value stocks.\nTech sector focus on AI."
    store.write_memory_file("2026-05-20.md", content)
    indexed = indexer.index_text("2026-05-20.md", content)
    assert indexed >= 1

    # Search should find relevant results
    results = search_memory("growth stocks", database, store)
    assert len(results) >= 1
    assert "growth" in results[0].snippet.lower() or "stocks" in results[0].snippet.lower()

    database.close()


def test_settings_load_from_env():
    """测试配置从环境变量加载。"""
    from finders.utils.config import Settings, get_settings

    # Direct instantiation with env override
    settings = Settings(llm_api_key="test_key_123")
    assert settings.llm_api_key == "test_key_123"


def test_prompt_tool_injection(tmp_path):
    """测试 system prompt 正确注入工具描述。"""
    from finders.utils.config import Settings
    from finders.agents.prompt import build_system_prompt

    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)

    # Should contain all core tools
    assert "web_search" in prompt
    assert "web_fetch" in prompt
    assert "read_file" in prompt
    assert "write_file" in prompt

    # Should have date replaced
    assert "{{date}}" not in prompt
    # Should have tools replaced
    assert "{{tool_descriptions}}" not in prompt
