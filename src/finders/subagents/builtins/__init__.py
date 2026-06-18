"""Built-in subagent configurations."""

from .general_purpose import GENERAL_PURPOSE_CONFIG
from .deep_research import DEEP_RESEARCH_CONFIG

__all__ = [
    "GENERAL_PURPOSE_CONFIG",
    "DEEP_RESEARCH_CONFIG",
]

# Registry of built-in subagents
BUILTIN_SUBAGENTS = {
    "general-purpose": GENERAL_PURPOSE_CONFIG,
    "deep-research": DEEP_RESEARCH_CONFIG,
}
