"""Tests for finders agent factory."""
import os
import pytest
from unittest.mock import patch, MagicMock
from finders.utils.config import Settings
from finders.agent.factory import create_finders_agent


@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("finders.agent.factory.create_agent")
def test_create_agent_with_middleware(mock_create):
    mock_create.return_value = MagicMock()
    settings = Settings()
    settings.memory.enabled = False

    agent = create_finders_agent(settings)

    # Verify create_agent was called
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs

    # Verify middleware list exists
    assert "middleware" in call_kwargs
    # TodoList, Summarization, ContextEditing, ToolCallLimit, ToolRetry, ModelRetry, HITL
    assert len(call_kwargs["middleware"]) >= 5


@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("finders.agent.factory.create_agent")
def test_create_agent_has_tools_and_prompt(mock_create):
    mock_create.return_value = MagicMock()
    settings = Settings()
    settings.memory.enabled = False

    with patch("finders.skills.registry.has_skills", return_value=False):
        agent = create_finders_agent(settings)

    call_kwargs = mock_create.call_args.kwargs
    assert "tools" in call_kwargs
    assert "system_prompt" in call_kwargs
    assert "Dexter" in call_kwargs["system_prompt"]
