"""Web search tool using Tavily."""
from langchain_core.tools import tool


def format_search_results(results: list[dict]) -> str:
    """格式化搜索结果为 Markdown。"""
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("content", r.get("snippet", ""))
        lines.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}")
    return "\n\n".join(lines)


@tool
async def web_search(query: str) -> str:
    """Search the web for current information on any topic. Returns relevant search results with URLs and content snippets."""
    try:
        from langchain_tavily import TavilySearch

        search_tool = TavilySearch(max_results=5)
        response = await search_tool.ainvoke({"query": query})
        results = response.get("results", [])
        return format_search_results(results)
    except ImportError:
        return "Error: Tavily Search not available. Install langchain-tavily."
    except Exception as e:
        return f"Error: {e}"
