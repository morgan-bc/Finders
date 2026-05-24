"""Web fetch tool using httpx + markdownify."""
import httpx
from langchain_core.tools import tool
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown。"""
    return markdownify(html, heading_style="ATX", strip=["script", "style"])


def truncate_markdown(md: str, max_chars: int = 8000) -> str:
    """截断 Markdown 到指定长度。"""
    if len(md) <= max_chars:
        return md
    return md[:max_chars].rsplit("\n", 1)[0] + "\n\n... [truncated]"


@tool
async def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL as markdown. Use when you need full article text beyond headlines."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            md = html_to_markdown(response.text)
            return truncate_markdown(md)
    except httpx.HTTPStatusError as e:
        return f"Error fetching URL: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error fetching URL: {e}"
