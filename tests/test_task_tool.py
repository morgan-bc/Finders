# tests/test_task_tool.py
import pytest
from finders.tools.task_tool import task_tool

def test_task_tool_has_correct_name():
    assert task_tool.name == "task"

def test_task_tool_with_invalid_subagent_type():
    """Test that task_tool returns error for unknown subagent type."""
    import asyncio
    
    async def run_test():
        result = await task_tool.ainvoke({
            "args": {
                "description": "Test task",
                "prompt": "Do something",
                "subagent_type": "nonexistent-type",
            },
            "id": "test-call-id",
            "name": "task",
            "type": "tool_call",
            "tool_call_id": "test-call-id",
        })
        return result
    
    result = asyncio.run(run_test())
    assert "Error" in result.content
    assert "nonexistent-type" in result.content
    assert "general-purpose" in result.content
