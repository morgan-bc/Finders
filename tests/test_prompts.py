"""Tests for finders system prompt builder."""
from finders.agents.prompt import (
    build_system_prompt,
    SYSTEM_PROMPT_TEMPLATE,
    IDENTITY_SECTION,
    DATE_SECTION,
    BEHAVIOR_SECTION,
    WORKFLOW_SECTION,
    TODO_GUIDANCE,
    TOOLS_SECTION,
)
from finders.utils.config import Settings


def test_build_system_prompt_contains_date():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    # Check that the date placeholder is replaced (should contain a weekday name)
    assert "{date}" not in prompt
    assert "Monday" in prompt or "Tuesday" in prompt or "Wednesday" in prompt or \
           "Thursday" in prompt or "Friday" in prompt or "Saturday" in prompt or "Sunday" in prompt


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
    assert "TODO" in prompt


def test_system_prompt_template_structure():
    """Test that template contains expected placeholders."""
    assert "{identity}" in SYSTEM_PROMPT_TEMPLATE
    assert "{date}" in SYSTEM_PROMPT_TEMPLATE
    assert "{core_principles}" in SYSTEM_PROMPT_TEMPLATE
    assert "{workflow}" in SYSTEM_PROMPT_TEMPLATE
    assert "{task_management}" in SYSTEM_PROMPT_TEMPLATE
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
    assert "Task Management" in prompt
    assert "Available Tools" in prompt
    assert "Evidence-driven" in prompt


def test_prompt_does_not_contain_output_format_or_skills():
    """Test that system prompt does NOT contain OUTPUT_FORMAT or Skills System sections.
    These are handled separately: output format guidance is in workflow, skills via middleware.
    """
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)

    assert "## Response Format" not in prompt
    assert "## Skills System" not in prompt
    assert "Progressive Disclosure" not in prompt
