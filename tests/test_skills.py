"""Tests for finders skills system."""
from pathlib import Path
import tempfile
from finders.skills.loader import load_skill
from finders.skills.registry import discover_skills, get_skill, has_skills, reset_cache


def test_load_skill(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: A test skill
---

# Test Skill Instructions
Do something useful.
""", encoding="utf-8")

    result = load_skill(skill_file)
    assert result is not None
    assert result.name == "test-skill"
    assert "Do something useful" in result.instructions


def test_load_skill_invalid(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("No yaml frontmatter", encoding="utf-8")
    assert load_skill(skill_file) is None


def test_load_skill_missing_fields(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\nInstructions", encoding="utf-8")
    assert load_skill(skill_file) is None  # missing description


def test_discover_skills_empty():
    reset_cache()
    skills = discover_skills()
    assert isinstance(skills, list)


def test_get_skill_not_found():
    reset_cache()
    assert get_skill("nonexistent_skill_xyz") is None


def test_has_skills():
    reset_cache()
    result = has_skills()
    assert isinstance(result, bool)
