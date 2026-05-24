"""Skill tool for finders."""
from langchain_core.tools import tool


@tool
async def skill(skill_name: str, args: str = "") -> str:
    """Execute a skill to get specialized instructions for complex tasks."""
    from finders.skills.registry import get_skill, discover_skills

    skill_def = get_skill(skill_name)
    if not skill_def:
        available = ", ".join(s.name for s in discover_skills())
        return f"Skill '{skill_name}' not found. Available: {available or 'none'}"

    result = f"## Skill: {skill_def.name}\n\n"
    if args:
        result += f"**Arguments:** {args}\n\n"
    result += skill_def.instructions
    return result


skill_tool = skill
