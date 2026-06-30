"""Middleware for loading and exposing agent skills to the system prompt.

This middleware implements Anthropic's "Agent Skills" pattern with progressive disclosure:
1. Parse YAML frontmatter from SKILL.md files at session start
2. Inject skills metadata (name + description) into system prompt
3. Agent reads full SKILL.md content when relevant to a task

Skills directory structure (per-agent + project):
User-level: ~/.finders/skills/
Project-level: {PROJECT_ROOT}/.finders/skills/

Example structure:
~/.finders/skills/
├── web-research/
│   ├── SKILL.md        # Required: YAML frontmatter + instructions
│   └── helper.py       # Optional: supporting files
├── code-review/
│   ├── SKILL.md
│   └── checklist.md

.finders/skills/
├── project-specific/
│   └── SKILL.md        # Project-specific skills
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage

from finders.skills.load import SkillMetadata, list_skills

SKILLS_SYSTEM_PROMPT = """
<skills_system>
You have access to a skills library that provides specialized capabilities and domain knowledge.

{skills_list}

**How to Use Skills (Progressive Disclosure):**

Skills follow a **progressive disclosure** pattern - you know they exist (name + description above), but you only read the full instructions when needed:

1. **Recognize when a skill applies**: Check if the user's task matches any skill's description
2. **Read the skill's full instructions**: Use the `read_file` tool to read the SKILL.md file at the path shown above
3. **Follow the skill's instructions**: SKILL.md contains step-by-step workflows, best practices, and examples
4. **Access supporting files**: Skills may include Python scripts, configs, or reference docs - use absolute paths

**When to Use Skills:**
- When the user's request matches a skill's domain (e.g., "research X" → web-research skill)
- When you need specialized knowledge or structured workflows
- When a skill provides proven patterns for complex tasks

**Skills are Self-Documenting:**
- Each SKILL.md tells you exactly what the skill does and how to use it
- The skill list above shows the full path for each skill's SKILL.md file

Remember: Skills are tools to make you more capable and consistent. When in doubt, check if a skill exists for the task!
</skills_system>
"""


class SkillsMiddleware(AgentMiddleware):
    """Middleware for loading and exposing agent skills.

    This middleware implements Anthropic's agent skills pattern:
    - Loads skills metadata (name, description) from YAML frontmatter at session start
    - Injects skills list into system prompt for discoverability
    - Agent reads full SKILL.md content when a skill is relevant (progressive disclosure)

    Supports both user-level and project-level skills:
    - User skills: ~/.finders/skills/
    - Project skills: {PROJECT_ROOT}/.finders/skills/
    - Project skills override user skills with the same name

    Args:
        skills_dir: Path to the user-level skills directory.
        project_skills_dir: Optional path to project-level skills directory.
        allowed: Optional list of skill names to allow. If set, only these skills are loaded.
        disallowed: Optional list of skill names to exclude.
    """

    def __init__(
        self,
        *,
        skills_dir: str | Path,
        project_skills_dir: str | Path | None = None,
        allowed: list[str] | None = None,
        disallowed: list[str] | None = None,
    ) -> None:
        """Initialize the skills middleware.

        Args:
            skills_dir: Path to the user-level skills directory.
            project_skills_dir: Optional path to the project-level skills directory.
            allowed: Optional list of skill names to allow. If set, only these skills are loaded.
            disallowed: Optional list of skill names to exclude.
        """
        self.skills_dir = Path(skills_dir).expanduser()
        self.project_skills_dir = (
            Path(project_skills_dir).expanduser() if project_skills_dir else None
        )
        self.allowed = set(allowed) if allowed else None
        self.disallowed = set(disallowed) if disallowed else None

    def before_agent(self, state: dict[str, Any], runtime) -> dict[str, Any] | None:
        """Load skills metadata before agent execution.

        This runs once at session start to discover available skills from both
        user-level and project-level directories.

        Args:
            state: Current agent state.
            runtime: Runtime context.

        Returns:
            Updated state with skills_metadata populated.
        """
        skills = list_skills(
            user_skills_dir=self.skills_dir,
            project_skills_dir=self.project_skills_dir,
        )

        # Filter skills based on allowed/disallowed lists
        if self.allowed is not None:
            skills = [s for s in skills if s["name"] in self.allowed]
        if self.disallowed is not None:
            skills = [s for s in skills if s["name"] not in self.disallowed]

        return {"skills_metadata": skills}

    def before_model(self, state: dict[str, Any], runtime) -> dict[str, Any] | None:
        """Inject skills documentation into the system prompt.

        This runs on every model call to ensure skills info is always available.

        Args:
            state: Current agent state.
            runtime: Runtime context.

        Returns:
            Updated state with modified system message, or None.
        """
        skills_metadata = state.get("skills_metadata", [])

        skills_list = self._format_skills_list(skills_metadata)

        skills_section = SKILLS_SYSTEM_PROMPT.format(skills_list=skills_list)

        messages = list(state.get("messages", []))
        if messages and isinstance(messages[0], SystemMessage):
            original_content = messages[0].content
            if isinstance(original_content, str) and "## Skills System" not in original_content:
                skills_suffix = f"\n\n{skills_section}"
                messages[0] = SystemMessage(content=original_content + skills_suffix)
                return {"messages": messages}

        return None

    def _to_virtual_path(self, path: str) -> str:
        """Convert a local skill path to a virtual container path.

        Project skills map to /project/... and user skills map to /skills/...
        so that all paths surfaced in prompts are virtual paths.
        """
        p = str(Path(path).expanduser().resolve())
        if self.project_skills_dir is not None:
            proj = str(self.project_skills_dir.expanduser().resolve())
            if p == proj or p.startswith(proj + os.sep):
                rel = p[len(proj):].lstrip(os.sep).replace(os.sep, "/")
                return f"/project/{rel}" if rel else "/project"
        if self.skills_dir is not None:
            usr = str(self.skills_dir.expanduser().resolve())
            if p == usr or p.startswith(usr + os.sep):
                rel = p[len(usr):].lstrip(os.sep).replace(os.sep, "/")
                return f"/skills/{rel}" if rel else "/skills"
        return path

    def _format_skills_list(self, skills: list[SkillMetadata]) -> str:
        """Format skills metadata for display in system prompt."""
        if not skills:
            return "<available_skills></available_skills>"

        lines = ["<available_skills>"]
        for skill in skills:
            location = self._to_virtual_path(skill["path"])
            lines.append(
                f"  <skill name={skill['name']}>\n"
                f"    <description>{skill['description']}</description>\n"
                f"    <location>{location}</location>\n"
                f"  </skill>"
            )
        lines.append("</available_skills>")

        return "\n".join(lines)
