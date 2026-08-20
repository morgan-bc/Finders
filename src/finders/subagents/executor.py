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
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents.middleware import TodoListMiddleware, ToolRetryMiddleware, ModelRetryMiddleware

from finders.middlewares.dynamic_context import DynamicContextMiddleware
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
        skill_metadata: dict[str, dict] | None = None,
    ):
        self.config = config
        self.parent_model = parent_model
        self.trace_id = str(uuid.uuid4())[:8]
        self.skill_metadata = skill_metadata

        self.tools = _filter_tools(
            tools,
            config.tools,
            config.disallowed_tools,
        )

        logger.info(f"[trace={self.trace_id}] SubagentExecutor initialized: {config.name} with {len(self.tools)} tools")

    def _load_skills_content(self) -> str:
        """Load skill content directly into system prompt."""
        if not self.config.allowed_skills:
            return ""
        
        skill_section = []
        for skill_name in self.config.allowed_skills:
            skill = self.skill_metadata.get(skill_name, None)
            if skill is not None:
                skill_content = Path(skill["path"]).read_text(encoding="utf-8")
                skill_content = f"<skill>{skill_content}</skill>"
                skill_section.append(skill_content)
        
        return "\n\n".join(skill_section)

    def _create_agent(self, checkpointer=None):
        """Create the agent instance."""
        settings = get_settings()
        model_name = self.parent_model if self.config.model == "inherit" else self.config.model
        model = settings.create_chat_model(model_name=model_name)

        middlewares = [
            DynamicContextMiddleware(),
            TodoListMiddleware(),
            ToolRetryMiddleware(max_retries=2),
            ModelRetryMiddleware(max_retries=3),
        ]

        # Load skills content directly into system prompt
        system_prompt = self.config.system_prompt
        skills_content = self._load_skills_content()
        if skills_content:
            system_prompt = system_prompt + "\n\n" + skills_content

        return create_agent(
            model=model,
            tools=self.tools,
            middleware=middlewares,
            system_prompt=system_prompt,
            # checkpointer=checkpointer,
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
            from finders.utils.checkpointing import open_saver

            thread_id = result.task_id or str(uuid.uuid4())
            state = self._build_initial_state(task)
            run_config = {
                "recursion_limit": self.config.max_turns,
                "configurable": {"thread_id": thread_id},
            }

            logger.info(
                f"[trace={self.trace_id}] Subagent {self.config.name} starting async "
                f"execution with max_turns={self.config.max_turns} thread={thread_id}"
            )

            async with open_saver() as saver:
                await saver.setup()
                agent = self._create_agent(checkpointer=saver)

                final_state = None
                async for chunk in agent.astream(state, config=run_config, stream_mode="values"):
                    final_state = chunk

                    messages = chunk.get("messages", [])
                    if messages:
                        last_message = messages[-1]
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
