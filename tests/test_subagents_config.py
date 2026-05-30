# tests/test_subagents_config.py
from finders.subagents.config import SubagentConfig

def test_subagent_config_defaults():
    config = SubagentConfig(
        name="test",
        description="Test subagent",
        system_prompt="You are a test agent.",
    )
    assert config.name == "test"
    assert config.tools is None
    assert config.disallowed_tools == ["task"]
    assert config.model == "inherit"
    assert config.max_turns == 50
    assert config.timeout_seconds == 900
