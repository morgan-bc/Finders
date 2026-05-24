"""Memory search tool for finders."""
from langchain_core.tools import tool


@tool
async def memory_search(query: str) -> str:
    """Search past conversations and memories. Returns relevant memory snippets."""
    try:
        from finders.memory.manager import MemoryManager
        from finders.utils.paths import get_finders_dir

        manager = MemoryManager(base_dir=get_finders_dir())
        try:
            results = manager.search(query)
            if not results:
                return "No relevant memories found."

            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. [{r.path}] (score: {r.score:.2f})\n   {r.snippet}")

            return "\n\n".join(lines)
        finally:
            manager.close()
    except Exception as e:
        return f"Error searching memory: {e}"


memory_search_tool = memory_search
