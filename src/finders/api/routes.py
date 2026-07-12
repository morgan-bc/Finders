"""FastAPI routes."""
from __future__ import annotations

import json
from sse_starlette.sse import EventSourceResponse

from fastapi import APIRouter

from finders.api.models import HealthResponse, QueryRequest
from finders.agents.factory import create_finders_agent
from finders.utils.config import get_settings, Settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/query")
async def query(request: QueryRequest):
    """启动 Agent 查询，返回 SSE 事件流。"""
    settings = _build_settings(request)
    agent = create_finders_agent(settings)

    async def event_stream():
        async for event in agent.astream_events(
            {"messages": [("user", request.query)]},
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_start":
                yield {"event": "thinking", "data": json.dumps({"message": "Thinking..."})}

            elif kind == "on_tool_start":
                yield {
                    "event": "tool_start",
                    "data": json.dumps({
                        "tool": event["name"],
                        "args": event["data"].get("input", {}),
                    }),
                }

            elif kind == "on_tool_end":
                yield {
                    "event": "tool_end",
                    "data": json.dumps({
                        "tool": event["name"],
                        "status": "completed",
                    }),
                }

            elif kind == "on_tool_error":
                yield {
                    "event": "tool_error",
                    "data": json.dumps({
                        "tool": event["name"],
                        "error": str(event["data"].get("error", "Unknown")),
                    }),
                }

            elif kind == "on_chat_model_end":
                output = event["data"].get("output")
                if output and hasattr(output, "content") and output.content:
                    yield {
                        "event": "answer",
                        "data": json.dumps({"answer": output.content}),
                    }

    return EventSourceResponse(event_stream())


def _build_settings(request: QueryRequest) -> Settings:
    """根据请求覆盖默认设置。"""
    settings = get_settings()
    if request.model:
        settings.agent.model = request.model
    if request.fast_model:
        settings.agent.fast_model = request.fast_model
    settings.agent.max_iterations = request.max_iterations
    settings.memory.enabled = request.memory_enabled
    return settings
