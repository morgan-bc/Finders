"""Tests for finders web_search tool."""
from finders.tools.web_search import format_search_results


def test_format_search_results():
    results = [
        {"title": "Test", "url": "https://example.com", "content": "Test content"}
    ]
    formatted = format_search_results(results)
    assert "**Test**" in formatted
    assert "https://example.com" in formatted


def test_format_search_results_empty():
    formatted = format_search_results([])
    assert formatted == ""
