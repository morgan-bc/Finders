"""Subagent registry for managing available subagents."""

import logging
from finders.subagents.config import SubagentConfig
from finders.subagents.builtins import BUILTIN_SUBAGENTS

logger = logging.getLogger(__name__)


def get_subagent_config(name: str) -> SubagentConfig | None:
    """Get a subagent configuration by name.

    Args:
        name: The name of the subagent.

    Returns:
        SubagentConfig if found, None otherwise.
    """
    return BUILTIN_SUBAGENTS.get(name)


def get_available_subagent_names() -> list[str]:
    """Get all available subagent names.

    Returns:
        List of subagent names.
    """
    return list(BUILTIN_SUBAGENTS.keys())
