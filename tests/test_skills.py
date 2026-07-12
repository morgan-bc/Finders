"""Tests for finders skills system."""
from pathlib import Path
import tempfile
from finders.skills.load import list_skills, _parse_skill_metadata, SkillMetadata


def test_parse_skill_metadata(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: A test skill
---

# Test Skill Instructions
Do something useful.
""", encoding="utf-8")

    result = _parse_skill_metadata(skill_file)
    assert result is not None
    assert result["name"] == "test-skill"
    assert result["description"] == "A test skill"


def test_parse_skill_metadata_missing_fields(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\nInstructions", encoding="utf-8")
    assert _parse_skill_metadata(skill_file) is None


def test_parse_skill_metadata_no_frontmatter(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("No yaml frontmatter", encoding="utf-8")
    assert _parse_skill_metadata(skill_file) is None


def test_list_skills_empty(tmp_path):
    skills = list_skills([tmp_path / "nonexistent"])
    assert isinstance(skills, list)
    assert len(skills) == 0


def test_list_skills_user(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
---

Instructions here.
""", encoding="utf-8")

    skills = list_skills([skills_dir])
    assert len(skills) == 1
    assert skills[0]["name"] == "test-skill"


def test_list_skills_project_overrides_user(tmp_path):
    user_dir = tmp_path / "user_skills"
    project_dir = tmp_path / "project_skills"
    user_dir.mkdir()
    project_dir.mkdir()

    # User skill
    (user_dir / "test-skill").mkdir()
    (user_dir / "test-skill" / "SKILL.md").write_text("""---
name: test-skill
description: User skill
---

User instructions.
""", encoding="utf-8")

    # Project skill with same name
    (project_dir / "test-skill").mkdir()
    (project_dir / "test-skill" / "SKILL.md").write_text("""---
name: test-skill
description: Project skill
---

Project instructions.
""", encoding="utf-8")

    skills = list_skills([user_dir, project_dir])
    assert len(skills) == 1
    assert skills[0]["description"] == "Project skill"


def test_list_skills_multiple(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    (skills_dir / "skill-a").mkdir()
    (skills_dir / "skill-a" / "SKILL.md").write_text("""---
name: skill-a
description: Skill A
---

Instructions A.
""", encoding="utf-8")

    (skills_dir / "skill-b").mkdir()
    (skills_dir / "skill-b" / "SKILL.md").write_text("""---
name: skill-b
description: Skill B
---

Instructions B.
""", encoding="utf-8")

    skills = list_skills([skills_dir])
    assert len(skills) == 2
    names = {s["name"] for s in skills}
    assert names == {"skill-a", "skill-b"}
