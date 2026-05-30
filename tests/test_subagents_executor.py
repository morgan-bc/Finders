# tests/test_subagents_executor.py
import pytest
from finders.subagents.executor import (
    SubagentResult,
    SubagentStatus,
    get_background_task_result,
    cleanup_background_task,
)

def test_subagent_result_defaults():
    result = SubagentResult(
        task_id="test-123",
        trace_id="trace-1",
        status=SubagentStatus.PENDING,
    )
    assert result.task_id == "test-123"
    assert result.ai_messages == []
    assert result.result is None
    assert result.error is None

def test_subagent_status_values():
    assert SubagentStatus.PENDING.value == "pending"
    assert SubagentStatus.RUNNING.value == "running"
    assert SubagentStatus.COMPLETED.value == "completed"
    assert SubagentStatus.FAILED.value == "failed"
    assert SubagentStatus.TIMED_OUT.value == "timed_out"

def test_background_task_result_returns_none_for_unknown():
    result = get_background_task_result("nonexistent-task")
    assert result is None
