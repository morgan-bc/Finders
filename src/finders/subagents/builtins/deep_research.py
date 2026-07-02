"""Deep research subagent configuration."""

from pathlib import Path

from finders.subagents.config import SubagentConfig


def _load_deep_research_skill() -> str:
    """Load the full content of the deep-research skill."""
    skill_path = Path(__file__).parent.parent.parent.parent.parent / "skills" / "deep-research" / "SKILL.md"
    
    if not skill_path.exists():
        raise FileNotFoundError(
            f"Deep research skill not found at {skill_path}. "
            "Please ensure the skills/deep-research/SKILL.md file exists."
        )
    
    return skill_path.read_text(encoding="utf-8")


DEEP_RESEARCH_CONFIG = SubagentConfig(
    name="deep-research",
    description="""A specialized research agent that conducts systematic, multi-angle web research following a structured methodology.

Use this subagent when:
- The task requires comprehensive research on a topic
- Multiple search angles and deep dives are needed
- Content generation requires thorough pre-research
- The question needs current, authoritative information from multiple sources

This agent automatically loads the deep-research skill methodology and follows a 4-phase research process:
1. Broad Exploration - understand the landscape
2. Deep Dive - targeted research on key dimensions
3. Diversity & Validation - ensure comprehensive coverage
4. Synthesis Check - verify research quality before reporting

Do NOT use for simple factual lookups that a single search can answer.""",
    system_prompt=_load_deep_research_skill(),
    tools=None,  # Inherit all tools from parent
    disallowed_tools=["task"],  # Prevent nesting
    model="inherit",
    max_turns=50,
    max_calls_per_tool=20,
)
