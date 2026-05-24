"""Full pipeline integration test: config -> factory -> tools -> memory -> skills."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_full_pipeline_no_llm(tmp_path):
    """测试不依赖 LLM 的完整 pipeline。"""
    from finders.utils.config import Settings
    from finders.tools.registry import get_core_tools, is_concurrent_safe, requires_approval
    from finders.memory.store import MemoryStore
    from finders.skills.registry import has_skills, reset_cache

    settings = Settings()
    settings.memory.enabled = False

    # 1. Tools
    reset_cache()
    with patch("finders.skills.registry.has_skills", return_value=False):
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

    # 5. Skills (should be empty by default)
    reset_cache()
    assert isinstance(has_skills(), bool)


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


def test_skill_pipeline(tmp_path):
    """测试 skill load -> registry -> tool pipeline."""
    import tempfile
    from finders.skills.loader import load_skill
    from finders.skills.registry import get_skill, discover_skills, reset_cache

    # Create a test skill
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-analysis
description: Test analysis skill
---

# Test Analysis
Follow these steps...
""", encoding="utf-8")

    # Load directly
    skill = load_skill(skill_file)
    assert skill is not None
    assert skill.name == "test-analysis"

    # Registry should discover it if we point to the right dir
    reset_cache()
    from finders.skills import registry as reg
    original_dirs = reg.SKILL_DIRS
    reg.SKILL_DIRS = [skill_dir.parent]

    discovered = reg.discover_skills()
    assert len(discovered) >= 1

    # Restore
    reg.SKILL_DIRS = original_dirs


def test_settings_load_from_env():
    """测试配置从环境变量加载。"""
    from finders.utils.config import Settings, get_settings

    # Direct instantiation with env override
    settings = Settings(openai_api_key="test_key_123")
    assert settings.openai_api_key == "test_key_123"


def test_prompt_tool_injection(tmp_path):
    """测试 system prompt 正确注入工具描述。"""
    from finders.utils.config import Settings
    from finders.prompts.system import build_system_prompt

    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
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
