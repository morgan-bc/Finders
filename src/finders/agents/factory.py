"""Agent factory for creating Finders agent with middleware pipeline."""
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ContextEditingMiddleware,
    ToolCallLimitMiddleware,
    TodoListMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
    ModelFallbackMiddleware,
)
from finders.utils.config import Settings
from finders.tools.registry import get_core_tools
from finders.agents.prompt import build_system_prompt
from finders.utils.paths import get_finders_dir


def create_finders_agent(settings: Settings):
    """创建 Finders Agent 实例。"""

    model = settings.create_chat_model()
    fast_model = settings.create_chat_model(fast=True)

    system_prompt = build_system_prompt(settings)
    tools = get_core_tools(settings)

    middleware = [
        # 1. 任务规划：Agent 自动分解复杂查询为子任务清单
        TodoListMiddleware(),
        # 2. 上下文压缩：当上下文超过阈值时，用快模型压缩旧消息
        SummarizationMiddleware(
            model=fast_model,
            trigger=("tokens", settings.agent.compact_threshold),
        ),
        # 3. 上下文编辑：无条件截断超出 token 限制的消息
        ContextEditingMiddleware(),
        # 4. 工具调用限制：防止单个工具被过度调用
        ToolCallLimitMiddleware(
            run_limit=settings.tools.max_calls_per_tool,
        ),
        # 5. 工具重试：工具执行失败自动重试
        ToolRetryMiddleware(
            max_retries=2,
        ),
        # 6. 模型重试：模型 API 调用失败自动重试
        ModelRetryMiddleware(
            max_retries=3,
        ),
        # 7. 人工审批：需要确认的写操作
        HumanInTheLoopMiddleware(
            interrupt_on={"write_file": True},
        ),
    ]

    # 8. Memory flush + recall（如果启用记忆系统）
    if settings.memory.enabled:
        from finders.middlewares.memory import MemoryMiddleware
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
