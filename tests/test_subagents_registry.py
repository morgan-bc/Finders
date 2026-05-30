# tests/test_subagents_registry.py
from finders.subagents.registry import get_subagent_config, get_available_subagent_names

def test_get_available_subagent_names():
    names = get_available_subagent_names()
    assert isinstance(names, list)
    assert "general-purpose" in names

def test_get_subagent_config_returns_config():
    config = get_subagent_config("general-purpose")
    assert config is not None
    assert config.name == "general-purpose"

def test_get_subagent_config_returns_none_for_unknown():
    config = get_subagent_config("nonexistent")
    assert config is None

def test_general_purpose_config():
    from finders.subagents.builtins.general_purpose import GENERAL_PURPOSE_CONFIG
    assert GENERAL_PURPOSE_CONFIG.name == "general-purpose"
    assert GENERAL_PURPOSE_CONFIG.max_turns == 50
    assert "task" in GENERAL_PURPOSE_CONFIG.disallowed_tools
