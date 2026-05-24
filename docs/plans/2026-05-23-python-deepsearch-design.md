# Python DeepSearch 后端设计文档

> 参考项目：Dexter (TypeScript + LangChain CLI 金融研究 Agent)  
> 目标：Python + LangChain 1.0 + LangGraph 重新实现 DeepSearch 后端  
> 设计日期：2026-05-23

---

## 1. 项目概述

### 1.1 目标

从零构建一个 Python DeepSearch 后端，参考现有 TypeScript Dexter 的架构设计，使用 LangChain 1.0 的 `create_agent` + Middleware 架构实现迭代式 ReAct Agent。

### 1.2 核心特性

- **迭代式 Agent 循环** — 多轮工具调用、推理、回答
- **Middleware 架构** — 上下文管理、Memory、压缩、审批全部通过 Middleware 实现
- **Memory 系统** — SQLite 向量存储 + 混合搜索（向量 + 关键词）+ 时间衰减 + MMR
- **双入口** — CLI（Rich/TUI）+ FastAPI（REST + SSE 事件流）
- **Skill 系统** — SKILL.md 文件驱动的扩展工作流

### 1.3 技术栈

| 组件 | 技术 |
|------|------|
| 运行时 | Python 3.12+ |
| Agent 框架 | LangChain >= 1.0 |
| Agent 运行时 | LangGraph >= 1.0 |
| LLM Provider | langchain-openai, langchain-anthropic |
| 向量存储 | 后续根据实际搜索效果决定是否添加 |
| 全文搜索 | SQLite FTS5 |
| CLI UI | Rich |
| API 框架 | FastAPI + sse-starlette |
| 配置 | Pydantic Settings + YAML |

---

## 2. LangChain 1.0 架构映射

### 2.1 核心概念

| LangChain 1.0 概念 | 用途 |
|-------------------|------|
| `create_agent()` | 统一 Agent 入口，替代 `langgraph.prebuilt.create_react_agent` |
| `Middleware` | 在 Agent 循环的每个步骤前后注入自定义逻辑 |
| `before_model` | 模型调用前钩子 — 动态 prompt、上下文清理 |
| `after_model` | 模型调用后钩子 — Memory flush、工具结果处理 |
| `before_tool` | 工具执行前钩子 — 审批、限流、并发控制 |
| `after_tool` | 工具执行后钩子 — 结果截断、预算控制 |

### 2.2 Middleware 映射表

| TypeScript Dexter 功能 | Python LangChain 1.0 实现 | 类型 |
|----------------------|-------------------------|------|
| Microcompact（轻量清理） | `ContextEditingMiddleware`（`ClearToolUsesEdit`） | 内置 |
| Context Compaction（LLM 压缩） | `SummarizationMiddleware` | 内置 |
| Memory Flush/Recall | MemoryMiddleware（自定义）+ FilesystemMiddleware（底层支撑） | 自定义+内置 |
| Tool Approval | `HumanInTheLoopMiddleware` | 内置 |
| Tool Limit Warning | `ToolCallLimitMiddleware` | 内置 |
| Model Call Limit | `ModelCallLimitMiddleware` | 内置 |
| Tool Concurrency | ❌ 无需 - Agent 自动并发 | N/A |
| Model/Tool Retry | `ModelRetryMiddleware` / `ToolRetryMiddleware` | 内置 |
| Dynamic System Prompt | `dynamic_prompt` 装饰器 | 内置 |
| Model Fallback | `ModelFallbackMiddleware` | 内置 |
| PII Detection | `PIIMiddleware` | 内置（可选） |
| Task Planning | `ToDoListMiddleware` | 内置（可选） |
| Tool Selection | `LLMToolSelectorMiddleware` | 内置（可选） |

### 2.3 Agent 循环流程

```
User Query
    │
    ▼
┌─────────────────────────────────────────────┐
│         create_agent() Loop                  │
│                                              │
│  before_model middleware                     │
│    ├─ DynamicPromptMiddleware                │
│    ├─ ContextEditingMiddleware (清理旧结果)   │
│    └─ MemoryMiddleware (注入记忆上下文)       │
│         │                                    │
│         ▼                                    │
│    ┌─────────────┐                           │
│    │  Model Call  │                           │
│    └─────────────┘                           │
│         │                                    │
│  after_model middleware                      │
│    └─ MemoryMiddleware (flush 到磁盘)         │
│         │                                    │
│    有 tool_calls?                            │
│    ├─ 否 → 返回最终答案                       │
│    └─ 是                                     │
│         │                                    │
│  before_tool middleware                      │
│    ├─ HITLMiddleware (审批)                   │
│    ├─ ToolCallLimitMiddleware (次数限制)      │
│    └─ ConcurrencyMiddleware (并发分组)        │
│         │                                    │
│         ▼                                    │
│    执行工具                                   │
│         │                                    │
│  after_tool middleware                       │
│    └─ 结果截断/预算控制                       │
│         │                                    │
│         ▼                                    │
│    下一轮迭代                                 │
└─────────────────────────────────────────────┘
    │
    ▼
Final Answer (via SSE / CLI output)
```

---

## 3. 项目结构

```
backend/
├── pyproject.toml                    # 项目配置 + 依赖
├── .env.example                      # 环境变量模板
├── README.md
│
├── src/finders
│   ├── __init__.py
│   │
│   ├── agent/                        # Agent 核心
│   │   ├── __init__.py
│   │   ├── factory.py                # create_agent 封装 + 配置
│   │   ├── runner.py                 # Agent 运行器（事件桥接、流式）
│   │   ├── state.py                  # 自定义 AgentState 扩展
│   │   ├── scratchpad.py             # 工作记录（JSONL 持久化、工具计数）
│   │   └── types.py                  # 事件类型、配置类型
│   │
│   ├── middleware/                   # Middleware 实现
│   │   ├── __init__.py
│   │   ├── context.py                # MicrocompactMiddleware — 轻量上下文清理
│   │   ├── memory.py                 # MemoryMiddleware — 记忆 flush + recall
│   │   ├── compaction.py             # ContextOverflowMiddleware — 溢出重试
│   │   ├── tool_limit.py             # ToolLimitMiddleware — 调用次数限制
│   │   └── concurrency.py            # ConcurrencyMiddleware — 并发工具执行
│   │
│   ├── tools/                        # 工具定义
│   │   ├── __init__.py
│   │   ├── registry.py               # 工具注册表（名称 → 实例 + 元数据）
│   │   ├── web_search.py             # 网页搜索（Tavily/Exa）
│   │   ├── web_fetch.py              # 网页内容抓取
│   │   ├── filesystem.py             # 文件读写（read_file, write_file, edit_file）
│   │   └── skill.py                  # skill 调用工具
│   │
│   ├── skills/                       # Skill 系统
│   │   ├── __init__.py
│   │   ├── loader.py                 # SKILL.md YAML frontmatter 解析
│   │   └── registry.py               # 技能发现（内置 + 项目目录扫描）
│   │
│   ├── memory/                       # Memory 系统
│   │   ├── __init__.py
│   │   ├── manager.py                # MemoryManager（单例入口）
│   │   ├── store.py                  # 文件存储（MEMORY.md + 每日文件）
│   │   ├── database.py               # SQLite 数据库（chunks + FTS5 + 向量）
│   │   ├── indexer.py                # 分块索引 + 文件监听
│   │   ├── search.py                 # 混合搜索（向量 + 关键词 + MMR + 衰减）
│   │   ├── embeddings.py             # Embedding Provider（OpenAI/Gemini/Ollama）
│   │   ├── chunker.py                # 文本分块（段落级、重叠）
│   │   ├── temporal_decay.py         # 时间衰减（30天半衰期）
│   │   ├── mmr.py                    # MMR 重排序
│   │   └── types.py                  # 类型定义
│   │
│   ├── prompts/                      # Prompt 管理
│   │   ├── __init__.py
│   │   ├── system.py                 # System Prompt 构建
│   │   └── templates/                # 模板文件
│   │       ├── system.md
│   │       ├── compaction.md
│   │       └── memory_flush.md
│   │
│   ├── api/                          # FastAPI 服务
│   │   ├── __init__.py
│   │   ├── app.py                    # FastAPI 应用创建
│   │   ├── routes.py                 # API 路由（POST /query, GET /health）
│   │   ├── sse.py                    # SSE 事件流
│   │   └── models.py                 # API 请求/响应模型
│   │
│   ├── cli/                          # CLI 入口
│   │   ├── __init__.py
│   │   ├── main.py                   # CLI 主入口
│   │   ├── tui.py                    # Rich TUI 组件
│   │   └── interaction.py            # 用户交互（输入、审批）
│   │
│   └── utils/                        # 工具函数
│       ├── __init__.py
│       ├── config.py                 # 配置加载（YAML + 环境变量）
│       ├── tokens.py                 # Token 估算（usage_metadata + 字符回退）
│       ├── events.py                 # 事件类型（dataclass）
│       └── paths.py                  # 路径管理（.deepsearch 目录）
│
├── skills/                           # 内置 SKILL.md 文件
│   └── dcf/
│       ├── SKILL.md
│       └── sector-wacc.md
│
└── tests/
    ├── test_agent.py
    ├── test_middleware.py
    ├── test_memory.py
    ├── test_tools.py
    └── test_skills.py
```

---

## 4. 核心模块设计

### 4.1 Agent Factory

[`src/finders/agent/factory.py`](src/agent/factory.py)

**职责**：封装 `create_agent` 调用，组装 middleware、tools、prompt。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ToolCallLimitMiddleware,
    ModelCallLimitMiddleware,
    ContextEditingMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
    ModelFallbackMiddleware,
    FilesystemMiddleware,
)
# 可选中间件
# from langchain.agents.middleware import PIIMiddleware, ToDoListMiddleware, LLMToolSelectorMiddleware
from deepsearch.tools.registry import get_core_tools
from deepsearch.prompts.system import build_system_prompt
from deepsearch.config import AgentConfig

def create_deepsearch_agent(config: AgentConfig):
    """创建 DeepSearch Agent 实例。"""
    
    system_prompt = build_system_prompt(
        model=config.model,
        memory_context=config.memory_context,
        skills=config.skills,
    )
    
    tools = get_core_tools(config)
    
    middleware = [
        # 内置：上下文压缩（使用 fast model 做 LLM 摘要压缩）
        SummarizationMiddleware(
            model=config.fast_model,
            threshold=config.compact_threshold,
        ),
        # 内置：上下文编辑（清理旧工具结果，Anthropic clear_tool_uses 风格）
        ContextEditingMiddleware(
            threshold=80_000,
        ),
        # 内置：长期记忆（自动持久化对话到文件系统）
        FilesystemMiddleware(
            memory_dir=config.memory_dir,
        ),
        # 内置：人工审批
        HumanInTheLoopMiddleware(
            interrupt_on={"write_file": True, "edit_file": True},
        ),
        # 内置：工具调用次数限制
        ToolCallLimitMiddleware(
            max_calls_per_tool=3,
        ),
        # 内置：模型调用次数限制（防止无限循环）
        ModelCallLimitMiddleware(
            max_calls=config.max_iterations,
        ),
        # 内置：模型回退（主模型失败时切换到备用模型）
        ModelFallbackMiddleware(
            fallbacks=[config.fallback_model] if config.fallback_model else [],
        ),
        # 内置：模型重试
        ModelRetryMiddleware(
            max_retries=2,
        ),
        # 内置：工具重试
        ToolRetryMiddleware(
            max_retries=2,
        ),
        # 可选：PII 检测（防止敏感信息泄露）
        # PIIMiddleware(mode="redact"),
        # 可选：任务列表（Agent 自动维护 TODO 清单）
        # ToDoListMiddleware(),
        # 可选：动态工具选择（根据上下文筛选可用工具）
        # LLMToolSelectorMiddleware(),
    ]
    
    return create_agent(
        model=config.model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
```

### 4.2 Agent Runner

[`src/agent/runner.py`](src/agent/runner.py)

**职责**：桥接 LangChain `astream_events` 标准事件到 DeepSearch 语义化事件流，支持流式输出。使用 LangChain 内置的 `AsyncCallbackHandler` 作为事件处理基类，而非自定义 dataclass 事件。

**LangChain 标准事件映射**：

| LangChain 事件 | DeepSearch 事件 | 说明 |
|---------------|----------------|------|
| `on_chat_model_start` | `ThinkingEvent` | Agent 开始推理 |
| `on_chat_model_stream` | `TokenStreamEvent`（可选） | 流式 token 输出 |
| `on_tool_start` | `ToolStartEvent` | 工具开始执行 |
| `on_tool_end` | `ToolEndEvent` | 工具执行完成 |
| `on_tool_error` | `ToolErrorEvent` | 工具执行失败 |
| `on_chat_model_end`（无 tool_calls） | `DoneEvent` | 最终答案完成（含 `usage_metadata`） |

**Token 来源**：
- 优先：`AIMessage.usage_metadata`（OpenAI 原生返回 `{"input_tokens": N, "output_tokens": N, "total_tokens": N}`）
- 备选：`AIMessage.response_metadata["token_usage"]`
- 无数据时：按 `1.5 字符 = 1 token` 估算

```python
import time
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage

class DeepSearchEventHandler(AsyncCallbackHandler):
    """基于 LangChain AsyncCallbackHandler 的事件处理器。"""

    def __init__(self, on_event=None):
        self.on_event = on_event
        self.start_time = 0

    async def on_chat_model_start(self, serialized, prompts, **kwargs):
        await self._emit({"type": "thinking", "message": "Thinking..."})

    async def on_chat_model_end(self, response: AIMessage, **kwargs):
        if not response.tool_calls:
            usage = getattr(response, "usage_metadata", None)
            if not usage and "token_usage" in response.response_metadata:
                usage = response.response_metadata["token_usage"]
            
            await self._emit({
                "type": "done",
                "answer": response.content,
                "total_time_ms": int((time.time() - self.start_time) * 1000),
                "token_usage": usage,
            })

    async def on_tool_start(self, serialized, input_str, **kwargs):
        await self._emit({
            "type": "tool_start",
            "tool": serialized.get("name", ""),
            "args": input_str,
        })

    async def on_tool_end(self, output, **kwargs):
        await self._emit({
            "type": "tool_end",
            "tool": output.get("name", ""),
            "result": str(output.get("content", ""))[:200],
        })

    async def on_tool_error(self, error, **kwargs):
        await self._emit({
            "type": "tool_error",
            "tool": kwargs.get("name", ""),
            "error": str(error),
        })

    async def _emit(self, event: dict):
        if self.on_event:
            await self.on_event(event)


class AgentRunner:
    """Agent 运行器，桥接 LangChain astream_events 到 DeepSearch 事件流。"""

    def __init__(self, agent, query: str):
        self.agent = agent
        self.query = query

    async def run_stream(self, on_event):
        """运行 Agent 并产出事件流。"""
        handler = DeepSearchEventHandler(on_event=on_event)
        
        await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": self.query}]},
            config={"callbacks": [handler]},
        )
```

### 4.3 Middleware 实现

**设计原则**：DeepSearch 全部使用 LangChain 1.0 内置的 Middleware，不实现自定义中间件。这确保了与 LangChain 生态的兼容性，减少维护成本。

#### 4.3.1 SummarizationMiddleware

使用 fast model 对长对话历史进行 LLM 级别的摘要压缩，保留关键信息同时大幅减少 token 消耗。

```python
from langchain.agents.middleware import SummarizationMiddleware

# 当上下文超过 100K token 时，使用 fast model 进行摘要压缩
middleware = SummarizationMiddleware(
    model=ChatOpenAI(model="gpt-5-mini"),  # fast model
    threshold=100_000,  # 触发压缩的 token 阈值
)
```

#### 4.3.2 ContextEditingMiddleware

内置的 `ContextEditingMiddleware` 使用 `ClearToolUsesEdit` 策略，当 token 超过阈值时自动清除旧的工具结果，与 Anthropic 的 `clear_tool_uses_20250919` 行为一致。这是比 SummarizationMiddleware 更轻量级的清理方式。

```python
from langchain.agents.middleware import ContextEditingMiddleware

# 当输入 token 超过 80K 时清除旧工具结果（轻量级清理，不调用 LLM）
middleware = ContextEditingMiddleware(threshold=80_000)
```

#### 4.3.3 HumanInTheLoopMiddleware

内置的人工审批中间件，支持对特定工具或所有工具设置审批拦截。用户可以在 CLI 或 Web UI 中审批/拒绝工具调用。

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

# 对写操作工具启用审批，只读工具无需审批
middleware = HumanInTheLoopMiddleware(
    interrupt_on={"write_file": True, "edit_file": True},
)
```

#### 4.3.4 ToolCallLimitMiddleware

内置的工具调用次数限制中间件，防止 Agent 对同一工具过度调用。支持运行级和线程级计数。

```python
from langchain.agents.middleware import ToolCallLimitMiddleware

# 每个工具最多调用 3 次（单次运行）
middleware = ToolCallLimitMiddleware(
    max_calls_per_tool=3,
    scope="run",  # "run" | "thread"
)
```

#### 4.3.5 ModelCallLimitMiddleware

内置的模型调用次数限制，防止 Agent 进入无限循环。当模型调用次数超过限制时，强制终止 Agent 循环。

```python
from langchain.agents.middleware import ModelCallLimitMiddleware

# 最多 10 次模型调用（等同于 max_iterations）
middleware = ModelCallLimitMiddleware(
    max_calls=10,
)
```

#### 4.3.6 ModelFallbackMiddleware

内置的模型回退中间件。当主模型调用失败（API 错误、超时等）时，自动切换到备用模型列表中的下一个模型。

```python
from langchain.agents.middleware import ModelFallbackMiddleware

# 主模型失败时依次回退到备用模型
middleware = ModelFallbackMiddleware(
    fallbacks=[
        ChatOpenAI(model="gpt-5-mini"),
        ChatAnthropic(model="claude-sonnet-4-20250514"),
    ],
)
```

#### 4.3.7 ToolRetryMiddleware

内置的工具重试中间件。当工具执行失败（网络错误、解析错误等）时，自动重试指定次数，并可选择性注入错误反馈给 Agent。

```python
from langchain.agents.middleware import ToolRetryMiddleware

# 工具失败时最多重试 2 次
middleware = ToolRetryMiddleware(
    max_retries=2,
)
```

#### 4.3.8 ModelRetryMiddleware

内置的模型调用重试中间件。当模型 API 调用失败时自动重试，支持指数退避策略。

```python
from langchain.agents.middleware import ModelRetryMiddleware

# 模型调用失败时最多重试 2 次
middleware = ModelRetryMiddleware(
    max_retries=2,
)
```

#### 4.3.9 FilesystemMiddleware（Memory）

内置的 `FilesystemMiddleware` 替代了自定义的 `MemoryMiddleware`。它自动将对话历史持久化到文件系统，支持跨会话的记忆恢复。

```python
from langchain.agents.middleware import FilesystemMiddleware

# 自动将对话持久化到指定目录
middleware = FilesystemMiddleware(
    memory_dir=".deepsearch/memory",
)
```

**记忆召回**：通过 `dynamic_prompt` 装饰器在每次模型调用前注入记忆上下文：

```python
from langchain.agents.middleware import dynamic_prompt

@dynamic_prompt
def inject_memory(state, prompt):
    """从文件系统记忆注入上下文。"""
    memory = load_recent_memories(limit=5)
    if memory:
        prompt.messages.insert(0, {
            "role": "system",
            "content": f"## Memory Context\n{memory}",
        })
    return prompt
```

#### 4.3.10 PIIMiddleware（可选）

可选的 PII（个人身份信息）检测中间件。自动检测和脱敏敏感信息，防止泄露。

```python
from langchain.agents.middleware import PIIMiddleware

# 自动检测并脱敏 PII 信息
middleware = PIIMiddleware(mode="redact")  # "redact" | "warn" | "block"
```

#### 4.3.12 其他可选中间件

```python
from langchain.agents.middleware import ToDoListMiddleware, LLMToolSelectorMiddleware

# 任务列表 - Agent 自动维护 TODO 清单，跟踪进度
todo_middleware = ToDoListMiddleware()

# 动态工具选择 - 根据上下文智能筛选可用工具
selector_middleware = LLMToolSelectorMiddleware()
```

### 4.4 Tool 系统

#### 4.4.1 工具注册

[`src/tools/registry.py`](src/tools/registry.py)

```python
from langchain_core.tools import BaseTool
from deepsearch.tools import web_search, web_fetch, filesystem, skill
from deepsearch.config import ToolConfig

def get_core_tools(config: ToolConfig) -> list[BaseTool]:
    """获取核心工具列表。"""
    tools = [
        web_search.tool,      # web_search
        web_fetch.tool,       # web_fetch
        filesystem.read_file, # read_file
        filesystem.write_file,# write_file
        skill.tool,           # skill
    ]
    
    # Memory 工具（如果启用）
    if config.memory_enabled:
        from deepsearch.memory import memory_search_tool
        tools.append(memory_search_tool)
    
    return tools
```

#### 4.4.2 Web Search Tool

```python
from langchain_core.tools import tool
from langchain_tavily import TavilySearchResults

@tool
async def web_search(query: str) -> str:
    """Search the web for current information on any topic."""
    search_tool = TavilySearchResults(max_results=5)
    results = await search_tool.ainvoke({"query": query})
    return format_search_results(results)
```

#### 4.4.3 Web Fetch Tool

```python
import httpx
from langchain_core.tools import tool

@tool
async def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL as markdown."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return extract_markdown(response.text)
```

### 4.5 Memory 系统

#### 4.5.1 整体架构

```
MemoryManager (单例)
    │
    ├── MemoryStore          # 文件层（MEMORY.md + 每日文件）
    ├── MemoryDatabase       # SQLite（chunks + FTS5 + 向量）
    └── MemoryIndexer        # 分块索引 + 文件监听
    
搜索管道:
    query → 向量召回 + 关键词召回 → 加权合并 → 时间衰减 → MMR → Top-K
```

#### 4.5.2 MemoryDatabase

使用 SQLite + `sqlite-vec` 扩展存储向量嵌入，使用 FTS5 做全文索引。

```python
import sqlite3
import sqlite_vec
import numpy as np

class MemoryDatabase:
    """SQLite 向量数据库。"""
    
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self._create_tables()
    
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE,
                embedding BLOB,
                updated_at INTEGER
            );
            
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content, chunk_id UNINDEXED
            );
        """)
    
    def search_vector(self, query_embedding: list[float], k: int) -> list[dict]:
        """向量搜索（余弦相似度）。"""
        # 使用 sqlite-vec 的向量搜索
        ...
    
    def search_keyword(self, query: str, k: int) -> list[dict]:
        """关键词搜索（FTS5 BM25）。"""
        cursor = self.conn.execute(
            "SELECT chunk_id, rank FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            [query, k]
        )
        return [{"chunk_id": row[0], "score": 1 / (1 + max(0, row[1]))} for row in cursor]
```

#### 4.5.3 混合搜索管道

```python
async def hybrid_search(
    db: MemoryDatabase,
    query: str,
    embedding_client,
    max_results: int = 6,
    vector_weight: float = 0.7,
    text_weight: float = 0.3,
) -> list[MemorySearchResult]:
    """混合搜索：向量 + 关键词 + 时间衰减 + MMR。"""
    
    # 1. 并行召回
    query_embedding = await embed_query(embedding_client, query)
    vector_results = db.search_vector(query_embedding, k=max_results * 4)
    keyword_results = db.search_keyword(query, k=max_results * 4)
    
    # 2. 加权合并
    merged = weighted_merge(vector_results, keyword_results, vector_weight, text_weight)
    
    # 3. 时间衰减
    decayed = apply_temporal_decay(merged, half_life_days=30)
    
    # 4. MMR 重排序
    reranked = apply_mmr(decayed, lambda_=0.7)
    
    # 5. Top-K
    return reranked[:max_results]
```

### 4.6 Skill 系统

#### 4.6.1 SKILL.md 格式

```yaml
---
name: dcf-valuation
description: Performs discounted cash flow (DCF) valuation analysis...
---

# DCF Valuation Skill

## Step 1: Gather Financial Data
...
```

#### 4.6.2 Skill 工具

```python
from langchain_core.tools import tool
from deepsearch.skills.registry import get_skill

@tool
async def skill(skill: str, args: str = "") -> str:
    """Execute a skill to get specialized instructions."""
    skill_def = get_skill(skill)
    if not skill_def:
        available = list_skills()
        return f"Skill '{skill}' not found. Available: {', '.join(available)}"
    
    return f"## Skill: {skill_def.name}\n\n{skill_def.instructions}"
```

---

## 5. API 设计

### 5.1 FastAPI 路由

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/query` | 提交查询，返回流式事件（SSE） |
| GET | `/api/health` | 健康检查 |
| GET | `/api/memory/search` | 搜索记忆 |
| POST | `/api/memory` | 更新记忆 |

### 5.2 SSE 事件格式

```
event: thinking
data: {"type": "thinking", "message": "Searching for financial data..."}

event: tool_start
data: {"type": "tool_start", "tool": "web_search", "args": {"query": "AAPL revenue"}}

event: tool_end
data: {"type": "tool_end", "tool": "web_search", "result": "...", "duration": 1234}

event: done
data: {"type": "done", "answer": "...", "iterations": 5, "totalTime": 12345}
```

### 5.3 API 请求/响应模型

```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    model: str = "openai:gpt-5"
    max_iterations: int = 10
    memory_enabled: bool = True

class QueryEvent(BaseModel):
    type: str
    data: dict
```

---

## 6. CLI 设计

### 6.1 交互流程

```
┌─────────────────────────────────────┐
│  Dexter - Deep Financial Research   │
│                                     │
│  Model: gpt-5  |  Memory: ON        │
├─────────────────────────────────────┤
│                                     │
│  > What is the current P/E of AAPL? │
│                                     │
│  ⠋ Thinking...                      │
│  ✓ web_search("AAPL P/E ratio")     │
│  ✓ web_fetch("https://...")         │
│                                     │
│  Answer: AAPL's current P/E is...   │
│                                     │
├─────────────────────────────────────┤
│  [?] Enter query...                 │
└─────────────────────────────────────┘
```

---

## 7. 配置系统

### 7.1 环境变量 (.env)

```bash
# LLM
OPENAI_API_KEY=sk-...

# Memory
MEMORY_EMBEDDING_PROVIDER=auto

# Search
TAVILY_API_KEY=tvly-...
EXASEARCH_API_KEY=...
```

### 7.2 配置文件 (.deepsearch/config.yaml)

```yaml
agent:
  model: "openai:gpt-5"
  fast_model: "openai:gpt-5-mini"
  max_iterations: 10
  compact_threshold: 100000

memory:
  enabled: true
  embedding_provider: auto
  chunk_tokens: 400
  chunk_overlap: 80
  max_results: 6
  vector_weight: 0.7
  text_weight: 0.3
  temporal_decay:
    enabled: true
    half_life_days: 30
  mmr:
    enabled: true
    lambda: 0.7

tools:
  web_search_provider: tavily  # tavily | exa
```

---

## 8. 依赖配置

### 8.1 pyproject.toml

```toml
[project]
name = "deepsearch"
version = "0.1.0"
description = "Deep financial research agent"
requires-python = ">=3.12"
dependencies = [
    "langchain>=1.0",
    "langgraph>=1.0",
    "langchain-openai>=0.3",
    "langchain-tavily>=0.1",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.28",
    "beautifulsoup4>=4.12",
    "rich>=13.0",
    "fastapi>=0.115",
    "sse-starlette>=2.0",
    "uvicorn>=0.34",
    "pyyaml>=6.0",
    "watchdog>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.9",
]
cli = [
    "textual>=1.0",
]

[project.scripts]
deepsearch = "deepsearch.cli.main:main"
deepsearch-serve = "deepsearch.cli.main:serve"
```

---

## 9. 错误处理

### 9.1 策略

| 错误类型 | 处理方式 |
|----------|----------|
| LLM API 超时/失败 | 重试 2 次，失败后返回用户友好错误 |
| 上下文溢出 | 自动触发 Microcompact，重试 2 次 |
| 工具调用失败 | 返回错误消息给 Agent，计入工具计数 |
| Memory 不可用 | 降级为无记忆模式，记录警告 |
| Embedding API 不可用 | 回退到纯关键词搜索 |

### 9.2 错误事件

```python
@dataclass
class ErrorEvent:
    type: str = "error"
    code: str  # 'api_error' | 'context_overflow' | 'tool_error' | ...
    message: str
    recoverable: bool
```

---

## 10. 测试策略

### 10.1 测试层级

| 层级 | 范围 | 工具 |
|------|------|------|
| 单元测试 | 单个函数/类 | pytest |
| 集成测试 | Middleware 链、工具执行 | pytest + mock LLM |
| E2E 测试 | 完整 Agent 循环 | pytest + cassette 录制 |

### 10.2 关键测试用例

- [ ] Agent 循环正确终止（无 tool_calls）
- [ ] Microcompact 在阈值时触发清理
- [ ] Memory flush 在接近压缩阈值时触发
- [ ] ToolLimitMiddleware 在超过限制时注入警告
- [ ] 混合搜索返回正确结果（向量 + 关键词）
- [ ] 时间衰减对每日记忆文件生效
- [ ] MMR 重排序增加结果多样性
- [ ] SSE 事件流正确格式
- [ ] CLI 审批流程正常工作

---

## 11. 实现顺序

### Phase 1: 基础框架 (Day 1-2)

1. 项目初始化（pyproject.toml、目录结构）
2. 配置系统（环境变量 + YAML）
3. 工具注册框架
4. 3 个核心工具：web_search, web_fetch, read_file

### Phase 2: Agent 核心 (Day 3-4)

5. `create_deepsearch_agent` 工厂函数（使用内置中间件）
6. Agent Runner（事件桥接）
7. 内置中间件配置：ContextEditingMiddleware、ToolCallLimitMiddleware

### Phase 3: Memory 系统 (Day 5-6)

9. MemoryStore（文件层）
10. MemoryDatabase（SQLite 向量库）
11. MemoryIndexer（分块索引）
12. HybridSearch（向量 + 关键词 + MMR + 衰减）
13. MemoryMiddleware

### Phase 4: API + CLI (Day 7-8)

14. FastAPI 服务 + SSE
15. CLI TUI（Rich）
16. 审批流程

### Phase 5: Skills + 完善 (Day 9-10)

17. Skill 系统（SKILL.md 加载）
18. 内置 Skill（DCF）
19. 错误处理完善
20. 测试覆盖
