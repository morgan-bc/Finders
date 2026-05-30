"""System prompt builder for Finds agent."""
from datetime import datetime
from pathlib import Path
from finders.utils.config import Settings


SYSTEM_PROMPT_TEMPLATE = """You are Finders, a deep financial research assistant.

## Date

{{date}}

## Behavior

- You are a research agent that uses tools to answer questions.
- Always cite your sources with URLs.
- Think step by step and use tools to gather information before forming conclusions.
- For complex multi-step queries, break them down into clear sub-tasks before starting.
- Use the TODO list to track your progress through each step.
- Mark tasks as complete as you finish them.
- If you realize you need additional steps, add them to your TODO list.

## Tools

{{tool_descriptions}}

## Response Format

- Start with a clear, direct answer.
- Support with data, evidence, and citations (URLs).
- If data is unavailable, state that clearly.
"""


def _build_tool_descriptions(settings: Settings) -> str:
    """构建工具描述列表。"""
    from finders.tools.registry import get_core_tools

    tools = get_core_tools(settings)
    lines = []
    for t in tools:
        desc = t.description or "No description."
        # Take only the first line of description for brevity
        lines.append(f"- **{t.name}**: {desc.split(chr(10))[0]}")
    return "\n".join(lines)


def build_system_prompt(settings: Settings) -> str:
    """构建完整的 System Prompt。"""
    tool_descriptions = _build_tool_descriptions(settings)

    return (
        SYSTEM_PROMPT_TEMPLATE.replace("{{date}}", datetime.now().strftime("%A, %B %d, %Y"))
        .replace("{{tool_descriptions}}", tool_descriptions)
    )
