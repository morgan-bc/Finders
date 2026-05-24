"""Token estimation utilities.

优先使用 AIMessage.usage_metadata，无数据时按 1.5 字符 = 1 token 估算。
"""

CHARS_PER_TOKEN = 1.5


def estimate_tokens(text: str) -> int:
    """使用 1.5 字符/token 估算文本的 token 数。"""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def get_token_count_from_message(message) -> int:
    """从消息中获取 token 数。

    优先级：
    1. AIMessage.usage_metadata（OpenAI 兼容模型原生返回）
    2. response_metadata.token_usage
    3. 字符估算回退（1.5 字符/token）
    """
    # Check usage_metadata first (LangChain standard)
    usage = getattr(message, "usage_metadata", None)
    if usage:
        return usage.get("total_tokens", 0)

    # Check response_metadata fallback
    response_meta = getattr(message, "response_metadata", {})
    token_usage = response_meta.get("token_usage") if isinstance(response_meta, dict) else None
    if token_usage:
        return token_usage.get("total_tokens", 0)

    # Final fallback: character estimation
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return estimate_tokens(content)
    return 0


def get_effective_context_window(model: str) -> int:
    """获取模型有效上下文窗口（扣除输出预留）。"""
    windows = {
        "gpt-5": 200_000,
        "gpt-4": 128_000,
        "gemini": 1_000_000,
    }

    base_window = 128_000  # default
    for key, window in windows.items():
        if key in model.lower():
            base_window = window
            break

    # Reserve 20K for output
    return base_window - 20_000


def get_compact_threshold(model: str) -> int:
    """获取自动压缩阈值（有效窗口 - 13K 缓冲）。"""
    effective = get_effective_context_window(model)
    return effective - 13_000
