"""Skill loader for finders."""
import yaml
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SkillDef:
    name: str
    description: str
    path: str
    instructions: str


def load_skill(skill_path: Path) -> SkillDef | None:
    """加载单个 SKILL.md 文件。"""
    try:
        content = skill_path.read_text(encoding="utf-8")
        # Split YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1])
                instructions = parts[2].strip()
            else:
                return None
        else:
            return None

        if not meta or "name" not in meta or "description" not in meta:
            return None

        return SkillDef(
            name=meta["name"],
            description=meta["description"],
            path=str(skill_path),
            instructions=instructions,
        )
    except Exception:
        return None
