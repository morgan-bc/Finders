"""Tests for finders token estimation utilities."""
from unittest.mock import MagicMock
from finders.utils.tokens import estimate_tokens, get_compact_threshold, get_token_count_from_message


def test_estimate_tokens_basic():
    tokens = estimate_tokens("Hello world")
    assert tokens > 0


def test_estimate_tokens_ratio():
    # 1.5 chars/token: "Hello world" = 11 chars → ~7 tokens
    tokens = estimate_tokens("Hello world")
    assert tokens == int(11 / 1.5)


def test_estimate_tokens_empty():
    tokens = estimate_tokens("")
    assert tokens >= 1


def test_estimate_tokens_longer_text():
    text = "The quick brown fox jumps over the lazy dog. " * 10
    tokens = estimate_tokens(text)
    assert tokens > 20


def test_get_token_count_from_message_with_usage():
    msg = MagicMock()
    msg.usage_metadata = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    assert get_token_count_from_message(msg) == 30


def test_get_token_count_from_message_response_metadata():
    msg = MagicMock()
    msg.usage_metadata = None
    msg.response_metadata = {"token_usage": {"total_tokens": 50}}
    msg.content = ""
    assert get_token_count_from_message(msg) == 50


def test_get_token_count_from_message_fallback():
    msg = MagicMock()
    msg.usage_metadata = None
    msg.response_metadata = {}
    msg.content = "Hello world"
    tokens = get_token_count_from_message(msg)
    assert tokens == estimate_tokens("Hello world")


def test_compact_threshold_gpt5():
    threshold = get_compact_threshold("openai:gpt-5")
    assert threshold == 200_000 - 20_000 - 13_000


def test_compact_threshold_default():
    threshold = get_compact_threshold("unknown-model")
    assert threshold == 128_000 - 20_000 - 13_000
