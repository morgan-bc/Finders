"""FastAPI routes."""
from __future__ import annotations

from sse_starlette.sse import EventSourceResponse

from fastapi import APIRouter

from finders.api.models import HealthResponse, QueryRequest
from finders.api.sse import agent_event_stream
from finders.agent.runner import AgentRunner
from finders.utils.config import get_settings, Settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/query")
async def query(request: QueryRequest):
    """启动 Agent 查询，返回 SSE 事件流。"""
    settings = _build_settings(request)
    runner = AgentRunner(settings, request.query)
    return EventSourceResponse(agent_event_stream(runner.run_stream()))


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
