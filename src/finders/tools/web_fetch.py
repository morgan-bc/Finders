"""Web fetch tool using jinaai + markdownify fallback."""
import os
import re
import httpx
from langchain_core.tools import tool
from markdownify import markdownify


JINA_WEB_FETCH_BASE = os.environ.get("JINA_WEB_FETCH_BASE", "https://r.jina.ai")


def parse_jina_response(text: str) -> tuple[str, str]:
    """解析 Jina Reader 返回的文本，提取 title 和 markdown content。

    Jina 返回格式：
    Title: xxx
    URL Source: xxx
    Markdown Content:
    ...
    """
    title = ""
    markdown_content = ""

    # 提取 Title
    title_match = re.search(r"^Title:\s*(.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # 提取 Markdown Content（从 "Markdown Content:" 之后到结尾）
    content_match = re.search(r"Markdown Content:\s*\n(.*)", text, re.DOTALL)
    if content_match:
        markdown_content = content_match.group(1).strip()

    return title, markdown_content


def clean_markdown_links(md: str) -> str:
    """清理 Markdown 链接：删除 [文本](URL) 中的链接，只保留文本和图片链接。

    - [文本](http://...) -> 文本
    - ![图片](http://...) -> ![图片](http://...)  (保留)
    """
    # 匹配图片链接（保留）
    # 匹配普通链接并替换为纯文本
    def replace_link(match):
        # 如果是图片链接，保留原样
        if match.group(0).startswith("!"):
            return match.group(0)
        # 否则只保留链接文本
        return match.group(1)

    # 匹配 [文本](URL) 格式，但不匹配 ![图片](URL)
    # 使用负向前瞻确保不匹配图片
    pattern = r"(?<!\!)\[([^\]]*)\]\([^)]+\)"
    return re.sub(pattern, replace_link, md)


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown。"""
    return markdownify(html, heading_style="ATX", strip=["script", "style"])


def truncate_markdown(md: str, max_chars: int = 8000) -> str:
    """截断 Markdown 到指定长度。"""
    if len(md) <= max_chars:
        return md
    return md[:max_chars].rsplit("\n", 1)[0] + "\n\n... [truncated]"


async def fetch_with_jina(url: str, client: httpx.AsyncClient) -> str:
    """使用 Jina Reader 获取网页内容。"""
    jina_url = f"{JINA_WEB_FETCH_BASE}/{url}"
    response = await client.get(jina_url)
    response.raise_for_status()

    title, markdown_content = parse_jina_response(response.text)

    # 清理链接
    markdown_content = clean_markdown_links(markdown_content)

    # 如果有标题，添加到开头
    if title:
        return f"# {title}\n\n{markdown_content}"
    return markdown_content


@tool
async def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL as markdown. Use when you need full article text beyond headlines."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 首先尝试使用 Jina Reader
            try:
                md = await fetch_with_jina(url, client)
                return truncate_markdown(md)
            except Exception:
                # Jina 失败，回退到 markdownify
                response = await client.get(url)
                response.raise_for_status()
                md = html_to_markdown(response.text)
                return truncate_markdown(md)
    except httpx.HTTPStatusError as e:
        return f"Error fetching URL: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error fetching URL: {e}"
