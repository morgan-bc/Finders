"""Skill loader for parsing and loading agent skills from SKILL.md files.

This module implements Anthropic's agent skills pattern with YAML frontmatter parsing.
Each skill is a directory containing a SKILL.md file with:
- YAML frontmatter (name, description required)
- Markdown instructions for the agent
- Optional supporting files (scripts, configs, etc.)

Example SKILL.md structure:
```markdown
---
name: web-research
description: Structured approach to conducting thorough web research
---

# Web Research Skill

## When to Use
- User asks you to research a topic
...
```
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

from typing_extensions import NotRequired

import yaml

from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum size for SKILL.md files (10MB)
MAX_SKILL_FILE_SIZE = 10 * 1024 * 1024

# Agent Skills spec constraints (https://agentskills.io/specification)
MAX_SKILL_NAME_LENGTH = 64
MAX_SKILL_DESCRIPTION_LENGTH = 1024


class SkillMetadata(TypedDict):
    """Metadata for a skill per Agent Skills spec (https://agentskills.io/specification)."""

    name: str
    """Name of the skill (max 64 chars, lowercase alphanumeric and hyphens)."""

    description: str
    """Description of what the skill does (max 1024 chars)."""

    path: str
    """Path to the SKILL.md file."""

    # Optional fields per Agent Skills spec
    compatibility: NotRequired[str | None]
    """Environment requirements (max 500 chars)."""

    metadata: NotRequired[dict[str, str] | None]
    """Arbitrary key-value mapping for additional metadata."""

    allowed_tools: NotRequired[str | None]
    """Space-delimited list of pre-approved tools."""


def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if a path is safely contained within base_dir.

    This prevents directory traversal attacks via symlinks or path manipulation.
    The function resolves both paths to their canonical form (following symlinks)
    and verifies that the target path is within the base directory.

    Args:
        path: The path to validate
        base_dir: The base directory that should contain the path

    Returns:
        True if the path is safely within base_dir, False otherwise
    """
    try:
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        resolved_path.relative_to(resolved_base)
        return True
    except ValueError:
        return False
    except (OSError, RuntimeError):
        return False


def _validate_skill_name(name: str, directory_name: str) -> tuple[bool, str]:
    """Validate skill name per Agent Skills spec.

    Requirements:
    - Max 64 characters
    - Lowercase alphanumeric and hyphens only (a-z, 0-9, -)
    - Cannot start or end with hyphen
    - No consecutive hyphens
    - Must match parent directory name

    Args:
        name: The skill name from YAML frontmatter.
        directory_name: The parent directory name.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not name:
        return False, "name is required"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, "name exceeds 64 characters"
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        return False, "name must be lowercase alphanumeric with single hyphens only"
    if name != directory_name:
        return False, f"name '{name}' must match directory name '{directory_name}'"
    return True, ""


def _parse_skill_metadata(skill_md_path: Path) -> SkillMetadata | None:
    """Parse YAML frontmatter from a SKILL.md file per Agent Skills spec.

    Args:
        skill_md_path: Path to the SKILL.md file.

    Returns:
        SkillMetadata with all fields, or None if parsing fails.
    """
    try:
        file_size = skill_md_path.stat().st_size
        if file_size > MAX_SKILL_FILE_SIZE:
            logger.warning("Skipping %s: file too large (%d bytes)", skill_md_path, file_size)
            return None

        content = skill_md_path.read_text(encoding="utf-8")

        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            logger.warning("Skipping %s: no valid YAML frontmatter found", skill_md_path)
            return None

        frontmatter_str = match.group(1)

        try:
            frontmatter_data = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            logger.warning("Invalid YAML in %s: %s", skill_md_path, e)
            return None

        if not isinstance(frontmatter_data, dict):
            logger.warning("Skipping %s: frontmatter is not a mapping", skill_md_path)
            return None

        name = frontmatter_data.get("name")
        description = frontmatter_data.get("description")

        if not name or not description:
            logger.warning("Skipping %s: missing required 'name' or 'description'", skill_md_path)
            return None

        directory_name = skill_md_path.parent.name
        is_valid, error = _validate_skill_name(str(name), directory_name)
        if not is_valid:
            logger.warning(
                "Skill '%s' in %s does not follow Agent Skills spec: %s. "
                "Consider renaming to be spec-compliant.",
                name,
                skill_md_path,
                error,
            )

        description_str = str(description)
        if len(description_str) > MAX_SKILL_DESCRIPTION_LENGTH:
            logger.warning(
                "Description exceeds %d chars in %s, truncating",
                MAX_SKILL_DESCRIPTION_LENGTH,
                skill_md_path,
            )
            description_str = description_str[:MAX_SKILL_DESCRIPTION_LENGTH]

        return SkillMetadata(
            name=str(name),
            description=description_str,
            path=str(skill_md_path),
            compatibility=frontmatter_data.get("compatibility"),
            metadata=frontmatter_data.get("metadata"),
            allowed_tools=frontmatter_data.get("allowed-tools"),
        )

    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Error reading %s: %s", skill_md_path, e)
        return None


def _list_skills(skills_dir: Path) -> list[SkillMetadata]:
    """List all skills from a single skills directory (internal helper).

    Scans the skills directory for subdirectories containing SKILL.md files,
    parses YAML frontmatter, and returns skill metadata.

    Args:
        skills_dir: Path to the skills directory.

    Returns:
        List of skill metadata dictionaries with name, description, and path.
    """
    skills_dir = skills_dir.expanduser()
    if not skills_dir.exists():
        return []

    try:
        resolved_base = skills_dir.resolve()
    except (OSError, RuntimeError):
        return []

    skills: list[SkillMetadata] = []

    for skill_dir in skills_dir.iterdir():
        if not _is_safe_path(skill_dir, resolved_base):
            continue

        if not skill_dir.is_dir():
            continue

        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            continue

        if not _is_safe_path(skill_md_path, resolved_base):
            continue

        metadata = _parse_skill_metadata(skill_md_path)
        if metadata:
            skills.append(metadata)

    return skills


def list_skills(skills_dirs: list[Path] | None = None) -> list[SkillMetadata]:
    """List skills from multiple directories.

    Later directories override earlier ones when skill names conflict.

    Args:
        skills_dirs: List of paths to skills directories.

    Returns:
        Merged list of skill metadata, with later directories taking precedence.
    """
    if not skills_dirs:
        return []

    all_skills: dict[str, SkillMetadata] = {}

    for skills_dir in skills_dirs:
        dir_skills = _list_skills(skills_dir)
        for skill in dir_skills:
            all_skills[skill["name"]] = skill

    return list(all_skills.values())
