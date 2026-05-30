"""Tests for finders configuration system."""
import pytest
from finders.utils.config import Settings, AgentConfig, MemoryConfig, ToolConfig


def test_default_settings():
    settings = Settings(_env_file=None)
    assert settings.agent.model == "deepseek-v4-flash"
    assert settings.agent.max_iterations == 10
    assert settings.memory.enabled is True
    assert settings.memory.mmr_lambda == 0.7


def test_agent_config_validation():
    with pytest.raises(Exception):
        AgentConfig(max_iterations=0)

    with pytest.raises(Exception):
        MemoryConfig(chunk_tokens=50)


def test_agent_config_enable_todo():
    config = AgentConfig()
    assert config.enable_todo is True

    config_disabled = AgentConfig(enable_todo=False)
    assert config_disabled.enable_todo is False


def test_tool_config_defaults():
    config = ToolConfig()
    assert config.web_search_provider == "tavily"
    assert config.max_concurrency == 10
