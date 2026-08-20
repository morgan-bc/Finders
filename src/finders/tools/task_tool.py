"""Task tool for delegating work to subagents."""

import asyncio
import logging
from dataclasses import replace
from typing import Annotated

from langchain.tools import tool, ToolRuntime

from finders.subagents import SubagentExecutor, get_available_subagent_names, get_subagent_config
from finders.subagents.executor import SubagentStatus, cleanup_background_task, get_background_task_result
from finders.utils.config import get_settings

logger = logging.getLogger(__name__)


def _get_core_tools(settings):
    """Lazy import to avoid circular dependency."""
    from finders.tools.registry import get_core_tools
    return get_core_tools(settings)


@tool("task", parse_docstring=True)
async def task_tool(
    description: str,
    prompt: str,
    subagent_type: str,
    runtime: ToolRuntime,
) -> str:
    """Delegate a task to a specialized subagent that runs in its own context.

    Subagents help you:
    - Preserve context by keeping exploration and implementation separate
    - Handle complex multi-step tasks autonomously
    - Execute operations in isolated contexts

    Available subagent types:
    - **general-purpose**: A capable agent for complex, multi-step tasks that require
      both exploration and action. Use when the task requires complex reasoning,
      multiple dependent steps, or would benefit from isolated context.

    When to use this tool:
    - Complex tasks requiring multiple steps or tools
    - Tasks that produce verbose output
    - When you want to isolate context from the main conversation

    When NOT to use this tool:
    - Simple, single-step operations (use tools directly)
    - Tasks requiring user interaction or clarification

    Args:
        description: A short (3-5 word) description of the task. ALWAYS PROVIDE THIS PARAMETER FIRST.
        prompt: The task description for the subagent. Be specific and clear. ALWAYS PROVIDE THIS PARAMETER SECOND.
        subagent_type: The type of subagent to use. ALWAYS PROVIDE THIS PARAMETER THIRD.
    """
    available_subagent_names = get_available_subagent_names()

    config = get_subagent_config(subagent_type)
    if config is None:
        available = ", ".join(available_subagent_names)
        return f"Error: Unknown subagent type '{subagent_type}'. Available: {available}"

    # overrides: dict = {}
    # if overrides:
    #     config = replace(config, **overrides)

    settings = get_settings()
    parent_model = settings.agent.model

    tools = _get_core_tools(settings)

    executor = SubagentExecutor(
        config=config,
        tools=tools,
        parent_model=parent_model,
        skill_metadata=runtime.state.get("skill_metadata", None),
    )

    task_id = executor.execute_async(prompt, task_id=runtime.tool_call_id)

    poll_count = 0
    last_status = None
    max_poll_count = (config.timeout_seconds + 60) // 5

    logger.info(f"[trace={executor.trace_id}] Started background task {task_id} (subagent={subagent_type}, timeout={config.timeout_seconds}s, polling_limit={max_poll_count} polls)")

    try:
        while True:
            result = get_background_task_result(task_id)

            if result is None:
                logger.error(f"[trace={executor.trace_id}] Task {task_id} not found in background tasks")
                return f"Error: Task {task_id} disappeared from background tasks"

            if result.status != last_status:
                logger.info(f"[trace={executor.trace_id}] Task {task_id} status: {result.status.value}")
                last_status = result.status

            if result.status == SubagentStatus.COMPLETED:
                logger.info(f"[trace={executor.trace_id}] Task {task_id} completed after {poll_count} polls")
                cleanup_background_task(task_id)
                return f"Task Succeeded. Result: {result.result}"
            elif result.status == SubagentStatus.FAILED:
                logger.error(f"[trace={executor.trace_id}] Task {task_id} failed: {result.error}")
                cleanup_background_task(task_id)
                return f"Task failed. Error: {result.error}"
            elif result.status == SubagentStatus.TIMED_OUT:
                logger.warning(f"[trace={executor.trace_id}] Task {task_id} timed out: {result.error}")
                cleanup_background_task(task_id)
                return f"Task timed out. Error: {result.error}"

            await asyncio.sleep(5)
            poll_count += 1

            if poll_count > max_poll_count:
                timeout_minutes = config.timeout_seconds // 60
                logger.error(f"[trace={executor.trace_id}] Task {task_id} polling timed out after {poll_count} polls")
                return f"Task polling timed out after {timeout_minutes} minutes. Status: {result.status.value}"
    except asyncio.CancelledError:
        raise
