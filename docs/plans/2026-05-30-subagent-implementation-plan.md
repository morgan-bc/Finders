# Subagent Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add subagent functionality to Finders, allowing the main agent to delegate complex tasks to specialized subagents running in isolated contexts.

**Architecture:** Simplified adaptation of deer-flow's subagent system with 5 core modules (config, registry, executor, builtins, task_tool), using ThreadPoolExecutor for background task management and polling for result retrieval.

**Tech Stack:** Python 3.12, LangChain, LangGraph, ThreadPoolExecutor, dataclasses, pytest

---

### Task 1: SubagentConfig Dataclass

**Files:**
- Create: `src/finders/subagents/config.py`
- Test: `tests/test_subagents_config.py`

**Step 1: Write the failing test**

```python
# tests/test_subagents_config.py
from finders.subagents.config import SubagentConfig

def test_subagent_config_defaults():
    config = SubagentConfig(
        name="test",
        description="Test subagent",
        system_prompt="You are a test agent.",
    )
    assert config.name == "test"
    assert config.tools is None
    assert config.disallowed_tools == ["task"]
    assert config.model == "inherit"
    assert config.max_turns == 50
    assert config.timeout_seconds == 900
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subagents_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'finders.subagents'"

**Step 3: Write minimal implementation**

```python
# src/finders/subagents/config.py
"""Subagent configuration definitions."""

from dataclasses import dataclass, field


@dataclass
class SubagentConfig:
    """Configuration for a subagent.

    Attributes:
        name: Unique identifier for the subagent.
        description: When Claude should delegate to this subagent.
        system_prompt: The system prompt that guides the subagent's behavior.
        tools: Optional list of tool names to allow. If None, inherits all tools.
        disallowed_tools: Optional list of tool names to deny.
        model: Model to use - 'inherit' uses parent's model.
        max_turns: Maximum number of agent turns before stopping.
        timeout_seconds: Maximum execution time in seconds (default: 900 = 15 minutes).
    """

    name: str
    description: str
    system_prompt: str
    tools: list[str] | None = None
    disallowed_tools: list[str] = field(default_factory=lambda: ["task"])
    model: str = "inherit"
    max_turns: int = 50
    timeout_seconds: int = 900
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_subagents_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/finders/subagents/config.py tests/test_subagents_config.py
git commit -m "feat: add SubagentConfig dataclass"
```

---

### Task 2: Subagent Registry

**Files:**
- Create: `src/finders/subagents/registry.py`
- Create: `src/finders/subagents/__init__.py`
- Test: `tests/test_subagents_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_subagents_registry.py
from finders.subagents.registry import get_subagent_config, get_available_subagent_names

def test_get_available_subagent_names():
    names = get_available_subagent_names()
    assert isinstance(names, list)
    assert "general-purpose" in names

def test_get_subagent_config_returns_config():
    config = get_subagent_config("general-purpose")
    assert config is not None
    assert config.name == "general-purpose"

def test_get_subagent_config_returns_none_for_unknown():
    config = get_subagent_config("nonexistent")
    assert config is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subagents_registry.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/finders/subagents/registry.py
"""Subagent registry for managing available subagents."""

import logging
from finders.subagents.config import SubagentConfig
from finders.subagents.builtins import BUILTIN_SUBAGENTS

logger = logging.getLogger(__name__)


def get_subagent_config(name: str) -> SubagentConfig | None:
    """Get a subagent configuration by name.

    Args:
        name: The name of the subagent.

    Returns:
        SubagentConfig if found, None otherwise.
    """
    return BUILTIN_SUBAGENTS.get(name)


def get_available_subagent_names() -> list[str]:
    """Get all available subagent names.

    Returns:
        List of subagent names.
    """
    return list(BUILTIN_SUBAGENTS.keys())
```

```python
# src/finders/subagents/__init__.py
from .config import SubagentConfig
from .registry import get_available_subagent_names, get_subagent_config

__all__ = [
    "SubagentConfig",
    "get_available_subagent_names",
    "get_subagent_config",
]
```

**Step 4: Run test to verify it fails (builtins not created yet)**

Run: `pytest tests/test_subagents_registry.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'finders.subagents.builtins'"

**Step 5: Create builtins package (placeholder for Task 3)**

```python
# src/finders/subagents/builtins/__init__.py
"""Built-in subagent configurations."""

BUILTIN_SUBAGENTS = {}
```

**Step 6: Run test to verify it passes (will fail until Task 3 completes)**

Run: `pytest tests/test_subagents_registry.py -v`
Expected: FAIL (general-purpose not registered yet) - this is expected, will pass after Task 3

**Step 7: Commit**

```bash
git add src/finders/subagents/registry.py src/finders/subagents/__init__.py src/finders/subagents/builtins/__init__.py tests/test_subagents_registry.py
git commit -m "feat: add subagent registry"
```

---

### Task 3: General-Purpose Subagent

**Files:**
- Create: `src/finders/subagents/builtins/general_purpose.py`
- Modify: `src/finders/subagents/builtins/__init__.py`
- Test: `tests/test_subagents_registry.py` (update to verify general-purpose is registered)

**Step 1: Write the failing test**

```python
# Add to tests/test_subagents_registry.py
def test_general_purpose_config():
    from finders.subagents.builtins.general_purpose import GENERAL_PURPOSE_CONFIG
    assert GENERAL_PURPOSE_CONFIG.name == "general-purpose"
    assert GENERAL_PURPOSE_CONFIG.max_turns == 50
    assert "task" in GENERAL_PURPOSE_CONFIG.disallowed_tools
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subagents_registry.py::test_general_purpose_config -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/finders/subagents/builtins/general_purpose.py
"""General-purpose subagent configuration."""

from finders.subagents.config import SubagentConfig

GENERAL_PURPOSE_CONFIG = SubagentConfig(
    name="general-purpose",
    description="""A capable agent for complex, multi-step tasks that require both exploration and action.

Use this subagent when:
- The task requires complex reasoning or multiple dependent steps
- The task would benefit from isolated context management

Do NOT use for simple, single-step operations.""",
    system_prompt="""You are a general-purpose subagent working on a delegated task. Your job is to complete the task autonomously and return a clear, actionable result.

<guidelines>
- Focus on completing the delegated task efficiently
- Use available tools as needed to accomplish the goal
- Think step by step but act decisively
- If you encounter issues, explain them clearly in your response
- Return a concise summary of what you accomplished
- Do NOT ask for clarification - work with the information provided
</guidelines>

<output_format>
When you complete the task, provide:
1. A brief summary of what was accomplished
2. Key findings or results
3. Any relevant file paths, data, or artifacts created
4. Issues encountered (if any)
5. Citations: Use `[citation:Title](URL)` format for external sources
</output_format>
""",
    tools=None,  # Inherit all tools from parent
    disallowed_tools=["task"],  # Prevent nesting
    model="inherit",
    max_turns=50,
)
```

```python
# Update src/finders/subagents/builtins/__init__.py
"""Built-in subagent configurations."""

from .general_purpose import GENERAL_PURPOSE_CONFIG

__all__ = [
    "GENERAL_PURPOSE_CONFIG",
]

# Registry of built-in subagents
BUILTIN_SUBAGENTS = {
    "general-purpose": GENERAL_PURPOSE_CONFIG,
}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_subagents_registry.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add src/finders/subagents/builtins/general_purpose.py src/finders/subagents/builtins/__init__.py tests/test_subagents_registry.py
git commit -m "feat: add general-purpose subagent"
```

---

### Task 4: Subagent Executor

**Files:**
- Create: `src/finders/subagents/executor.py`
- Test: `tests/test_subagents_executor.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subagents_executor.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/finders/subagents/executor.py
"""Subagent execution engine."""

import asyncio
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from finders.subagents.config import SubagentConfig
from finders.utils.config import get_settings

logger = logging.getLogger(__name__)


class SubagentStatus(Enum):
    """Status of a subagent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class SubagentResult:
    """Result of a subagent execution."""

    task_id: str
    trace_id: str
    status: SubagentStatus
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ai_messages: list[dict[str, Any]] = field(default_factory=list)


# Global storage for background task results
_background_tasks: dict[str, SubagentResult] = {}
_background_tasks_lock = threading.Lock()

# Thread pools
_scheduler_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subagent-scheduler-")
_execution_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subagent-exec-")


def _filter_tools(all_tools, allowed: list[str] | None, disallowed: list[str] | None):
    """Filter tools based on subagent configuration."""
    filtered = all_tools

    if allowed is not None:
        allowed_set = set(allowed)
        filtered = [t for t in filtered if t.name in allowed_set]

    if disallowed is not None:
        disallowed_set = set(disallowed)
        filtered = [t for t in filtered if t.name not in disallowed_set]

    return filtered


class SubagentExecutor:
    """Executor for running subagents."""

    def __init__(
        self,
        config: SubagentConfig,
        tools: list,
        parent_model: str | None = None,
    ):
        self.config = config
        self.parent_model = parent_model
        self.trace_id = str(uuid.uuid4())[:8]

        self.tools = _filter_tools(
            tools,
            config.tools,
            config.disallowed_tools,
        )

        logger.info(f"[trace={self.trace_id}] SubagentExecutor initialized: {config.name} with {len(self.tools)} tools")

    def _create_agent(self):
        """Create the agent instance."""
        settings = get_settings()
        model_name = self.parent_model if self.config.model == "inherit" else self.config.model
        model = settings.create_chat_model(model_name=model_name)

        from finders.agents.factory import _build_middleware
        middlewares = _build_middleware(settings)

        return create_agent(
            model=model,
            tools=self.tools,
            middleware=middlewares,
            system_prompt=self.config.system_prompt,
        )

    def _build_initial_state(self, task: str) -> dict[str, Any]:
        """Build the initial state for agent execution."""
        return {
            "messages": [HumanMessage(content=task)],
        }

    async def _aexecute(self, task: str, result_holder: SubagentResult | None = None) -> SubagentResult:
        """Execute a task asynchronously."""
        if result_holder is not None:
            result = result_holder
        else:
            task_id = str(uuid.uuid4())[:8]
            result = SubagentResult(
                task_id=task_id,
                trace_id=self.trace_id,
                status=SubagentStatus.RUNNING,
                started_at=datetime.now(),
            )

        try:
            agent = self._create_agent()
            state = self._build_initial_state(task)

            run_config = {
                "recursion_limit": self.config.max_turns,
            }

            logger.info(f"[trace={self.trace_id}] Subagent {self.config.name} starting async execution with max_turns={self.config.max_turns}")

            final_state = None
            async for chunk in agent.astream(state, config=run_config, stream_mode="values"):
                final_state = chunk

                messages = chunk.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    from langchain_core.messages import AIMessage
                    if isinstance(last_message, AIMessage):
                        message_dict = last_message.model_dump()
                        message_id = message_dict.get("id")
                        is_duplicate = False
                        if message_id:
                            is_duplicate = any(msg.get("id") == message_id for msg in result.ai_messages)
                        else:
                            is_duplicate = message_dict in result.ai_messages

                        if not is_duplicate:
                            result.ai_messages.append(message_dict)

            logger.info(f"[trace={self.trace_id}] Subagent {self.config.name} completed async execution")

            if final_state is None:
                result.result = "No response generated"
            else:
                messages = final_state.get("messages", [])
                last_ai_message = None
                from langchain_core.messages import AIMessage
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        last_ai_message = msg
                        break

                if last_ai_message is not None:
                    content = last_ai_message.content
                    if isinstance(content, str):
                        result.result = content
                    elif isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if isinstance(block, str):
                                text_parts.append(block)
                            elif isinstance(block, dict):
                                text_val = block.get("text")
                                if isinstance(text_val, str):
                                    text_parts.append(text_val)
                        result.result = "\n".join(text_parts) if text_parts else "No text content in response"
                    else:
                        result.result = str(content)
                else:
                    result.result = "No response generated"

            result.status = SubagentStatus.COMPLETED
            result.completed_at = datetime.now()

        except Exception as e:
            logger.exception(f"[trace={self.trace_id}] Subagent {self.config.name} async execution failed")
            result.status = SubagentStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()

        return result

    def execute(self, task: str, result_holder: SubagentResult | None = None) -> SubagentResult:
        """Execute a task synchronously (wrapper around async execution)."""
        try:
            return asyncio.run(self._aexecute(task, result_holder))
        except Exception as e:
            logger.exception(f"[trace={self.trace_id}] Subagent {self.config.name} execution failed")
            if result_holder is not None:
                result = result_holder
            else:
                result = SubagentResult(
                    task_id=str(uuid.uuid4())[:8],
                    trace_id=self.trace_id,
                    status=SubagentStatus.FAILED,
                )
            result.status = SubagentStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
            return result

    def execute_async(self, task: str, task_id: str | None = None) -> str:
        """Start a task execution in the background."""
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        result = SubagentResult(
            task_id=task_id,
            trace_id=self.trace_id,
            status=SubagentStatus.PENDING,
        )

        logger.info(f"[trace={self.trace_id}] Subagent {self.config.name} starting async execution, task_id={task_id}, timeout={self.config.timeout_seconds}s")

        with _background_tasks_lock:
            _background_tasks[task_id] = result

        def run_task():
            with _background_tasks_lock:
                _background_tasks[task_id].status = SubagentStatus.RUNNING
                _background_tasks[task_id].started_at = datetime.now()
                result_holder = _background_tasks[task_id]

            try:
                execution_future = _execution_pool.submit(self.execute, task, result_holder)
                try:
                    exec_result = execution_future.result(timeout=self.config.timeout_seconds)
                    with _background_tasks_lock:
                        _background_tasks[task_id].status = exec_result.status
                        _background_tasks[task_id].result = exec_result.result
                        _background_tasks[task_id].error = exec_result.error
                        _background_tasks[task_id].completed_at = datetime.now()
                        _background_tasks[task_id].ai_messages = exec_result.ai_messages
                except FuturesTimeoutError:
                    logger.error(f"[trace={self.trace_id}] Subagent {self.config.name} execution timed out after {self.config.timeout_seconds}s")
                    with _background_tasks_lock:
                        _background_tasks[task_id].status = SubagentStatus.TIMED_OUT
                        _background_tasks[task_id].error = f"Execution timed out after {self.config.timeout_seconds} seconds"
                        _background_tasks[task_id].completed_at = datetime.now()
                    execution_future.cancel()
            except Exception as e:
                logger.exception(f"[trace={self.trace_id}] Subagent {self.config.name} async execution failed")
                with _background_tasks_lock:
                    _background_tasks[task_id].status = SubagentStatus.FAILED
                    _background_tasks[task_id].error = str(e)
                    _background_tasks[task_id].completed_at = datetime.now()

        _scheduler_pool.submit(run_task)
        return task_id


def get_background_task_result(task_id: str) -> SubagentResult | None:
    """Get the result of a background task."""
    with _background_tasks_lock:
        return _background_tasks.get(task_id)


def cleanup_background_task(task_id: str) -> None:
    """Remove a completed task from background tasks."""
    with _background_tasks_lock:
        task = _background_tasks.get(task_id)
        if task and task.status in {SubagentStatus.COMPLETED, SubagentStatus.FAILED, SubagentStatus.TIMED_OUT}:
            del _background_tasks[task_id]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_subagents_executor.py -v`
Expected: PASS

**Step 5: Update __init__.py to export executor components**

```python
# Update src/finders/subagents/__init__.py
from .config import SubagentConfig
from .executor import SubagentExecutor, SubagentResult, SubagentStatus
from .registry import get_available_subagent_names, get_subagent_config

__all__ = [
    "SubagentConfig",
    "SubagentExecutor",
    "SubagentResult",
    "SubagentStatus",
    "get_available_subagent_names",
    "get_subagent_config",
]
```

**Step 6: Commit**

```bash
git add src/finders/subagents/executor.py src/finders/subagents/__init__.py tests/test_subagents_executor.py
git commit -m "feat: add subagent executor with background task support"
```

---

### Task 5: Task Tool

**Files:**
- Create: `src/finders/tools/task_tool.py`
- Modify: `src/finders/tools/registry.py` (add task_tool to core tools)
- Test: `tests/test_task_tool.py`

**Step 1: Write the failing test**

```python
# tests/test_task_tool.py
import pytest
from finders.tools.task_tool import task_tool

def test_task_tool_is_callable():
    assert callable(task_tool)

def test_task_tool_has_correct_name():
    assert task_tool.name == "task"

def test_task_tool_with_invalid_subagent_type():
    """Test that task_tool returns error for unknown subagent type."""
    import asyncio
    
    async def run_test():
        result = await task_tool.ainvoke({
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "nonexistent-type",
        })
        return result
    
    result = asyncio.run(run_test())
    assert "Error" in result
    assert "nonexistent-type" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_tool.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/finders/tools/task_tool.py
"""Task tool for delegating work to subagents."""

import asyncio
import logging
from dataclasses import replace
from typing import Annotated

from langchain.tools import InjectedToolCallId, ToolRuntime, tool

from finders.subagents import SubagentExecutor, get_available_subagent_names, get_subagent_config
from finders.subagents.executor import SubagentStatus, cleanup_background_task, get_background_task_result
from finders.tools.registry import get_core_tools
from finders.utils.config import get_settings

logger = logging.getLogger(__name__)


@tool("task", parse_docstring=True)
async def task_tool(
    description: str,
    prompt: str,
    subagent_type: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    max_turns: int | None = None,
) -> str:
    """Delegate a task to a specialized subagent that runs in its own context.

    Subagents help you:
    - Preserve context by keeping exploration and implementation separate
    - Handle complex multi-step tasks autonomously
    - Execute operations in isolated contexts

    Available subagent types:
    - **general-purpose**: A capable agent for complex, multi-step tasks that require
      both exploration and action. Use when the task requires complex reasoning,
      multiple dependent steps, or would benefit from isolated context.

    When to use this tool:
    - Complex tasks requiring multiple steps or tools
    - Tasks that produce verbose output
    - When you want to isolate context from the main conversation

    When NOT to use this tool:
    - Simple, single-step operations (use tools directly)
    - Tasks requiring user interaction or clarification

    Args:
        description: A short (3-5 word) description of the task. ALWAYS PROVIDE THIS PARAMETER FIRST.
        prompt: The task description for the subagent. Be specific and clear. ALWAYS PROVIDE THIS PARAMETER SECOND.
        subagent_type: The type of subagent to use. ALWAYS PROVIDE THIS PARAMETER THIRD.
        max_turns: Optional maximum number of agent turns. Defaults to subagent's configured max.
    """
    available_subagent_names = get_available_subagent_names()

    config = get_subagent_config(subagent_type)
    if config is None:
        available = ", ".join(available_subagent_names)
        return f"Error: Unknown subagent type '{subagent_type}'. Available: {available}"

    overrides: dict = {}
    if max_turns is not None:
        overrides["max_turns"] = max_turns

    if overrides:
        config = replace(config, **overrides)

    settings = get_settings()
    parent_model = settings.agent.model

    tools = get_core_tools(settings)

    executor = SubagentExecutor(
        config=config,
        tools=tools,
        parent_model=parent_model,
    )

    task_id = executor.execute_async(prompt, task_id=tool_call_id)

    poll_count = 0
    last_status = None
    max_poll_count = (config.timeout_seconds + 60) // 5

    logger.info(f"[trace={executor.trace_id}] Started background task {task_id} (subagent={subagent_type}, timeout={config.timeout_seconds}s, polling_limit={max_poll_count} polls)")

    try:
        while True:
            result = get_background_task_result(task_id)

            if result is None:
                logger.error(f"[trace={executor.trace_id}] Task {task_id} not found in background tasks")
                return f"Error: Task {task_id} disappeared from background tasks"

            if result.status != last_status:
                logger.info(f"[trace={executor.trace_id}] Task {task_id} status: {result.status.value}")
                last_status = result.status

            if result.status == SubagentStatus.COMPLETED:
                logger.info(f"[trace={executor.trace_id}] Task {task_id} completed after {poll_count} polls")
                cleanup_background_task(task_id)
                return f"Task Succeeded. Result: {result.result}"
            elif result.status == SubagentStatus.FAILED:
                logger.error(f"[trace={executor.trace_id}] Task {task_id} failed: {result.error}")
                cleanup_background_task(task_id)
                return f"Task failed. Error: {result.error}"
            elif result.status == SubagentStatus.TIMED_OUT:
                logger.warning(f"[trace={executor.trace_id}] Task {task_id} timed out: {result.error}")
                cleanup_background_task(task_id)
                return f"Task timed out. Error: {result.error}"

            await asyncio.sleep(5)
            poll_count += 1

            if poll_count > max_poll_count:
                timeout_minutes = config.timeout_seconds // 60
                logger.error(f"[trace={executor.trace_id}] Task {task_id} polling timed out after {poll_count} polls")
                return f"Task polling timed out after {timeout_minutes} minutes. Status: {result.status.value}"
    except asyncio.CancelledError:
        raise
```

**Step 4: Update tool registry to include task_tool**

```python
# Update src/finders/tools/registry.py - add to get_core_tools()
def get_core_tools(settings: Settings) -> list[BaseTool]:
    """获取核心工具列表。"""
    from finders.tools.task_tool import task_tool
    
    tools = [
        web_search,
        web_fetch,
        read_file,
        write_file,
        task_tool,  # Add subagent delegation tool
    ]
    # ... rest of function unchanged
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_task_tool.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/finders/tools/task_tool.py src/finders/tools/registry.py tests/test_task_tool.py
git commit -m "feat: add task tool for subagent delegation"
```

---

### Task 6: Update Agent Factory

**Files:**
- Modify: `src/finders/agents/factory.py` (extract _build_middleware function)
- Test: `pytest tests/test_prompts.py tests/test_integration.py -v` (verify existing tests still pass)

**Step 1: Extract middleware building into reusable function**

```python
# Add to src/finders/agents/factory.py before create_finders_agent()
def _build_middleware(settings: Settings):
    """Build middleware pipeline for agent."""
    model = settings.create_chat_model()
    fast_model = settings.create_chat_model(fast=True)

    return [
        TodoListMiddleware(),
        SummarizationMiddleware(
            model=fast_model,
            trigger=("tokens", settings.agent.compact_threshold),
        ),
        ContextEditingMiddleware(),
        ToolCallLimitMiddleware(
            run_limit=settings.tools.max_calls_per_tool,
        ),
        ToolRetryMiddleware(
            max_retries=2,
        ),
        ModelRetryMiddleware(
            max_retries=3,
        ),
        HumanInTheLoopMiddleware(
            interrupt_on={"write_file": True},
        ),
    ]
```

**Step 2: Update create_finders_agent to use _build_middleware**

```python
# Update create_finders_agent() to use _build_middleware
def create_finders_agent(settings: Settings):
    """创建 Finders Agent 实例。"""
    model = settings.create_chat_model()
    system_prompt = build_system_prompt(settings)
    tools = get_core_tools(settings)

    middleware = _build_middleware(settings)

    # Memory flush + recall (if enabled)
    if settings.memory.enabled:
        from finders.middleware.memory import MemoryMiddleware
        middleware.append(
            MemoryMiddleware(
                memory_dir=str(get_finders_dir()),
                flush_threshold=settings.agent.compact_threshold,
            )
        )

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
```

**Step 3: Run existing tests to verify no regressions**

Run: `pytest tests/test_prompts.py tests/test_integration.py -v`
Expected: PASS (all 9 tests)

**Step 4: Commit**

```bash
git add src/finders/agents/factory.py
git commit -m "refactor: extract _build_middleware for reuse by subagents"
```

---

### Task 7: Integration Test

**Files:**
- Create: `tests/test_subagent_integration.py`

**Step 1: Write integration test**

```python
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
    
    with patch("finders.skills.registry.has_skills", return_value=False):
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
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "invalid-type",
        })
        return result
    
    result = asyncio.run(run_test())
    assert "Error" in result
    assert "invalid-type" in result
    assert "general-purpose" in result  # Should list available types
```

**Step 2: Run integration tests**

Run: `pytest tests/test_subagent_integration.py -v`
Expected: PASS (all 3 tests)

**Step 3: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/test_agent_web_search_live.py`
Expected: PASS (all tests except live agent test)

**Step 4: Commit**

```bash
git add tests/test_subagent_integration.py
git commit -m "test: add subagent integration tests"
```

---

### Task 8: Update Subagents __init__.py Exports

**Files:**
- Modify: `src/finders/subagents/__init__.py`

**Step 1: Update exports to include executor helper functions**

```python
# Update src/finders/subagents/__init__.py
from .config import SubagentConfig
from .executor import (
    SubagentExecutor,
    SubagentResult,
    SubagentStatus,
    get_background_task_result,
    cleanup_background_task,
)
from .registry import get_available_subagent_names, get_subagent_config

__all__ = [
    "SubagentConfig",
    "SubagentExecutor",
    "SubagentResult",
    "SubagentStatus",
    "get_available_subagent_names",
    "get_subagent_config",
    "get_background_task_result",
    "cleanup_background_task",
]
```

**Step 2: Run tests to verify imports work**

Run: `python -c "from finders.subagents import *; print('All imports successful')"`
Expected: "All imports successful"

**Step 3: Commit**

```bash
git add src/finders/subagents/__init__.py
git commit -m "chore: update subagents package exports"
```

---

### Task 9: Final Verification and Cleanup

**Files:**
- All modified files

**Step 1: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/test_agent_web_search_live.py`
Expected: PASS (all tests)

**Step 2: Verify file structure**

Run: `find src/finders/subagents -type f -name "*.py" | sort`
Expected output:
```
src/finders/subagents/__init__.py
src/finders/subagents/builtins/__init__.py
src/finders/subagents/builtins/general_purpose.py
src/finders/subagents/config.py
src/finders/subagents/executor.py
src/finders/subagents/registry.py
```

**Step 3: Verify task_tool is importable**

Run: `python -c "from finders.tools.task_tool import task_tool; print(f'Task tool name: {task_tool.name}')"`
Expected: "Task tool name: task"

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete subagent integration with task tool"
```

---

## Summary

This plan implements a simplified subagent system for Finders with:
- **5 new files** in `src/finders/subagents/` (config, registry, executor, builtins)
- **1 new tool** in `src/finders/tools/task_tool.py`
- **4 test files** with comprehensive coverage
- **2 modified files** (factory.py, registry.py)

The implementation follows deer-flow's architecture while removing unnecessary complexity (sandbox, bash agent) and adapting to Finders' existing configuration and tool systems.
