"""Agent factory for creating Finders agent with middleware pipeline."""
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ContextEditingMiddleware,
    ToolCallLimitMiddleware,
    TodoListMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
    ModelFallbackMiddleware,
)
from finders.utils.config import Settings
from finders.tools.registry import get_core_tools
from finders.agents.prompt import build_system_prompt
from finders.utils.paths import get_finders_dir
from finders.skills.middleware import SkillsMiddleware


def _build_middleware(settings: Settings):
    """Build middleware pipeline for agent."""
    model = settings.create_chat_model()
    fast_model = settings.create_chat_model(fast=True)

    return [
        SkillsMiddleware(
            skills_dir=Path.home() / ".finders" / "skills",
            project_skills_dir=Path.cwd() / ".finders" / "skills",
        ),
        TodoListMiddleware(),
        SummarizationMiddleware(
            model=fast_model,
            trigger=("tokens", settings.agent.compact_threshold),
        ),
        ContextEditingMiddleware(),
        ToolCallLimitMiddleware(
            run_limit=settings.tools.max_calls_per_tool,
        ),
        ToolRetryMiddleware(
            max_retries=2,
        ),
        ModelRetryMiddleware(
            max_retries=3,
        ),
        HumanInTheLoopMiddleware(
            interrupt_on={"write_file": True, "edit_file": True},
        ),
    ]


def create_finders_agent(settings: Settings):
    """创建 Finders Agent 实例。"""

    model = settings.create_chat_model()
    system_prompt = build_system_prompt(settings)
    tools = get_core_tools(settings)

    middleware = _build_middleware(settings)

    # Memory flush + recall（如果启用记忆系统）
    if settings.memory.enabled:
        from finders.middlewares.memory import MemoryMiddleware
        middleware.append(
            MemoryMiddleware(
                memory_dir=str(get_finders_dir()),
                flush_threshold=settings.agent.compact_threshold,
            )
        )

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
