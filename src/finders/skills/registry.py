"""Skill registry for finders."""
from pathlib import Path
from finders.skills.loader import SkillDef, load_skill

# Skill directories to scan
SKILL_DIRS = [
    Path(__file__).parent.parent.parent.parent / "skills",  # Built-in skills
    Path.home() / ".finders" / "skills",  # User skills
]

_skill_cache: dict[str, SkillDef] = {}


def discover_skills() -> list[SkillDef]:
    """发现所有可用 skills。"""
    global _skill_cache
    if _skill_cache:
        return list(_skill_cache.values())

    for skill_dir in SKILL_DIRS:
        if not skill_dir.exists():
            continue
        for skill_file in skill_dir.rglob("SKILL.md"):
            skill = load_skill(skill_file)
            if skill:
                _skill_cache[skill.name] = skill

    return list(_skill_cache.values())


def get_skill(name: str) -> SkillDef | None:
    """按名称获取 skill。"""
    if not _skill_cache:
        discover_skills()
    return _skill_cache.get(name)


def has_skills() -> bool:
    return len(discover_skills()) > 0


def reset_cache() -> None:
    """Reset skill cache (for testing)."""
    global _skill_cache
    _skill_cache = {}
