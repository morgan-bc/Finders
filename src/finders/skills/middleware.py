"""Middleware for loading and exposing agent skills to the system prompt.

This middleware implements Anthropic's "Agent Skills" pattern with progressive disclosure:
1. Parse YAML frontmatter from SKILL.md files at session start
2. Inject skills metadata (name + description) into system prompt
3. Agent reads full SKILL.md content when relevant to a task

Skills are loaded from one or more directories (str | list[str]).
When multiple directories are provided, later ones override earlier ones
on name conflicts.

Example structure:
~/.finders/skills/
├── web-research/
│   ├── SKILL.md        # Required: YAML frontmatter + instructions
│   └── helper.py       # Optional: supporting files
├── code-review/
│   ├── SKILL.md
│   └── checklist.md
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage

from finders.skills.load import SkillMetadata, _list_skills

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

    Supports multiple skills directories; later directories override earlier ones
    when skill names conflict.

    Args:
        skills_dir: Path or list of paths to skills directories.
        allowed: Optional list of skill names to allow. If set, only these skills are loaded.
        disallowed: Optional list of skill names to exclude.
    """

    def __init__(
        self,
        *,
        skills_dir: str | list[str],
        allowed: list[str] | None = None,
        disallowed: list[str] | None = None,
    ) -> None:
        """Initialize the skills middleware.

        Args:
            skills_dir: Path or list of paths to skills directories.
            allowed: Optional list of skill names to allow. If set, only these skills are loaded.
            disallowed: Optional list of skill names to exclude.
        """
        if isinstance(skills_dir, str):
            self.skills_dirs = [Path(skills_dir).expanduser()]
        else:
            self.skills_dirs = [Path(d).expanduser() for d in set(skills_dir)]
        self.allowed = set(allowed) if allowed else None
        self.disallowed = set(disallowed) if disallowed else None
        self._skills_metadata: list[SkillMetadata] = []

    def before_agent(self, state: dict[str, Any], runtime) -> dict[str, Any] | None:
        """Load skills metadata before agent execution.

        This runs once at session start to discover available skills from all
        configured skills directories.

        Args:
            state: Current agent state.
            runtime: Runtime context.

        Returns:
            None (skills are stored in instance variable for later use).
        """
        all_skills: dict[str, SkillMetadata] = {}
        for skills_dir in self.skills_dirs:
            skills = _list_skills(skills_dir)
            for skill in skills:
                all_skills[skill["name"]] = skill

        skills_list = list(all_skills.values())

        # Filter skills based on allowed/disallowed lists
        if self.allowed is not None:
            skills_list = [s for s in skills_list if s["name"] in self.allowed]
        if self.disallowed is not None:
            skills_list = [s for s in skills_list if s["name"] not in self.disallowed]

        self._skills_metadata = skills_list
        return {"skill_metadata": skills_list}

        
    def modify_request(self, request):
        """Modify the request to include skills metadata.

        Args:
            request: Model request to modify.
        Returns:
            Modified model request with skills metadata.
        """
        
        skills_list = self._format_skills_list(self._skills_metadata)
        skills_section = SKILLS_SYSTEM_PROMPT.format(skills_list=skills_list)
        system_prompt = request.system_prompt
        if system_prompt is not None:
            system_prompt = system_prompt + "\n\n" + skills_section
            request = request.override(system_prompt=system_prompt)
        return request 


    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        """Inject skills documentation into the system prompt.

        This intercepts every model call to ensure skills info is always available.

        Args:
            request: Model request containing state and messages.
            handler: Callback to execute the model request.

        Returns:
            The model response after injecting skills documentation.
        """
        request = self.modify_request(request)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        """Async version of wrap_model_call."""
        request = self.modify_request(request)
        return await handler(request)


    def _format_skills_list(self, skills: list[SkillMetadata]) -> str:
        """Format skills metadata for display in system prompt."""
        if not skills:
            return "<available_skills></available_skills>"

        lines = ["<available_skills>"]
        for skill in skills:
            location = skill["path"]
            lines.append(
                f"<skill>\n"
                f"<name>{skill['name']}</name>\n"
                f"<description>{skill['description']}</description>\n"
                f"<location>{location}</location>\n"
                f"</skill>"
            )
        lines.append("</available_skills>")

        return "\n".join(lines)
