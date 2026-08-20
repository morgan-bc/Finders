# Finders - Financial Deep Research

Finders is a deep financial research agent built with **Python + LangChain 1.0 + LangGraph**. It works as an **orchestrator**: it decomposes complex questions, delegates research subtasks to specialized **subagents**, coordinates their parallel execution, and synthesizes the results into comprehensive, evidence-driven reports.

## Features

- **Orchestrator-style agent** — the main agent plans, delegates via `task_tool`, coordinates, and synthesizes; it does not do the research itself
- **Built-in subagents** — `general-purpose` and `deep-research`, each with its own system prompt, tool allow/deny lists, model, and turn budget
- **Rich terminal UI** — streaming Markdown answers inside an `Answer` panel, live tool-call lines (`Tool: <name> (args)`), "Thinking..." spinner
- **Persistent sessions** — every conversation is checkpointed to SQLite (`langgraph-checkpoint-sqlite`, WAL mode); resume or review any past session
- **Session manager** — `/session` interactive picker with keyboard navigation
- **Skills system** — pluggable Markdown skills loaded into the agent context (deep-research methodology, company fundamentals, data analysis)
- **Full toolset** — web search/fetch, filesystem ops, code execution, memory search, and subagent delegation
- **FastAPI + SSE server** — expose the agent over HTTP with streaming events

## Architecture

```
User query
   │
   ▼
┌────────────────────────── Main Agent (orchestrator) ──────────────────────────┐
│  Middleware pipeline:                                                         │
│   SkillsMiddleware → DynamicContextMiddleware → TodoListMiddleware            │
│   → SummarizationMiddleware → ContextEditingMiddleware → ToolRetryMiddleware  │
│   → ModelRetryMiddleware → [MemoryMiddleware]                                 │
│                                                                               │
│  Tools: web_search, web_fetch, read_file, write_file, edit_file,              │
│         list_dir, glob, grep, execute, task_tool, [memory_search_tool]        │
└───────────────┬──────────────────────────────────────────────┬────────────────┘
                │ task_tool (delegate)                          │ direct tools
                ▼                                               ▼
  ┌─────────────────────────┐                     ┌─────────────────────────┐
  │ Subagents               │                     │ Skills / Memory         │
  │  • general-purpose      │                     │  • deep-research        │
  │  • deep-research        │                     │  • company-fundamentals │
  └─────────────────────────┘                     │  • data-analyzer        │
                                                  └─────────────────────────┘
```

### Middleware

| Middleware | Purpose |
| --- | --- |
| `SkillsMiddleware` | Loads Markdown skills (project + user) into context |
| `DynamicContextMiddleware` | Manages dynamic context window |
| `TodoListMiddleware` | Decomposes complex tasks into a TODO list |
| `SummarizationMiddleware` | Compacts conversation when tokens exceed threshold |
| `ContextEditingMiddleware` | Allows context pruning |
| `ToolRetryMiddleware` | Retries failed tool calls (2 retries) |
| `ModelRetryMiddleware` | Retries model failures (3 retries) |
| `MemoryMiddleware` | Optional memory flush/recall (enabled via config) |

### Built-in Subagents

| Subagent | Description |
| --- | --- |
| `deep-research` | Systematic multi-angle web research following a 4-phase methodology (broad exploration → deep dive → diversity & validation → synthesis check). Max 1000 turns. |
| `general-purpose` | General delegation target for subtasks. |

## Quick Start

```bash
# 1. Install (editable, with dev deps)
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# 3. Run the CLI
finders
```

## Configuration (`.env`)

| Variable | Required | Description |
| --- | --- | --- |
| `LLM_API_BASE` | Yes | OpenAI-compatible API base URL (e.g. DeepSeek) |
| `LLM_API_KEY` | Yes | LLM API key |
| `BASE_MODEL` | No | Default model (default `deepseek-v4-flash`) |
| `FAST_MODEL` | No | Fast model for compaction/aux tasks |
| `TAVILY_API_KEY` | No | Web search provider key |
| `TUSHARE_TOKEN` | No | Tushare financial data token |
| `JINA_WEB_FETCH_BASE` | No | Jina Reader base URL (`https://r.jina.ai`; use `https://r.jinaai.cn` in mainland China) |
| `FINDERS_WORKSPACE` | No | Sandbox/workspace root (default `~/.finders/workspace`) |

Additional runtime settings (model, `recursion_limit`, compaction threshold, memory, tool concurrency) live in `src/finders/utils/config.py`.

## CLI Usage

```bash
finders
```

Interactive commands:

| Command | Description |
| --- | --- |
| `>` (any question) | Run a query; answer streams as Markdown |
| `/session` | Open session manager: `↑/↓` select, `Enter` load, `d` delete, `q`/`Esc` quit |
| `/model <name>` | Switch the active model |
| `/quit` `/exit` `/q` | Exit |

Sessions are stored in `$FINDERS_WORKSPACE/sessions/chat.db`. Loading a historical session replays the conversation using the same rendering as live chat (Markdown for user/assistant messages, tool-call lines with parameters only — no execution results).

## API Server

```bash
python -m uvicorn finders.api.app:create_app --factory
```

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Health check |
| `/api/query` | POST | Run a query, returns an SSE event stream |

`POST /api/query` request body:

```json
{
  "query": "深度研究一下中国平安的基本数据",
  "model": null,
  "fast_model": null,
  "max_iterations": 10,
  "memory_enabled": true
}
```

SSE event types: `thinking`, `tool_start`, `tool_end`, `tool_error`, `answer`.

## Project Structure

```
src/finders/
├── agents/          # Agent factory, system prompt, scratchpad
├── api/             # FastAPI app, routes (SSE), models
├── cli/             # Terminal UI (tui.py) + entry point (main.py)
├── memory/          # Memory chunking, indexing, search
├── middlewares/     # DynamicContext, Memory
├── sandbox/         # Sandboxed execution
├── skills/          # Skill loading + SkillsMiddleware
├── subagents/       # Subagent config, registry, executor, built-ins
├── tools/           # Tool registry + implementations
└── utils/           # Config, paths, checkpointing (sessions), tokens
skills/              # Markdown skills (deep-research, company-fundamentals, data-analyzer)
```

## Development

```bash
ruff check src/       # Lint
pytest tests/ -v      # Tests
```

## Notes

- The main agent is an **orchestrator** — it always delegates complex research to subagents via `task_tool` and never researches itself.
- Simple/factual questions should be answered with a single `web_search`; independent tool calls are issued in parallel in a single assistant turn.
- `astream_events` calls pass `config={"recursion_limit": ...}` (default 100) to avoid `GraphRecursionError`.
