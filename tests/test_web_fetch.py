"""Tests for finders web_fetch tool."""
from finders.tools.web_fetch import html_to_markdown, truncate_markdown


def test_html_to_markdown():
    html = "<h1>Title</h1><p>Content</p>"
    md = html_to_markdown(html)
    assert "Title" in md
    assert "Content" in md


def test_truncate_markdown_short():
    text = "Short text"
    assert truncate_markdown(text) == "Short text"


def test_truncate_markdown_long():
    text = "x" * 10000
    result = truncate_markdown(text, max_chars=100)
    assert len(result) <= 150
    assert "[truncated]" in result
