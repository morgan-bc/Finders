# Subagent Integration Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add subagent functionality to Finders, allowing the main agent to delegate complex tasks to specialized subagents that run in isolated contexts.

**Architecture:** Simplified adaptation of deer-flow's subagent system, removing sandbox-related code and adapting to Finders' existing tool chain and configuration system.

**Tech Stack:** Python, LangChain, LangGraph, ThreadPoolExecutor, dataclasses

---

## Design Overview

### File Structure

```
src/finders/subagents/
  __init__.py              # Export public API
  config.py                # SubagentConfig dataclass
  registry.py              # Registry managing subagent configs
  executor.py              # Execution engine (background tasks + polling)
  builtins/
    __init__.py            # Export built-in subagents
    general_purpose.py     # General-purpose subagent config

src/finders/tools/task_tool.py  # Task tool (delegates to subagents)
```

### Core Components

#### 1. SubagentConfig (config.py)

```python
@dataclass
class SubagentConfig:
    name: str                    # Unique identifier, e.g. "general-purpose"
    description: str             # When to use this subagent
    system_prompt: str           # System prompt guiding subagent behavior
    tools: list[str] | None      # Allowed tools (None = inherit all)
    disallowed_tools: list[str]  # Denied tools (default excludes "task" to prevent nesting)
    model: str                   # Model name, "inherit" uses parent agent's model
    max_turns: int               # Maximum agent turns (default 50)
    timeout_seconds: int         # Timeout in seconds (default 900 = 15 minutes)
```

#### 2. Registry (registry.py)

- `BUILTIN_SUBAGENTS` dict storing built-in subagent configs
- `get_subagent_config(name)` → `SubagentConfig | None`
- `get_available_subagent_names()` → `list[str]`
- Optional: support timeout overrides from Settings

#### 3. Executor (executor.py)

**SubagentExecutor class:**
- `execute_async(task, task_id)` → `str` — Start background task, return task_id
- `_aexecute(task, result_holder)` → `SubagentResult` — Async execution, collect AI messages
- Uses `ThreadPoolExecutor` for background task management
- Global `_background_tasks` dict for task state storage

**SubagentResult dataclass:**
- `task_id`, `trace_id`, `status`, `result`, `error`
- `started_at`, `completed_at`, `ai_messages`

**SubagentStatus enum:**
- `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMED_OUT`

**Helper functions:**
- `get_background_task_result(task_id)` → `SubagentResult | None`
- `cleanup_background_task(task_id)` → `None`

#### 4. Built-in Subagent (builtins/general_purpose.py)

System prompt guidelines:
- Guide subagent to complete tasks autonomously
- Require clear summary, key findings, citations
- Prohibit `task` tool to prevent nesting
- Prohibit `ask_clarification` (no need to ask user)

#### 5. Task Tool (tools/task_tool.py)

LangChain `@tool` decorated function:
- Parameters: `description`, `prompt`, `subagent_type`, `max_turns` (optional)
- Flow:
  1. Validate subagent_type
  2. Get config and build overrides
  3. Create SubagentExecutor with filtered tools (exclude task)
  4. Call execute_async to start background task
  5. Poll every 5 seconds until completion
  6. Return final result or error

### Data Flow

```
User Request → Main Agent
                    ↓
               Decides to use task tool
                    ↓
          ┌─────────────────────┐
          │    task_tool.py     │
          │  1. Validate type   │
          │  2. Get config      │
          │  3. Filter tools    │
          └────────┬────────────┘
                   ↓
          ┌─────────────────────┐
          │   executor.py       │
          │  execute_async()    │
          │  → Create Result    │
          │  → Submit to pool   │
          │  → Return task_id   │
          └────────┬────────────┘
                   ↓
          ┌─────────────────────┐
          │   Poll loop (5s)    │
          │  get_result()       │
          │  → RUNNING → ...    │
          │  → COMPLETED/FAILED │
          └────────┬────────────┘
                   ↓
          Return result to Main Agent
```

### Error Handling

| Scenario | Handling |
|----------|----------|
| Unknown subagent_type | Return error with available types |
| Execution timeout | Set status to TIMED_OUT, return timeout error |
| Task disappeared | Return "Task disappeared" error |
| Agent execution exception | Catch exception, set FAILED, return error |
| Polling timeout | Return "Task polling timed out" error |
| No final state | Return "No response generated" |

### Concurrency Control

- `_scheduler_pool`: Scheduler thread pool, `max_workers=3`
- `_execution_pool`: Execution thread pool, `max_workers=3`
- `_background_tasks`: Global dict, thread-safe access via `threading.Lock`
- Max concurrent subagents: 3 (configurable)

### Integration Points with Finders

1. **Tool Registry**: Add `task_tool` to `get_core_tools()` return list
2. **Configuration**: Subagent timeout can be read from Settings (optional)
3. **Model Creation**: Use `settings.create_chat_model()` for subagent model instances
4. **Middleware Reuse**: Subagents can reuse main agent's middleware (SummarizationMiddleware, etc.)

### Removed from deer-flow (Simplification)

- Sandbox-related code (Finders has no sandbox mechanism)
- Bash subagent (not needed for command execution)
- Thread state passing (sandbox_state, thread_data)
- Skills prompt section injection (can be added later if needed)
