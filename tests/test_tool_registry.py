"""Tests for finders tool registry."""
import pytest
from unittest.mock import patch
from finders.tools.registry import (
    get_core_tools,
    is_concurrent_safe,
    requires_approval,
)
from finders.utils.config import Settings


def test_concurrent_safe_tools():
    assert is_concurrent_safe("web_search") is True
    assert is_concurrent_safe("read_file") is True
    assert is_concurrent_safe("write_file") is False


def test_approval_tools():
    assert requires_approval("write_file") is True
    assert requires_approval("web_search") is False


def test_get_core_tools_basic():
    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
        tools = get_core_tools(settings)
    assert len(tools) == 5
    tool_names = [t.name for t in tools]
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
    assert "task" in tool_names
