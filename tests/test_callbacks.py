"""Tests for finders callback handler."""
from finders.utils.callbacks import FindsCallbackHandler


def test_callback_handler_init():
    handler = FindsCallbackHandler()
    assert handler.on_thinking is None
    assert handler.on_tool_start is None


def test_callback_handler_with_callbacks():
    thinking_calls = []
    handler = FindsCallbackHandler(on_thinking=lambda msg: thinking_calls.append(msg))
    assert handler.on_thinking is not None


def test_callback_handler_all_hooks():
    hooks = {
        "on_thinking": [],
        "on_tool_start": [],
        "on_tool_end": [],
        "on_tool_error": [],
        "on_answer": [],
    }
    handler = FindsCallbackHandler(
        on_thinking=lambda m: hooks["on_thinking"].append(m),
        on_tool_start=lambda t, a: hooks["on_tool_start"].append((t, a)),
        on_tool_end=lambda t, r, d: hooks["on_tool_end"].append((t, r, d)),
        on_tool_error=lambda t, e: hooks["on_tool_error"].append((t, e)),
        on_answer=lambda a, u: hooks["on_answer"].append((a, u)),
    )
    assert all(h is not None for h in [handler.on_thinking, handler.on_tool_start, handler.on_tool_end])
