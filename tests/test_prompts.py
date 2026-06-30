"""Tests for finders system prompt builder."""
from finders.agents.prompt import (
    build_system_prompt,
    SYSTEM_PROMPT_TEMPLATE,
    IDENTITY_SECTION,
    INSTRUCTION_SECTION,
    TOOLS_SECTION,
)
from finders.utils.config import Settings


def test_build_system_prompt_contains_tools():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    assert "web_search" in prompt
    assert "web_fetch" in prompt


def test_build_system_prompt_contains_behavior():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    assert "Core Principles" in prompt


def test_system_prompt_template_structure():
    """Test that template contains expected placeholders."""
    assert "{identity}" in SYSTEM_PROMPT_TEMPLATE
    assert "{instruction}" in SYSTEM_PROMPT_TEMPLATE
    assert "{tools}" in SYSTEM_PROMPT_TEMPLATE


def test_prompt_contains_all_sections():
    """Test that the built prompt contains all expected sections."""
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)

    assert "Finders" in prompt
    assert "financial research assistant" in prompt
    assert "Core Principles" in prompt
    assert "Research Workflow" in prompt
    assert "Available Tools" in prompt
    assert "Evidence-driven" in prompt


def test_prompt_does_not_contain_middleware_sections():
    """Test that system prompt does NOT contain sections handled by middleware.
    - TODO guidance → TodoListMiddleware
    - Skills → SkillsMiddleware
    - Date → DynamicContextMiddleware
    - Output format → handled in workflow guidance
    """
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)

    assert "## Task Management" not in prompt
    assert "## Skills System" not in prompt
    assert "## Current Date" not in prompt
    assert "## Date" not in prompt
    assert "## Response Format" not in prompt
    assert "Progressive Disclosure" not in prompt
    assert "{{date}}" not in prompt
    assert "{date}" not in prompt
