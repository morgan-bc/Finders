"""Agent 回调处理器。继承 LangChain AsyncCallbackHandler，将 LLM 事件转发到 UI。"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class FindsCallbackHandler(AsyncCallbackHandler):
    """LangChain 异步回调处理器，将 Agent 事件通过回调函数转发给 UI 层。"""

    def __init__(
        self,
        on_thinking: Callable[[str], Any] | None = None,
        on_tool_start: Callable[[str, dict], Any] | None = None,
        on_tool_end: Callable[[str, str, int], Any] | None = None,
        on_tool_error: Callable[[str, str], Any] | None = None,
        on_answer: Callable[[str, dict | None], Any] | None = None,
    ) -> None:
        self.on_thinking = on_thinking
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_tool_error = on_tool_error
        self.on_answer = on_answer
        self._start_times: dict[str, float] = {}
        self._tool_call_counter = 0

    async def on_chat_model_start(self, serialized: dict[str, Any], messages: list[list[BaseMessage]], **kwargs: Any) -> None:
        """LLM 开始生成（thinking 阶段）。"""
        if self.on_thinking:
            self.on_thinking("Thinking...")

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM 生成结束。"""
        pass

    async def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """工具开始执行。"""
        tool_name = serialized.get("name", "unknown")
        self._start_times[tool_name] = time.time()
        self._tool_call_counter += 1

        if self.on_tool_start:
            try:
                args = json.loads(input_str) if input_str else {}
            except (json.JSONDecodeError, TypeError):
                args = {"input": input_str}
            self.on_tool_start(tool_name, args)

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具执行完成。"""
        tool_name = kwargs.get("name", "unknown")
        duration_ms = int((time.time() - self._start_times.get(tool_name, time.time())) * 1000)

        if self.on_tool_end:
            self.on_tool_end(tool_name, output[:200], duration_ms)

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """工具执行出错。"""
        tool_name = kwargs.get("name", "unknown")
        if self.on_tool_error:
            self.on_tool_error(tool_name, str(error))

    async def on_chat_model_end(self, serialized: dict[str, Any], response: LLMResult, **kwargs: Any) -> None:
        """最终回答完成。"""
        if self.on_answer and response.generations:
            answer = response.generations[0][0].text if response.generations[0] else ""
            token_usage = response.llm_output.get("token_usage") if response.llm_output else None
            self.on_answer(answer, token_usage)
