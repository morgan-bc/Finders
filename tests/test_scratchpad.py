"""Tests for finders agent scratchpad."""
import pytest
from finders.agents.scratchpad import Scratchpad


def test_scratchpad_initial():
    scratchpad = Scratchpad("test query")
    assert scratchpad.get_call_count("web_search") == 0
    assert scratchpad.should_warn("web_search") is False


def test_scratchpad_record_and_count():
    scratchpad = Scratchpad("test query", max_calls_per_tool=3)
    scratchpad.record_tool("web_search", {"query": "test"}, "result")
    scratchpad.record_tool("web_search", {"query": "test2"}, "result2")

    assert scratchpad.get_call_count("web_search") == 2
    assert scratchpad.should_warn("web_search") is True


def test_scratchpad_over_limit():
    scratchpad = Scratchpad("test query", max_calls_per_tool=3)
    for i in range(3):
        scratchpad.record_tool("web_search", {"query": f"test{i}"}, "result")

    assert scratchpad.is_over_limit("web_search") is True


def test_scratchpad_get_records():
    scratchpad = Scratchpad("test query")
    scratchpad.record_tool("web_search", {"query": "test"}, "result")
    records = scratchpad.get_records()
    assert len(records) == 1
    assert records[0].tool == "web_search"
