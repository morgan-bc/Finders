"""Agent runner: bridges the agent factory with API/CLI layers."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from finders.agents.factory import create_finders_agent
from finders.utils.callbacks import FindsCallbackHandler
from finders.utils.config import Settings


@dataclass
class AgentEvent:
    """Agent 事件（用于 SSE/CLI 流式输出）。"""
    type: str
    data: dict = field(default_factory=dict)


class AgentRunner:
    """Agent 运行器，封装 agent 调用和事件流。"""

    def __init__(self, settings: Settings, query: str) -> None:
        self.settings = settings
        self.query = query
        self._agent = create_finders_agent(settings)
        self._events: asyncio.Queue[AgentEvent] | None = None
        self._done = False
        self._answer: str = ""

    async def run(self) -> str:
        """同步运行 agent 并返回最终答案。"""
        result = await self._agent.ainvoke({
            "messages": [{"role": "user", "content": self.query}],
        })
        messages = result.get("messages", [])
        # 最后一条 AI 消息即为答案
        for msg in reversed(messages):
            if hasattr(msg, "content") and getattr(msg, "type", None) != "tool":
                self._answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                break
        return self._answer

    async def run_stream(self) -> AsyncIterator[AgentEvent]:
        """流式运行 agent，产出 AgentEvent。"""
        self._events = asyncio.Queue()
        self._done = False
        self._answer = ""

        handler = FindsCallbackHandler(
            on_thinking=lambda msg: self._enqueue("thinking", {"message": msg}),
            on_tool_start=lambda name, args: self._enqueue("tool_start", {"tool": name, "args": args}),
            on_tool_end=lambda name, preview, duration: self._enqueue("tool_end", {
                "tool": name,
                "result_preview": preview,
                "duration_ms": duration,
            }),
            on_tool_error=lambda name, error: self._enqueue("tool_error", {
                "tool": name,
                "error": error,
            }),
            on_answer=lambda answer, usage: self._enqueue("answer", {
                "answer": answer,
                "token_usage": usage,
            }),
        )

        config = {"callbacks": [handler]}

        # 启动 agent 调用
        invoke_task = asyncio.create_task(
            self._agent.ainvoke(
                {"messages": [{"role": "user", "content": self.query}]},
                config=config,
            )
        )

        # 从队列中产出事件，直到 agent 完成
        while not self._done:
            try:
                event = await asyncio.wait_for(self._events.get(), timeout=0.5)
                if event.type == "answer":
                    self._answer = event.data.get("answer", "")
                    self._done = True
                yield event
            except asyncio.TimeoutError:
                if invoke_task.done():
                    # agent 完成但未触发 answer 回调
                    try:
                        result = invoke_task.result()
                        messages = result.get("messages", [])
                        for msg in reversed(messages):
                            if hasattr(msg, "content") and getattr(msg, "type", None) != "tool":
                                answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                                self._answer = answer
                                yield AgentEvent("answer", {"answer": answer})
                                break
                    except Exception:
                        pass
                    self._done = True

        await invoke_task

    def _enqueue(self, event_type: str, data: dict) -> None:
        if self._events:
            self._events.put_nowait(AgentEvent(event_type, data))

    @property
    def answer(self) -> str:
        return self._answer
