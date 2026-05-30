"""Tool registry for finders."""
from langchain_core.tools import BaseTool
from finders.utils.config import Settings
from finders.tools.web_search import web_search
from finders.tools.web_fetch import web_fetch
from finders.tools.filesystem import read_file, write_file
from finders.tools.task_tool import task_tool


# 工具元数据：哪些工具可以安全并发
CONCURRENT_TOOLS = {"web_search", "web_fetch", "read_file"}
# 哪些工具需要用户审批
APPROVAL_TOOLS = {"write_file"}


def get_core_tools(settings: Settings) -> list[BaseTool]:
    """获取核心工具列表。"""
    tools = [
        web_search,
        web_fetch,
        read_file,
        write_file,
        task_tool,
    ]

    # Memory 工具（如果启用）
    if settings.memory.enabled:
        from finders.memory.search_tool import memory_search_tool
        tools.append(memory_search_tool)

    # Skill 工具（如果有可用 skills）
    from finders.skills.registry import has_skills
    if has_skills():
        from finders.tools.skill import skill_tool
        tools.append(skill_tool)

    return tools


def is_concurrent_safe(tool_name: str) -> bool:
    """检查工具是否可并发执行。"""
    return tool_name in CONCURRENT_TOOLS


def requires_approval(tool_name: str) -> bool:
    """检查工具是否需要用户审批。"""
    return tool_name in APPROVAL_TOOLS
