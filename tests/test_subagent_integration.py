# tests/test_subagent_integration.py
"""Integration tests for subagent functionality."""
import pytest
from unittest.mock import patch, MagicMock
from finders.utils.config import Settings
from finders.subagents import SubagentConfig, SubagentExecutor, SubagentStatus
from finders.subagents.executor import (
    get_background_task_result,
    cleanup_background_task,
)
from finders.tools.registry import get_core_tools


def test_subagent_executor_initialization():
    """Test that SubagentExecutor can be initialized with config and tools."""
    settings = Settings()
    settings.memory.enabled = False
    
    tools = get_core_tools(settings)
    
    config = SubagentConfig(
        name="test",
        description="Test subagent",
        system_prompt="You are a test agent.",
        max_turns=5,
        timeout_seconds=60,
    )
    
    executor = SubagentExecutor(
        config=config,
        tools=tools,
        parent_model=settings.agent.model,
    )
    
    assert executor.config.name == "test"
    assert len(executor.tools) > 0
    # task tool should be filtered out if in disallowed_tools
    task_tools = [t for t in executor.tools if t.name == "task"]
    assert len(task_tools) == 0


def test_background_task_lifecycle():
    """Test background task result storage and cleanup."""
    from finders.subagents.executor import SubagentResult, _background_tasks_lock
    
    task_id = "test-task-lifecycle"
    result = SubagentResult(
        task_id=task_id,
        trace_id="test-trace",
        status=SubagentStatus.COMPLETED,
        result="Test result",
    )
    
    with _background_tasks_lock:
        from finders.subagents.executor import _background_tasks
        _background_tasks[task_id] = result
    
    # Should be able to retrieve result
    retrieved = get_background_task_result(task_id)
    assert retrieved is not None
    assert retrieved.status == SubagentStatus.COMPLETED
    assert retrieved.result == "Test result"
    
    # Cleanup should succeed
    cleanup_background_task(task_id)
    assert get_background_task_result(task_id) is None


def test_task_tool_filters_invalid_subagent_type():
    """Test that task_tool returns error for invalid subagent type."""
    import asyncio
    from finders.tools.task_tool import task_tool
    
    async def run_test():
        result = await task_tool.ainvoke({
            "args": {
                "description": "Test task",
                "prompt": "Do something",
                "subagent_type": "invalid-type",
            },
            "id": "test-call-id",
            "name": "task",
            "type": "tool_call",
            "tool_call_id": "test-call-id",
        })
        return result
    
    result = asyncio.run(run_test())
    assert "Error" in result.content
    assert "invalid-type" in result.content
    assert "general-purpose" in result.content
