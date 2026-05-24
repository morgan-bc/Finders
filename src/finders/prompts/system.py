"""System prompt builder for Finds agent."""
from datetime import datetime
from pathlib import Path
from finders.utils.config import Settings


def _load_template() -> str:
    """加载模板文件。"""
    template_path = Path(__file__).parent / "templates" / "system.md"
    return template_path.read_text(encoding="utf-8")


def build_system_prompt(settings: Settings) -> str:
    """构建完整的 System Prompt。"""
    template = _load_template()
    tool_descriptions = _build_tool_descriptions(settings)

    return (
        template.replace("{{date}}", datetime.now().strftime("%A, %B %d, %Y"))
        .replace("{{tool_descriptions}}", tool_descriptions)
    )


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
