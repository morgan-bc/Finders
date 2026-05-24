"""Tests for finders system prompt builder."""
from unittest.mock import patch
from finders.prompts.system import build_system_prompt
from finders.utils.config import Settings


def test_build_system_prompt_contains_date():
    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
        prompt = build_system_prompt(settings)
    # Check that the date placeholder is replaced (should contain a weekday name)
    assert "{{date}}" not in prompt


def test_build_system_prompt_contains_tools():
    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
        prompt = build_system_prompt(settings)
    assert "web_search" in prompt
    assert "web_fetch" in prompt


def test_build_system_prompt_contains_behavior():
    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
        prompt = build_system_prompt(settings)
    assert "Behavior" in prompt
    assert "TODO" in prompt


def test_build_system_prompt_template_not_found():
    """Test that template file is loaded without error."""
    from finders.prompts.system import _load_template
    template = _load_template()
    assert "{{date}}" in template
    assert "{{tool_descriptions}}" in template
