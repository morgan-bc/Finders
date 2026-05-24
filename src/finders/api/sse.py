"""SSE stream for agent events."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from finders.agent.runner import AgentEvent


async def agent_event_stream(runner: AgentEvent) -> AsyncIterator[dict]:
    """将 AgentEvent 流转换为 SSE 格式。"""
    async for event in runner:
        yield {
            "event": event.type,
            "data": json.dumps({
                "type": event.type,
                **{k: v for k, v in event.data.items()},
            }),
        }
