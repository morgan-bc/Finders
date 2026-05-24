# Python Finders 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 使用 Python + LangChain 1.0 + LangGraph 构建 Finds 后端，支持 CLI 和 FastAPI 双入口

**Architecture:** 参考 TypeScript Dexter 架构，使用 `create_agent` + Middleware 模式实现迭代式 ReAct Agent。核心 Agent 逻辑独立，CLI 和 FastAPI 共享同一 Agent 实例。

**Tech Stack:** LangChain >= 1.0, LangGraph >= 1.0, FastAPI, Rich, SQLite FTS5, Pydantic

***

## Phase 1: 项目基础

### Task 1: 项目初始化

**Files:**

- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/README.md`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "finders"
version = "0.1.0"
description = "Deep financial research agent"
requires-python = ">=3.12"
dependencies = [
    "langchain>=1.0",
    "langchain-community>=0.3",
    "langchain-core>=1.0",
    "langchain-text-splitters>=1.0",
    "langchain-openai>=0.3",
    "langchain-tavily>=0.1",
    "langgraph>=1.0",
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
    "markdownify>=0.13",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.9",
]

[project.scripts]
finders = "finders.cli.main:main"
finders-serve = "finders.cli.main:serve"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Step 2: 创建 .env.example**

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# Search API Keys (at least one required)
TAVILY_API_KEY=tvly-...
EXASEARCH_API_KEY=...

# Memory (optional, defaults to auto-detect)
MEMORY_EMBEDDING_PROVIDER=auto
```

**Step 3: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
.ruff_cache/
.finders/
```

**Step 4: 创建 README.md**

````markdown
# Finds

Deep financial research agent built with LangChain 1.0 and LangGraph.

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API keys

# CLI
finders

# API Server
finders-serve
````

````

**Step 5: 创建目录结构**

```bash
mkdir -p backend/src/finders/{agent,middleware,tools,skills,memory,prompts/templates,api,cli,utils}
mkdir -p backend/tests
mkdir -p backend/skills/dcf
touch backend/src/finders/__init__.py
touch backend/src/finders/{agent,middleware,tools,skills,memory,prompts,api,cli,utils}/__init__.py
````

**Step 6: 验证项目结构**

Run: `find backend/src/finders -type f -name "*.py" | sort`
Expected: All `__init__.py` files present

**Step 7: Commit**

```bash
cd backend
git add -A
git commit -m "chore: initialize project structure"
```

***

### Task 2: 配置系统

**Files:**

- Create: `backend/src/finders/utils/paths.py`
- Create: `backend/src/finders/utils/config.py`
- Test: `backend/tests/test_config.py`

**Step 1: 创建路径管理**

```python
# backend/src/finders/utils/paths.py
import os
from pathlib import Path


def get_finders_dir() -> Path:
    """获取 .finders 目录路径。"""
    return Path(os.environ.get("FINDS_DIR", Path.home() / ".finders"))


def finders_path(*parts: str) -> Path:
    """构建 .finders 子路径。"""
    path = get_finders_dir() / Path(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)
    return path
```

**Step 2: 创建配置模型**

```python
# backend/src/finders/utils/config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional


class AgentConfig(BaseModel):
    """Agent 运行时配置。"""
    model: str = Field(default="openai:gpt-5", description="LLM 模型")
    fast_model: str = Field(default="openai:gpt-5-mini", description="快速模型（用于压缩等辅助任务）")
    max_iterations: int = Field(default=10, ge=1, le=50)
    compact_threshold: int = Field(default=100_000, description="触发压缩的 token 阈值")


class MemoryConfig(BaseModel):
    """Memory 系统配置。"""
    enabled: bool = True
    chunk_tokens: int = Field(default=400, ge=100)
    chunk_overlap: int = Field(default=80, ge=0)
    max_results: int = Field(default=6, ge=1)
    min_score: float = Field(default=0.1, ge=0, le=1)
    half_life_days: float = Field(default=30, gt=0)
    mmr_lambda: float = Field(default=0.7, ge=0, le=1)


class ToolConfig(BaseModel):
    """工具配置。"""
    web_search_provider: str = Field(default="tavily", description="tavily | exa")
    max_concurrency: int = Field(default=10, ge=1)
    max_calls_per_tool: int = Field(default=3, ge=1)


class Settings(BaseSettings):
    """全局设置（从环境变量 + YAML 加载）。"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # LLM
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Search
    tavily_api_key: Optional[str] = None
    exasearch_api_key: Optional[str] = None

    # Sub-configs
    agent: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)


def get_settings() -> Settings:
    """获取全局设置（单例）。"""
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings()
    return get_settings._instance
```

**Step 3: 编写测试**

```python
# backend/tests/test_config.py
import pytest
from finders.utils.config import Settings, AgentConfig, MemoryConfig


def test_default_settings():
    settings = Settings()
    assert settings.agent.model == "openai:gpt-5"
    assert settings.agent.max_iterations == 10
    assert settings.memory.enabled is True
    assert settings.memory.mmr_lambda == 0.7


def test_agent_config_validation():
    with pytest.raises(Exception):
        AgentConfig(max_iterations=0)

    with pytest.raises(Exception):
        MemoryConfig(chunk_tokens=50)
```

**Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/utils/paths.py src/utils/config.py tests/test_config.py
git commit -m "feat: add config system with pydantic settings"
```

***

### Task 3: Token 估算工具

**Files:**

- Create: `backend/src/finders/utils/tokens.py`
- Test: `backend/tests/test_tokens.py`

**Step 1: 实现 Token 估算**

```python
# backend/src/finders/utils/tokens.py
"""Token 估算工具。优先使用 AIMessage.usage_metadata，无数据时按 1.5 字符 = 1 token 估算。"""

CHARS_PER_TOKEN = 1.5


def estimate_tokens(text: str) -> int:
    """使用 1.5 字符/token 估算文本的 token 数。"""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def get_token_count_from_message(message) -> int:
    """从 AIMessage.usage_metadata 获取 token 数（OpenAI 原生返回）。"""
    usage = getattr(message, "usage_metadata", None) or getattr(message, "response_metadata", {}).get("token_usage")
    if usage:
        return usage.get("total_tokens", usage.get("total_tokens", 0))
    # 回退到字符估算
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return estimate_tokens(content)
    return 0


def get_effective_context_window(model: str) -> int:
    """获取模型有效上下文窗口（扣除输出预留）。"""
    windows = {
        "gpt-5": 200_000,
        "gpt-4": 128_000,
    }

    base_window = 128_000  # 默认
    for key, window in windows.items():
        if key in model.lower():
            base_window = window
            break

    # 预留 20K 输出
    return base_window - 20_000


def get_compact_threshold(model: str) -> int:
    """获取自动压缩阈值。"""
    effective = get_effective_context_window(model)
    return effective - 13_000  # 13K 缓冲
```

**Step 2: 编写测试**

```python
# backend/tests/test_tokens.py
from unittest.mock import MagicMock
from finders.utils.tokens import estimate_tokens, get_compact_threshold, get_token_count_from_message


def test_estimate_tokens_basic():
    tokens = estimate_tokens("Hello world")
    assert tokens > 0


def test_estimate_tokens_ratio():
    # 1.5 字符/token: "Hello world" = 11 chars → ~7 tokens
    tokens = estimate_tokens("Hello world")
    assert tokens == int(11 / 1.5)


def test_estimate_tokens_empty():
    tokens = estimate_tokens("")
    assert tokens >= 1


def test_estimate_tokens_longer_text():
    text = "The quick brown fox jumps over the lazy dog. " * 10
    tokens = estimate_tokens(text)
    assert tokens > 20


def test_get_token_count_from_message_with_usage():
    msg = MagicMock()
    msg.usage_metadata = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    assert get_token_count_from_message(msg) == 30


def test_get_token_count_from_message_response_metadata():
    msg = MagicMock()
    msg.usage_metadata = None
    msg.response_metadata = {"token_usage": {"total_tokens": 50}}
    msg.content = ""
    assert get_token_count_from_message(msg) == 50


def test_get_token_count_from_message_fallback():
    msg = MagicMock()
    msg.usage_metadata = None
    msg.response_metadata = {}
    msg.content = "Hello world"
    tokens = get_token_count_from_message(msg)
    assert tokens == estimate_tokens("Hello world")


def test_compact_threshold_gpt5():
    threshold = get_compact_threshold("openai:gpt-5")
    assert threshold == 200_000 - 20_000 - 13_000


def test_compact_threshold_default():
    threshold = get_compact_threshold("unknown-model")
    assert threshold == 128_000 - 20_000 - 13_000
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_tokens.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/utils/tokens.py tests/test_tokens.py
git commit -m "feat: add token estimation utilities (1.5 chars/token + usage_metadata)"
```

***

### Task 4: 事件处理（LangChain Callback）

**Files:**

- Create: `backend/src/finders/utils/callbacks.py`
- Test: `backend/tests/test_callbacks.py`

**Step 1: 实现 AsyncCallbackHandler**

使用 LangChain 内置的 `AsyncCallbackHandler` 来捕获 LLM 和工具事件，替代自定义事件类型。

```python
# backend/src/finders/utils/callbacks.py
"""Agent 回调处理器。继承 LangChain AsyncCallbackHandler，将 LLM 事件转发到 UI。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult


class FindsCallbackHandler(AsyncCallbackHandler):
    """LangChain 异步回调处理器，将 Agent 事件通过回调函数转发给 UI 层。"""

    def __init__(
        self,
        on_thinking: Callable[[str], Any] | None = None,
        on_tool_start: Callable[[str, dict], Any] | None = None,
        on_tool_end: Callable[[str, str, int], Any] | None = None,
        on_tool_error: Callable[[str, str], Any] | None = None,
        on_answer: Callable[[str, dict | None], Any] | None = None,
    ) -> None:
        self.on_thinking = on_thinking
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_tool_error = on_tool_error
        self.on_answer = on_answer
        self._start_times: dict[str, float] = {}
        self._tool_call_counter = 0

    async def on_chat_model_start(self, serialized: dict[str, Any], messages: list[list[BaseMessage]], **kwargs: Any) -> None:
        """LLM 开始生成（thinking 阶段）。"""
        if self.on_thinking:
            self.on_thinking("Thinking...")

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM 生成结束。"""
        pass  # 单个 LLM 调用结束，不触发 UI 事件

    async def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """工具开始执行。"""
        tool_name = serialized.get("name", "unknown")
        self._start_times[tool_name] = time.time()
        self._tool_call_counter += 1

        if self.on_tool_start:
            # Parse input as dict if possible
            try:
                import json
                args = json.loads(input_str) if input_str else {}
            except (json.JSONDecodeError, TypeError):
                args = {"input": input_str}
            self.on_tool_start(tool_name, args)

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具执行完成。"""
        tool_name = kwargs.get("name", "unknown")
        duration_ms = int((time.time() - self._start_times.get(tool_name, time.time())) * 1000)

        if self.on_tool_end:
            self.on_tool_end(tool_name, output[:200], duration_ms)

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """工具执行出错。"""
        tool_name = kwargs.get("name", "unknown")
        if self.on_tool_error:
            self.on_tool_error(tool_name, str(error))

    async def on_chat_model_end(self, serialized: dict[str, Any], response: LLMResult, **kwargs: Any) -> None:
        """最终回答完成。"""
        if self.on_answer and response.generations:
            answer = response.generations[0][0].text if response.generations[0] else ""
            token_usage = response.llm_output.get("token_usage") if response.llm_output else None
            self.on_answer(answer, token_usage)
```

**Step 2: 编写测试**

```python
# backend/tests/test_callbacks.py
import pytest
from unittest.mock import MagicMock
from finders.utils.callbacks import FindsCallbackHandler


def test_callback_handler_init():
    handler = FindsCallbackHandler()
    assert handler.on_thinking is None
    assert handler.on_tool_start is None


def test_callback_handler_with_callbacks():
    thinking_calls = []
    handler = FindsCallbackHandler(on_thinking=lambda msg: thinking_calls.append(msg))
    assert handler.on_thinking is not None


def test_callback_handler_all_hooks():
    hooks = {
        "on_thinking": [],
        "on_tool_start": [],
        "on_tool_end": [],
        "on_tool_error": [],
        "on_answer": [],
    }
    handler = FindsCallbackHandler(
        on_thinking=lambda m: hooks["on_thinking"].append(m),
        on_tool_start=lambda t, a: hooks["on_tool_start"].append((t, a)),
        on_tool_end=lambda t, r, d: hooks["on_tool_end"].append((t, r, d)),
        on_tool_error=lambda t, e: hooks["on_tool_error"].append((t, e)),
        on_answer=lambda a, u: hooks["on_answer"].append((a, u)),
    )
    assert all(h is not None for h in [handler.on_thinking, handler.on_tool_start, handler.on_tool_end])
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_callbacks.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/utils/callbacks.py tests/test_callbacks.py
git commit -m "feat: add LangChain AsyncCallbackHandler for agent event streaming"
```

***

## Phase 2: 工具系统

### Task 5: Web Search 工具

**Files:**

- Create: `backend/src/finders/tools/web_search.py`
- Test: `backend/tests/test_web_search.py`

**Step 1: 实现 Web Search 工具**

```python
# backend/src/finders/tools/web_search.py
from langchain_core.tools import tool


def format_search_results(results: list[dict]) -> str:
    """格式化搜索结果为 Markdown。"""
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("content", r.get("snippet", ""))
        lines.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}")
    return "\n\n".join(lines)


@tool
async def web_search(query: str) -> str:
    """Search the web for current information on any topic. Returns relevant search results with URLs and content snippets."""
    try:
        from langchain_tavily import TavilySearchResults
        search_tool = TavilySearchResults(max_results=5)
        results = await search_tool.ainvoke({"query": query})
        return format_search_results(results)
    except ImportError:
        return "Error: Tavily Search not available. Install langchain-tavily."
    except Exception as e:
        return f"Error: {e}"
```

**Step 2: 编写测试**

```python
# backend/tests/test_web_search.py
from finders.tools.web_search import format_search_results


def test_format_search_results():
    results = [
        {"title": "Test", "url": "https://example.com", "content": "Test content"}
    ]
    formatted = format_search_results(results)
    assert "**Test**" in formatted
    assert "https://example.com" in formatted


def test_format_search_results_empty():
    formatted = format_search_results([])
    assert formatted == ""
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_web_search.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/tools/web_search.py tests/test_web_search.py
git commit -m "feat: add web_search tool with Tavily"
```

***

### Task 6: Web Fetch 工具

**Files:**

- Create: `backend/src/finders/tools/web_fetch.py`
- Test: `backend/tests/test_web_fetch.py`

**Step 1: 实现 Web Fetch 工具**

```python
# backend/src/finders/tools/web_fetch.py
import httpx
from langchain_core.tools import tool
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown。"""
    return markdownify(html, heading_style="ATX", strip=["script", "style"])


def truncate_markdown(md: str, max_chars: int = 8000) -> str:
    """截断 Markdown 到指定长度。"""
    if len(md) <= max_chars:
        return md
    return md[:max_chars].rsplit("\n", 1)[0] + "\n\n... [truncated]"


@tool
async def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL as markdown. Use when you need full article text beyond headlines."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30.0
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            md = html_to_markdown(response.text)
            return truncate_markdown(md)
    except httpx.HTTPStatusError as e:
        return f"Error fetching URL: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error fetching URL: {e}"
```

**Step 2: 编写测试**

```python
# backend/tests/test_web_fetch.py
from finders.tools.web_fetch import html_to_markdown, truncate_markdown


def test_html_to_markdown():
    html = "<h1>Title</h1><p>Content</p>"
    md = html_to_markdown(html)
    assert "Title" in md
    assert "Content" in md


def test_truncate_markdown_short():
    text = "Short text"
    assert truncate_markdown(text) == "Short text"


def test_truncate_markdown_long():
    text = "x" * 10000
    result = truncate_markdown(text, max_chars=100)
    assert len(result) <= 150
    assert "[truncated]" in result
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_web_fetch.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/tools/web_fetch.py tests/test_web_fetch.py
git commit -m "feat: add web_fetch tool with HTML to markdown"
```

***

### Task 7: 文件系统工具

**Files:**

- Create: `backend/src/finders/tools/filesystem.py`
- Test: `backend/tests/test_filesystem.py`

**Step 1: 实现文件系统工具**

```python
# backend/src/finders/tools/filesystem.py
from pathlib import Path
from langchain_core.tools import tool


def safe_read(path_str: str, max_chars: int = 20000) -> str:
    """安全读取文件。"""
    path = Path(path_str)
    if not path.exists():
        return f"Error: File not found: {path_str}"
    if not path.is_file():
        return f"Error: Not a file: {path_str}"
    content = path.read_text(encoding="utf-8")
    if len(content) > max_chars:
        return content[:max_chars] + "\n\n... [truncated]"
    return content


def safe_write(path_str: str, content: str) -> str:
    """安全写入文件（需审批）。"""
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} chars to {path_str}"


@tool
async def read_file(path: str) -> str:
    """Read a local file by path. Returns file content as text."""
    return safe_read(path)


@tool
async def write_file(path: str, content: str) -> str:
    """Create or overwrite a file. Requires user approval."""
    return safe_write(path, content)
```

**Step 2: 编写测试**

```python
# backend/tests/test_filesystem.py
import pytest
from finders.tools.filesystem import safe_read, safe_write


def test_safe_read_file_not_found(tmp_path):
    result = safe_read(str(tmp_path / "nonexistent.txt"))
    assert "Error: File not found" in result


def test_safe_write_and_read(tmp_path):
    path = str(tmp_path / "test.txt")
    write_result = safe_write(path, "Hello world")
    assert "Successfully wrote" in write_result

    read_result = safe_read(path)
    assert read_result == "Hello world"


def test_safe_read_truncate(tmp_path):
    path = str(tmp_path / "large.txt")
    safe_write(path, "x" * 30000)
    result = safe_read(path, max_chars=20000)
    assert "[truncated]" in result
    assert len(result) <= 20100
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_filesystem.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/tools/filesystem.py tests/test_filesystem.py
git commit -m "feat: add read_file and write_file tools"
```

***

### Task 8: 工具注册表

**Files:**

- Create: `backend/src/finders/tools/registry.py`
- Modify: `backend/src/finders/tools/__init__.py`
- Test: `backend/tests/test_tool_registry.py`

**Step 1: 实现工具注册**

```python
# backend/src/finders/tools/registry.py
from langchain_core.tools import BaseTool
from finders.utils.config import Settings
from finders.tools.web_search import web_search
from finders.tools.web_fetch import web_fetch
from finders.tools.filesystem import read_file, write_file


CONCURRENT_TOOLS = {"web_search", "web_fetch", "read_file"}
APPROVAL_TOOLS = {"write_file"}


def get_core_tools(settings: Settings) -> list[BaseTool]:
    """获取核心工具列表。"""
    tools = [
        web_search,
        web_fetch,
        read_file,
        write_file,
    ]

    # Memory 工具（如果启用）
    if settings.memory.enabled:
        from finders.tools.memory import memory_search_tool
        tools.append(memory_search_tool)

    # Skill 工具（如果有可用 skills）
    from finders.skills.registry import has_skills
    if has_skills():
        from finders.tools.skill import skill_tool
        tools.append(skill_tool)

    return tools


def is_concurrent_safe(tool_name: str) -> bool:
    """检查工具是否可并发执行。"""
    return tool_name in CONCURRENT_TOOLS


def requires_approval(tool_name: str) -> bool:
    """检查工具是否需要用户审批。"""
    return tool_name in APPROVAL_TOOLS
```

**Step 2: 更新** __init__.py

```python
# backend/src/finders/tools/__init__.py
from finders.tools.registry import get_core_tools, is_concurrent_safe, requires_approval

__all__ = ["get_core_tools", "is_concurrent_safe", "requires_approval"]
```

**Step 3: 编写测试**

```python
# backend/tests/test_tool_registry.py
import pytest
from unittest.mock import patch
from finders.tools.registry import (
    get_core_tools,
    is_concurrent_safe,
    requires_approval,
)
from finders.utils.config import Settings


def test_concurrent_safe_tools():
    assert is_concurrent_safe("web_search") is True
    assert is_concurrent_safe("read_file") is True
    assert is_concurrent_safe("write_file") is False


def test_approval_tools():
    assert requires_approval("write_file") is True
    assert requires_approval("web_search") is False


def test_get_core_tools_basic():
    settings = Settings()
    settings.memory.enabled = False
    with patch("finders.skills.registry.has_skills", return_value=False):
        tools = get_core_tools(settings)
    assert len(tools) == 4
    tool_names = [t.name for t in tools]
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
```

**Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_tool_registry.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/tools/registry.py src/tools/__init__.py tests/test_tool_registry.py
git commit -m "feat: add tool registry with concurrency and approval metadata"
```

***

## Phase 3: Agent 核心

### Task 9: Scratchpad 工作记录

**Files:**

- Create: `backend/src/finders/agent/scratchpad.py`
- Test: `backend/tests/test_scratchpad.py`

**Step 1: 实现 Scratchpad**

```python
# backend/src/finders/agent/scratchpad.py
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from finders.utils.paths import finders_path


@dataclass
class ToolCallRecord:
    tool: str
    args: dict
    result: str


class Scratchpad:
    """Agent 工作记录。跟踪工具调用次数、查询相似度等。"""

    def __init__(self, query: str, max_calls_per_tool: int = 3):
        self.query = query
        self.max_calls_per_tool = max_calls_per_tool
        self._tool_calls: list[ToolCallRecord] = []
        self._call_counts: dict[str, int] = {}
        self._file_path = self._get_file_path()

    def _get_file_path(self) -> Path:
        """获取持久化文件路径。"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        return finders_path("scratchpad", f"{timestamp}.jsonl")

    def record_tool(self, tool: str, args: dict, result: str) -> None:
        """记录工具调用。"""
        record = ToolCallRecord(tool=tool, args=args, result=result)
        self._tool_calls.append(record)
        self._call_counts[tool] = self._call_counts.get(tool, 0) + 1
        self._persist()

    def get_call_count(self, tool: str) -> int:
        """获取工具调用次数。"""
        return self._call_counts.get(tool, 0)

    def should_warn(self, tool: str) -> bool:
        """检查是否接近调用限制。"""
        return self.get_call_count(tool) >= self.max_calls_per_tool - 1

    def is_over_limit(self, tool: str) -> bool:
        """检查是否超过调用限制。"""
        return self.get_call_count(tool) >= self.max_calls_per_tool

    def get_records(self) -> list[ToolCallRecord]:
        """获取所有工具调用记录。"""
        return self._tool_calls

    def _persist(self) -> None:
        """追加写入 JSONL。"""
        try:
            with open(self._file_path, "a", encoding="utf-8") as f:
                record = self._tool_calls[-1]
                f.write(json.dumps({
                    "tool": record.tool,
                    "args": record.args,
                    "result_preview": record.result[:500],
                    "timestamp": datetime.now().isoformat(),
                }) + "\n")
        except Exception:
            pass  # 持久化失败不阻塞执行
```

**Step 2: 编写测试**

```python
# backend/tests/test_scratchpad.py
from finders.agent.scratchpad import Scratchpad


def test_scratchpad_initial():
    scratchpad = Scratchpad("test query")
    assert scratchpad.get_call_count("web_search") == 0
    assert scratchpad.should_warn("web_search") is False


def test_scratchpad_record_and_count():
    scratchpad = Scratchpad("test query", max_calls_per_tool=3)
    scratchpad.record_tool("web_search", {"query": "test"}, "result")
    scratchpad.record_tool("web_search", {"query": "test2"}, "result2")

    assert scratchpad.get_call_count("web_search") == 2
    assert scratchpad.should_warn("web_search") is True


def test_scratchpad_over_limit():
    scratchpad = Scratchpad("test query", max_calls_per_tool=3)
    for i in range(3):
        scratchpad.record_tool("web_search", {"query": f"test{i}"}, "result")

    assert scratchpad.is_over_limit("web_search") is True


def test_scratchpad_get_records():
    scratchpad = Scratchpad("test query")
    scratchpad.record_tool("web_search", {"query": "test"}, "result")
    records = scratchpad.get_records()
    assert len(records) == 1
    assert records[0].tool == "web_search"
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_scratchpad.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/agent/scratchpad.py tests/test_scratchpad.py
git commit -m "feat: add Scratchpad for tool call tracking and persistence"
```

***

### Task 10: Agent Factory

**Files:**

- Create: `backend/src/finders/agent/factory.py`
- Test: `backend/tests/test_factory.py`

**Step 1: 实现 Agent Factory**

LangChain 1.0 提供了多个内置中间件。Agent Factory 按顺序配置所有中间件：

```python
# backend/src/finders/agent/factory.py
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,          # 内置：上下文压缩
    HumanInTheLoopMiddleware,          # 内置：人工审批
    ContextEditingMiddleware,          # 内置：上下文编辑（条件式截断）
    ToolCallLimitMiddleware,           # 内置：工具调用次数限制
    RateLimitMiddleware,               # 内置：工具调用频率限制
)
from finders.utils.config import Settings
from finders.tools.registry import get_core_tools
from finders.prompts.system import build_system_prompt


def create_finders_agent(settings: Settings):
    """创建 Finds Agent 实例。"""

    system_prompt = build_system_prompt(settings)
    tools = get_core_tools(settings)

    middleware = [
        # 1. 上下文压缩：当上下文超过阈值时，用快模型压缩旧消息
        SummarizationMiddleware(
            model=settings.agent.fast_model,
            threshold=settings.agent.compact_threshold,
        ),
        # 2. 上下文编辑：无条件截断超出 token 限制的消息
        ContextEditingMiddleware(
            threshold=settings.agent.compact_threshold,
        ),
        # 3. 工具调用限制：防止单个工具被过度调用
        ToolCallLimitMiddleware(
            max_calls=settings.tools.max_calls_per_tool,
            scope="run",  # 按运行周期计数
        ),
        # 4. 频率限制：防止工具调用过快（可选）
        RateLimitMiddleware(
            max_calls_per_minute=60,
        ),
        # 5. 人工审批：需要确认的写操作
        HumanInTheLoopMiddleware(
            interrupt_on={"write_file": True},
        ),
    ]

    return create_agent(
        model=settings.agent.model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
```

**Step 2: 编写测试（mock LLM）**

```python
# backend/tests/test_factory.py
import pytest
from unittest.mock import patch, MagicMock
from finders.utils.config import Settings
from finders.agent.factory import create_finders_agent


@patch("finders.agent.factory.create_agent")
def test_create_agent_with_middleware(mock_create):
    mock_create.return_value = MagicMock()
    settings = Settings()
    settings.memory.enabled = False

    agent = create_finders_agent(settings)

    # 验证 create_agent 被调用
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs

    # 验证 middleware 存在
    assert "middleware" in call_kwargs
    assert len(call_kwargs["middleware"]) >= 5  # Summarization + ContextEditing + ToolCallLimit + RateLimit + HITL
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_factory.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/agent/factory.py tests/test_factory.py
git commit -m "feat: add create_finders_agent factory with middleware pipeline"
```

***

### Task 11: System Prompt 构建

**Files:**

- Create: `backend/src/finders/prompts/system.py`
- Create: `backend/src/finders/prompts/templates/system.md`
- Test: `backend/tests/test_prompts.py`

**Step 1: 创建 System Prompt 模板**

```markdown
<!-- backend/src/finders/prompts/templates/system.md -->
You are Dexter, a deep financial research assistant.

Current date: {{date}}

Your output is displayed on a command line interface. Keep responses short and concise.

## Available Tools

{{tool_descriptions}}

## Tool Usage Policy

- Call tools with the full natural language query — they handle multi-parameter requests internally
- Only respond directly for conceptual definitions, stable historical facts, or conversational queries

## Behavior

- Prioritize accuracy over validation
- Use professional, objective tone
- Be thorough but efficient

## Response Format

- Keep responses brief and direct
- For non-comparative information, prefer plain text or simple lists over tables
```

**Step 2: 实现 Prompt 构建器**

```python
# backend/src/finders/prompts/system.py
from datetime import datetime
from pathlib import Path
from finders.utils.config import Settings


def _load_template() -> str:
    """加载模板文件。"""
    template_path = Path(__file__).parent / "templates" / "system.md"
    return template_path.read_text(encoding="utf-8")


def build_system_prompt(settings: Settings) -> str:
    """构建完整的 System Prompt。"""
    template = _load_template()

    tool_descriptions = _build_tool_descriptions(settings)

    return template.replace("{{date}}", datetime.now().strftime("%A, %B %d, %Y")).replace(
        "{{tool_descriptions}}", tool_descriptions
    )


def _build_tool_descriptions(settings: Settings) -> str:
    """构建工具描述列表。"""
    from finders.tools.registry import get_core_tools

    tools = get_core_tools(settings)
    lines = []
    for t in tools:
        desc = t.description or "No description."
        lines.append(f"- **{t.name}**: {desc.split(chr(10))[0]}")
    return "\n".join(lines)
```

**Step 3: 编写测试**

```python
# backend/tests/test_prompts.py
from finders.prompts.system import build_system_prompt
from finders.utils.config import Settings


def test_build_system_prompt_contains_date():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    assert "2026" in prompt  # 当前年份


def test_build_system_prompt_contains_tools():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    assert "web_search" in prompt
    assert "web_fetch" in prompt


def test_build_system_prompt_contains_behavior():
    settings = Settings()
    settings.memory.enabled = False
    prompt = build_system_prompt(settings)
    assert "Behavior" in prompt
    assert "Response Format" in prompt
```

**Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/prompts/system.py src/prompts/templates/system.md tests/test_prompts.py
git commit -m "feat: add system prompt builder with template"
```

***

## Phase 4: Middleware 配置

所有中间件均已内置于 LangChain 1.0 `langchain.agents.middleware`，无需自定义实现。

### Task 12: 配置内置中间件

在 Agent Factory（Task 10）中已完成配置。以下是各中间件的作用和配置参数：

| 中间件                        | 作用                          | 关键参数                   | 来源                            |
| -------------------------- | --------------------------- | ---------------------- | ----------------------------- |
| `SummarizationMiddleware`  | 上下文超过阈值时用快模型压缩旧消息           | `model`, `threshold`   | `langchain.agents.middleware` |
| `ContextEditingMiddleware` | 无条件截断超出 token 限制的消息         | `threshold`            | `langchain.agents.middleware` |
| `ToolCallLimitMiddleware`  | 限制单个工具最大调用次数                | `max_calls`, `scope`   | `langchain.agents.middleware` |
| `RateLimitMiddleware`      | 限制工具调用频率                    | `max_calls_per_minute` | `langchain.agents.middleware` |
| `HumanInTheLoopMiddleware` | 需要用户确认的危险操作中断               | `interrupt_on`         | `langchain.agents.middleware` |
| `ModelRetryMiddleware`     | 模型 API 调用失败自动重试             | `max_retries`          | `langchain.agents.middleware` |
| `ToolRetryMiddleware`      | 工具执行失败自动重试                  | `max_retries`          | `langchain.agents.middleware` |
| `ModelFallbackMiddleware`  | 主模型失败切换到备用模型                | `fallbacks`            | `langchain.agents.middleware` |
| `ModelCallLimitMiddleware` | 限制模型调用次数（防止无限循环）            | `max_calls`            | `langchain.agents.middleware` |
| `FilesystemMiddleware`     | 自动持久化对话到文件系统                | `memory_dir`           | `langchain.agents.middleware` |
| `ToDoListMiddleware`       | Agent 自动维护 TODO 任务清单，分解复杂任务 | —                      | `langchain.agents.middleware` |

***

### Task 13: 自定义 MemoryMiddleware（Flush + Recall）

**Files:**

- Create: `backend/src/finders/middleware/memory.py`
- Create: `backend/src/finders/prompts/templates/memory_flush.md`
- Test: `backend/tests/test_memory_middleware.py`

**设计说明：**

- `FilesystemMiddleware` 只负责底层文件存储和对话持久化，**不包含 Memory Flush/Recall 逻辑**
- 需要自定义 `MemoryMiddleware` 来实现：
  - **Memory Flush**：当上下文 token 接近压缩阈值时，用 LLM 提取关键事实写入每日记忆文件
  - **Memory Recall**：每次模型调用前，读取记忆文件并注入到系统提示

**参考原始实现：**

- Flush 触发条件：`estimatedContextTokens >= compact_threshold` 且本会话尚未 flush 过
- Flush 内容：关键事实、用户偏好、金融目标、风险偏好、投资决策
- Flush 存储：写入当日文件（如 `2026-05-23.md`），标题为 "## Pre-compaction memory flush"
- Recall 内容：列出记忆文件列表 + 加载近期会话上下文（session context）

**Step 1: 创建 Memory Flush 模板**

```markdown
<!-- backend/src/finders/prompts/templates/memory_flush.md -->
Session context is close to compaction. Summarize durable facts and user preferences worth remembering long-term.

Rules:
- Output concise markdown bullet points.
- Include durable facts, explicit user preferences, and stable decisions.
- Prioritize capturing personal financial information:
  - Financial goals (retirement targets, savings goals, income targets)
  - Risk tolerance and investment philosophy
  - Portfolio decisions and allocation changes
  - Trade history and the reasoning behind buy/sell decisions
  - Account details mentioned (brokerage, 401k, IRA specifics)
- Also capture personal context that affects financial advice:
  - Life events (job changes, home purchase, family changes)
  - Tax situation or jurisdiction
  - Time horizons and liquidity needs
- Do not include temporary tool output, market data, or stock prices.
- If nothing should be stored, reply exactly with ${MEMORY_FLUSH_TOKEN}.
```

**Step 2: 实现 Memory Flush 逻辑**

```python
# backend/src/finders/middleware/memory.py
"""MemoryMiddleware — Memory Flush + Recall 中间件。

FilesystemMiddleware 只提供底层文件存储，本中间件负责：
- before_model: Recall 记忆并注入到系统提示
- after_model: 检查是否需要 Flush（上下文接近压缩阈值时）
"""

import time
from datetime import datetime
from langchain.agents.middleware import BaseMiddleware
from langchain_core.messages import SystemMessage

MEMORY_FLUSH_TOKEN = "NO_MEMORY_TO_FLUSH"


def build_flush_prompt() -> str:
    """加载 Memory Flush 模板。"""
    from pathlib import Path
    template_path = Path(__file__).parent.parent / "prompts" / "templates" / "memory_flush.md"
    return template_path.read_text(encoding="utf-8").replace("${MEMORY_FLUSH_TOKEN}", MEMORY_FLUSH_TOKEN)


class MemoryMiddleware(BaseMiddleware):
    """Memory flush + recall 中间件。"""

    def __init__(
        self,
        memory_dir: str,
        flush_threshold: int = 140_000,
        fast_model: str | None = None,
    ):
        super().__init__()
        self.memory_dir = Path(memory_dir) / "memory"
        self.flush_threshold = flush_threshold
        self.fast_model = fast_model
        self._already_flushed = False
        self._flush_prompt = build_flush_prompt()

    def _get_today_file(self) -> str:
        """获取今日记忆文件名。"""
        return f"{datetime.now().strftime('%Y-%m-%d')}.md"

    async def _load_permanent_memories(self) -> str:
        """Recall: 读取永久记忆和近期每日记忆。"""
        parts = []

        # 1. 读取 MEMORY.md（永久记忆）
        permanent = self.memory_dir / "MEMORY.md"
        if permanent.exists():
            parts.append(f"## Long-term Memory\n{permanent.read_text(encoding='utf-8')}")

        # 2. 读取最近 3 天的每日记忆文件
        today = datetime.now()
        for i in range(3):
            day = today.replace(day=today.day - i)
            filename = f"{day.strftime('%Y-%m-%d')}.md"
            daily_file = self.memory_dir / filename
            if daily_file.exists():
                parts.append(f"## Memory from {filename.replace('.md', '')}\n{daily_file.read_text(encoding='utf-8')}")

        return "\n\n".join(parts) if parts else ""

    async def before_model(self, state) -> AgentState:
        """Recall: 注入记忆上下文到系统提示。"""
        memory_context = await self._load_permanent_memories()
        if memory_context:
            # 注入到系统提示的末尾
            messages = list(state.get("messages", []))
            if messages and isinstance(messages[0], SystemMessage):
                original_prompt = messages[0].content
                messages[0] = SystemMessage(
                    content=f"{original_prompt}\n\n## Memory Context\n{memory_context}"
                )
            state["messages"] = messages

        return state

    async def after_model(self, state) -> AgentState:
        """Flush: 检查上下文 token 数，接近阈值时提取关键事实。"""
        # 计算当前上下文 token 数
        messages = state.get("messages", [])
        total_tokens = sum(len(m.content) / 1.5 for m in messages if hasattr(m, "content") and isinstance(m.content, str))

        if self._already_flushed or total_tokens < self.flush_threshold:
            return state

        # 收集工具结果
        tool_results = self._get_tool_results(messages)
        if not tool_results:
            return state

        # 调用 LLM 提取关键事实
        flush_result = await self._run_flush(
            query=state.get("query", ""),
            tool_results=tool_results,
        )

        if flush_result["written"]:
            self._already_flushed = True

        return state

    def _get_tool_results(self, messages: list) -> str:
        """从消息中提取工具结果文本。"""
        results = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    results.append(f"Tool: {tc['name']}({tc['args']})")
            elif hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                # Tool result messages
                results.append(msg.content[:500])
        return "\n\n".join(results)

    async def _run_flush(self, query: str, tool_results: str) -> dict:
        """调用 LLM 提取关键事实并写入每日记忆文件。"""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        prompt = f"""Original user query:
{query}

Relevant retrieved context:
{tool_results or '[no tool results yet]'}

{self._flush_prompt}"""

        model = ChatOpenAI(model=self.fast_model or "gpt-5-mini")
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = (response.content or "").strip()

        if not content or content == MEMORY_FLUSH_TOKEN:
            return {"flushed": True, "written": False}

        # 写入每日记忆文件
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        daily_file = self.memory_dir / self._get_today_file()
        existing = daily_file.read_text(encoding="utf-8") if daily_file.exists() else ""
        separator = "\n\n" if existing else ""
        daily_file.write_text(
            f"{existing}{separator}## Pre-compaction memory flush\n{content}",
            encoding="utf-8",
        )

        return {"flushed": True, "written": True, "content": content}
```

**Step 3: 将 MemoryMiddleware 添加到 Agent Factory**

```python
# backend/src/finders/agent/factory.py — 在 middleware 列表中添加
from finders.middleware.memory import MemoryMiddleware

middleware = [
    # ... 其他中间件 ...
    
    # 自定义：Memory Flush + Recall
    MemoryMiddleware(
        memory_dir=str(finders_path()),
        flush_threshold=settings.agent.compact_threshold,
        fast_model=settings.agent.fast_model,
    ),
    
    # 内置：长期记忆（文件持久化）
    FilesystemMiddleware(
        memory_dir=str(finders_path()),
    ),
]
```

**Step 4: 编写测试**

```python
# backend/tests/test_memory_middleware.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from finders.middleware.memory import MemoryMiddleware, build_flush_prompt, MEMORY_FLUSH_TOKEN


@pytest.fixture
def memory_middleware(tmp_path):
    return MemoryMiddleware(
        memory_dir=str(tmp_path),
        flush_threshold=1000,
        fast_model="gpt-5-mini",
    )


def test_build_flush_prompt():
    prompt = build_flush_prompt()
    assert "durable facts" in prompt.lower()
    assert MEMORY_FLUSH_TOKEN in prompt


def test_get_today_file(memory_middleware):
    today = Path(memory_middleware._get_today_file())
    assert today.name.endswith(".md")
    assert len(today.name) == 14  # YYYY-MM-DD.md


def test_load_permanent_memories_empty(memory_middleware):
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        memory_middleware._load_permanent_memories()
    )
    assert result == ""


def test_load_permanent_memories_with_files(memory_middleware, tmp_path):
    import asyncio
    memory_dir = memory_middleware.memory_dir
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "MEMORY.md").write_text("User likes tech stocks.")
    (memory_dir / "2026-05-23.md").write_text("## Flush\nAAPL analysis done.")

    result = asyncio.get_event_loop().run_until_complete(
        memory_middleware._load_permanent_memories()
    )
    assert "Long-term Memory" in result
    assert "tech stocks" in result


def test_already_flushed_flag(memory_middleware):
    assert memory_middleware._already_flushed is False
    memory_middleware._already_flushed = True
    assert memory_middleware._already_flushed is True
```

**Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_middleware.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/middleware/memory.py src/prompts/templates/memory_flush.md tests/test_memory_middleware.py
git commit -m "feat: add custom MemoryMiddleware with flush + recall logic"
```

***

### Task 14: 配置 ToDoListMiddleware（任务分解与规划）

**Files:**

- Modify: `backend/src/finders/agent/factory.py`
- Modify: `backend/src/finders/prompts/templates/system.md`
- Test: `backend/tests/test_todo_middleware.py`

**设计说明：**

- `ToDoListMiddleware` 是 LangChain 1.0 内置中间件，用于 Agent 自动维护 TODO 任务清单
- 适用于复杂多步骤查询（如 "比较 AAPL 和 MSFT 的财务指标，并给出投资建议"）
- Agent 在接收到查询后自动分解为子任务，跟踪每个任务的完成状态
- 与 Scratchpad 工具计数配合，防止 Agent 在复杂任务中迷失方向

**Step 1: 更新 System Prompt 模板**

在 system prompt 中添加任务规划指引，帮助 LLM 更好地使用 TODO 清单：

```markdown
<!-- backend/src/finders/prompts/templates/system.md — 追加到 Behavior 部分 -->

## Task Planning

- For complex multi-step queries, break them down into clear sub-tasks before starting
- Use the TODO list to track your progress through each step
- Mark tasks as complete as you finish them
- If you realize you need additional steps, add them to your TODO list
```

**Step 2: 在 Agent Factory 中启用 ToDoListMiddleware**

```python
# backend/src/finders/agent/factory.py — 在 middleware 列表中添加
from langchain.agents.middleware import ToDoListMiddleware

middleware = [
    # 1. 任务规划：Agent 自动分解复杂查询为子任务清单
    ToDoListMiddleware(),
    
    # 2. 上下文压缩
    SummarizationMiddleware(
        model=settings.agent.fast_model,
        threshold=settings.agent.compact_threshold,
    ),
    # ... 其他中间件 ...
]
```

**Step 3: 在 System Prompt 构建器中注入 TODO 指引**

```python
# backend/src/finders/prompts/system.py — 更新 build_system_prompt
def build_system_prompt(settings: Settings) -> str:
    """构建完整的 System Prompt。"""
    template = _load_template()

    tool_descriptions = _build_tool_descriptions(settings)

    prompt = template.replace("{{date}}", datetime.now().strftime("%A, %B %d, %Y")).replace(
        "{{tool_descriptions}}", tool_descriptions
    )

    # 如果启用了 ToDoListMiddleware，添加任务规划指引
    if settings.agent.enable_todo:
        prompt += "\n\n## Task Planning\n\n- For complex multi-step queries, break them down into clear sub-tasks before starting\n- Use the TODO list to track your progress\n- Mark tasks as complete as you finish them"

    return prompt
```

**Step 4: 在配置中添加 enable\_todo 开关**

```python
# backend/src/finders/utils/config.py — 在 AgentConfig 中添加
class AgentConfig(BaseModel):
    model: str = Field(default="openai:gpt-5", description="LLM 模型")
    fast_model: str = Field(default="openai:gpt-5-mini", description="快速模型")
    max_iterations: int = Field(default=10, ge=1, le=50)
    compact_threshold: int = Field(default=100_000, description="触发压缩的 token 阈值")
    enable_todo: bool = Field(default=True, description="启用 TODO 任务清单（分解复杂任务）")
```

**Step 5: 编写测试**

```python
# backend/tests/test_todo_middleware.py
import pytest
from finders.utils.config import AgentConfig


def test_enable_todo_default():
    config = AgentConfig()
    assert config.enable_todo is True


def test_enable_todo_disabled():
    config = AgentConfig(enable_todo=False)
    assert config.enable_todo is False


def test_prompt_includes_todo_section():
    from finders.prompts.system import build_system_prompt
    from finders.utils.config import Settings

    settings = Settings()
    settings.agent.enable_todo = True
    prompt = build_system_prompt(settings)
    assert "Task Planning" in prompt
    assert "TODO list" in prompt or "TODO" in prompt


def test_prompt_excludes_todo_section():
    from finders.prompts.system import build_system_prompt
    from finders.utils.config import Settings

    settings = Settings()
    settings.agent.enable_todo = False
    prompt = build_system_prompt(settings)
    assert "Task Planning" not in prompt
```

**Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_todo_middleware.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/agent/factory.py src/prompts/templates/system.md src/prompts/system.py src/utils/config.py tests/test_todo_middleware.py
git commit -m "feat: enable ToDoListMiddleware for complex task decomposition"
```

### Task 14: Memory 类型定义 + Store

**Files:**

- Create: `backend/src/finders/memory/types.py`
- Create: `backend/src/finders/memory/store.py`
- Test: `backend/tests/test_memory_store.py`

**Step 1: 定义 Memory 类型**

```python
# backend/src/finders/memory/types.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryChunk:
    id: Optional[int] = None
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    content: str = ""
    content_hash: str = ""
    updated_at: Optional[int] = None


@dataclass
class MemorySearchResult:
    snippet: str = ""
    path: str = ""
    start_line: int = 0
    end_line: int = 0
    score: float = 0.0
```

**Step 2: 实现 Memory Store**

```python
# backend/src/finders/memory/store.py
from pathlib import Path
import re
from finders.utils.paths import finders_path, ensure_dir


MEMORY_DIRNAME = "memory"
LONG_TERM_FILE = "MEMORY.md"
DAILY_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


class MemoryStore:
    """Memory 文件存储层。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or finders_path()
        self.memory_dir = self.base_dir / MEMORY_DIRNAME
        ensure_dir(self.memory_dir)

    def get_memory_dir(self) -> Path:
        return self.memory_dir

    def read_memory_file(self, path: str) -> str:
        """读取 memory 文件。"""
        file_path = self.memory_dir / path
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def write_memory_file(self, path: str, content: str) -> None:
        """写入 memory 文件。"""
        file_path = self.memory_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def append_memory_file(self, path: str, content: str) -> None:
        """追加到 memory 文件。"""
        existing = self.read_memory_file(path)
        separator = "\n" if existing and not existing.endswith("\n") else ""
        self.write_memory_file(path, existing + separator + content)

    def list_memory_files(self) -> list[str]:
        """列出所有 memory 文件。"""
        if not self.memory_dir.exists():
            return []
        return [
            f.name
            for f in self.memory_dir.iterdir()
            if f.is_file() and (f.name == LONG_TERM_FILE or DAILY_FILE_RE.match(f.name))
        ]
```

**Step 3: 编写测试**

```python
# backend/tests/test_memory_store.py
import pytest
from pathlib import Path
from finders.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(base_dir=tmp_path)


def test_store_write_and_read(store):
    store.write_memory_file("test.md", "Hello")
    assert store.read_memory_file("test.md") == "Hello"


def test_store_append(store):
    store.append_memory_file("test.md", "Line 1")
    store.append_memory_file("test.md", "Line 2")
    content = store.read_memory_file("test.md")
    assert "Line 1" in content
    assert "Line 2" in content


def test_store_list_files(store):
    store.write_memory_file("MEMORY.md", "Long term")
    store.write_memory_file("2026-05-23.md", "Daily")
    store.write_memory_file("notes.txt", "Should not appear")

    files = store.list_memory_files()
    assert "MEMORY.md" in files
    assert "2026-05-23.md" in files
    assert "notes.txt" not in files


def test_store_read_nonexistent(store):
    assert store.read_memory_file("nonexistent.md") == ""
```

**Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_store.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/memory/types.py src/memory/store.py tests/test_memory_store.py
git commit -m "feat: add MemoryStore for file-based memory persistence"
```

***

### Task 15: Memory Chunker

**Files:**

- Create: `backend/src/finders/memory/chunker.py`
- Test: `backend/tests/test_memory_chunker.py`

**Step 1: 实现 Chunker**

```python
# backend/src/finders/memory/chunker.py
import hashlib
from finders.memory.types import MemoryChunk


def split_into_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """将文本按段落分割，返回 (start_line, end_line, content)。"""
    lines = text.split("\n")
    paragraphs = []
    start = 0

    for i, line in enumerate(lines):
        if line.strip() == "" and i > start:
            content = "\n".join(lines[start:i]).strip()
            if content:
                paragraphs.append((start + 1, i, content))
            start = i + 1

    # Last paragraph
    if start < len(lines):
        content = "\n".join(lines[start:]).strip()
        if content:
            paragraphs.append((start + 1, len(lines), content))

    return paragraphs


def chunk_memory_text(
    file_path: str,
    text: str,
    chunk_tokens: int = 400,
    overlap_tokens: int = 80,
) -> list[MemoryChunk]:
    """将 memory 文本分块。"""
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        return []

    chunk_budget = chunk_tokens * 3  # ~3 chars/token
    overlap_budget = overlap_tokens * 3

    chunks = []
    start_idx = 0

    while start_idx < len(paragraphs):
        content = ""
        start_line = paragraphs[start_idx][0]
        end_line = paragraphs[start_idx][1]
        end_idx = start_idx

        while end_idx < len(paragraphs):
            candidate = paragraphs[end_idx]
            candidate_text = f"{content}\n\n{candidate[2]}" if content else candidate[2]
            if len(candidate_text) > chunk_budget and content:
                break
            content = candidate_text
            end_line = candidate[1]
            end_idx += 1
            if len(content) >= chunk_budget:
                break

        if not content:
            break

        chunks.append(
            MemoryChunk(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
        )

        # Overlap: carry some paragraphs from previous chunk
        start_idx = max(start_idx + 1, end_idx - (overlap_budget // 50))  # ~50 chars/paragraph

    return chunks
```

**Step 2: 编写测试**

```python
# backend/tests/test_memory_chunker.py
from finders.memory.chunker import split_into_paragraphs, chunk_memory_text


def test_split_into_paragraphs():
    text = "Para 1\n\nPara 2\n\nPara 3"
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) == 3
    assert paragraphs[0][2] == "Para 1"


def test_chunk_memory_text():
    text = "Content A\n\nContent B\n\nContent C"
    chunks = chunk_memory_text("test.md", text, chunk_tokens=1000)
    assert len(chunks) >= 1
    assert chunks[0].file_path == "test.md"
    assert chunks[0].content_hash  # Non-empty


def test_chunk_empty_text():
    chunks = chunk_memory_text("test.md", "", chunk_tokens=100)
    assert len(chunks) == 0
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_chunker.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/memory/chunker.py tests/test_memory_chunker.py
git commit -m "feat: add MemoryChunker for paragraph-based text chunking"
```

***

### Task 16: Memory Database (SQLite)

**Files:**

- Create: `backend/src/finders/memory/database.py`
- Test: `backend/tests/test_memory_database.py`

**Step 1: 实现 MemoryDatabase**

```python
# backend/src/finders/memory/database.py
import sqlite3
from pathlib import Path
from finders.memory.types import MemoryChunk, MemorySearchResult


class MemoryDatabase:
    """SQLite 向量数据库（基础版：仅 FTS5，向量扩展后续添加）。"""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content, chunk_id UNINDEXED
            );
        """)

    def upsert_chunk(self, chunk: MemoryChunk) -> int:
        """插入或更新 chunk，返回 chunk ID。"""
        try:
            cursor = self.conn.execute(
                "INSERT INTO chunks (file_path, start_line, end_line, content, content_hash) VALUES (?, ?, ?, ?, ?)",
                (chunk.file_path, chunk.start_line, chunk.end_line, chunk.content, chunk.content_hash),
            )
            self.conn.execute(
                "INSERT INTO chunks_fts (content, chunk_id) VALUES (?, ?)",
                (chunk.content, cursor.lastrowid),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Hash conflict: update existing
            cursor = self.conn.execute(
                "SELECT id FROM chunks WHERE content_hash = ?", (chunk.content_hash,)
            )
            row = cursor.fetchone()
            if row:
                self.conn.execute(
                    "UPDATE chunks SET file_path=?, start_line=?, end_line=?, content=?, updated_at=strftime('%s', 'now') WHERE id=?",
                    (chunk.file_path, chunk.start_line, chunk.end_line, chunk.content, row["id"]),
                )
                self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["id"],))
                self.conn.execute(
                    "INSERT INTO chunks_fts (content, chunk_id) VALUES (?, ?)",
                    (chunk.content, row["id"]),
                )
                self.conn.commit()
                return row["id"]
            raise

    def search_keyword(self, query: str, k: int = 20) -> list[dict]:
        """关键词搜索（FTS5）。"""
        # Build FTS query with quoted tokens
        tokens = [t for t in query.split() if len(t) > 2]
        if not tokens:
            return []
        fts_query = " AND ".join(f'"{t}"' for t in tokens)

        cursor = self.conn.execute(
            "SELECT chunk_id, rank FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, k),
        )
        return [{"chunk_id": row["chunk_id"], "score": 1 / (1 + max(0, row["rank"]))} for row in cursor]

    def get_chunk(self, chunk_id: int) -> MemorySearchResult | None:
        """按 ID 获取 chunk。"""
        cursor = self.conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return MemorySearchResult(
            snippet=row["content"][:700],
            path=row["file_path"],
            start_line=row["start_line"],
            end_line=row["end_line"],
        )

    def delete_chunks_for_file(self, file_path: str) -> int:
        """删除文件的所有 chunks。"""
        cursor = self.conn.execute("SELECT id FROM chunks WHERE file_path = ?", (file_path,))
        ids = [row["id"] for row in cursor]
        for chunk_id in ids:
            self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
        self.conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path,))
        self.conn.commit()
        return len(ids)

    def list_indexed_files(self) -> list[str]:
        """列出已索引文件。"""
        cursor = self.conn.execute("SELECT DISTINCT file_path FROM chunks")
        return [row["file_path"] for row in cursor]

    def close(self):
        self.conn.close()
```

**Step 2: 编写测试**

```python
# backend/tests/test_memory_database.py
import pytest
from pathlib import Path
from finders.memory.database import MemoryDatabase
from finders.memory.types import MemoryChunk


@pytest.fixture
def db(tmp_path):
    database = MemoryDatabase(tmp_path / "test.db")
    yield database
    database.close()


def test_upsert_and_get_chunk(db):
    chunk = MemoryChunk(
        file_path="test.md", start_line=1, end_line=3, content="Test content here", content_hash="hash1"
    )
    chunk_id = db.upsert_chunk(chunk)
    assert chunk_id > 0

    result = db.get_chunk(chunk_id)
    assert result is not None
    assert result.snippet == "Test content here"


def test_search_keyword(db):
    chunk = MemoryChunk(
        file_path="test.md", start_line=1, end_line=1, content="Apple revenue growth", content_hash="h1"
    )
    db.upsert_chunk(chunk)

    results = db.search_keyword("Apple revenue", k=5)
    assert len(results) >= 1


def test_delete_chunks_for_file(db):
    for i in range(3):
        db.upsert_chunk(MemoryChunk(
            file_path="test.md", start_line=i, end_line=i, content=f"Content {i}", content_hash=f"h{i}"
        ))

    deleted = db.delete_chunks_for_file("test.md")
    assert deleted == 3


def test_upsert_duplicate_hash(db):
    chunk1 = MemoryChunk(file_path="a.md", start_line=1, end_line=1, content="Same", content_hash="same")
    chunk2 = MemoryChunk(file_path="b.md", start_line=2, end_line=2, content="Same", content_hash="same")

    id1 = db.upsert_chunk(chunk1)
    id2 = db.upsert_chunk(chunk2)
    assert id1 == id2  # Same hash, same ID
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_database.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/memory/database.py tests/test_memory_database.py
git commit -m "feat: add MemoryDatabase with SQLite FTS5"
```

***

### Task 17: Memory Indexer

**Files:**

- Create: `backend/src/finders/memory/indexer.py`
- Test: `backend/tests/test_memory_indexer.py`

**Step 1: 实现 Indexer**

```python
# backend/src/finders/memory/indexer.py
from finders.memory.store import MemoryStore
from finders.memory.database import MemoryDatabase
from finders.memory.chunker import chunk_memory_text
from finders.memory.types import MemoryChunk


class MemoryIndexer:
    """Memory 索引器：扫描文件、分块、写入数据库。"""

    def __init__(self, store: MemoryStore, db: MemoryDatabase, chunk_tokens: int = 400, overlap_tokens: int = 80):
        self.store = store
        self.db = db
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

    def sync(self, force: bool = False) -> dict:
        """同步所有 memory 文件到数据库。"""
        files = self.store.list_memory_files()

        # Clean up deleted files
        indexed_files = set(self.db.list_indexed_files())
        for known_file in indexed_files:
            if known_file not in files:
                self.db.delete_chunks_for_file(known_file)

        # Index each file
        stats = {"indexed_files": 0, "indexed_chunks": 0, "removed_chunks": 0}

        for file in files:
            if force:
                stats["removed_chunks"] += self.db.delete_chunks_for_file(file)

            text = self.store.read_memory_file(file)
            chunks = chunk_memory_text(file, text, self.chunk_tokens, self.overlap_tokens)

            for chunk in chunks:
                try:
                    self.db.upsert_chunk(chunk)
                    stats["indexed_chunks"] += 1
                except Exception:
                    pass

            if not chunks:
                stats["removed_chunks"] += self.db.delete_chunks_for_file(file)

            stats["indexed_files"] += 1

        return stats
```

**Step 2: 编写测试**

```python
# backend/tests/test_memory_indexer.py
import pytest
from pathlib import Path
from finders.memory.store import MemoryStore
from finders.memory.database import MemoryDatabase
from finders.memory.indexer import MemoryIndexer


@pytest.fixture
def indexer(tmp_path):
    store = MemoryStore(base_dir=tmp_path)
    db = MemoryDatabase(tmp_path / "test.db")
    return MemoryIndexer(store, db, chunk_tokens=200, overlap_tokens=40), db


def test_indexer_sync(indexer):
    idx, db = indexer
    idx.store.write_memory_file("MEMORY.md", "User likes tech stocks.\nRisk tolerance is high.")

    stats = idx.sync()
    assert stats["indexed_files"] >= 1
    assert stats["indexed_chunks"] >= 1

    indexed_files = db.list_indexed_files()
    assert "MEMORY.md" in indexed_files


def test_indexer_cleanup_deleted_file(indexer):
    idx, db = indexer
    idx.store.write_memory_file("old.md", "Old content")
    idx.sync()

    # Delete file
    (idx.store.get_memory_dir() / "old.md").unlink()
    stats = idx.sync()
    assert stats["removed_chunks"] >= 1

    indexed_files = db.list_indexed_files()
    assert "old.md" not in indexed_files
```

**Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_indexer.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/memory/indexer.py tests/test_memory_indexer.py
git commit -m "feat: add MemoryIndexer for file-to-database sync"
```

***

### Task 18: Memory Search Pipeline

**Files:**

- Create: `backend/src/finders/memory/search.py`
- Create: `backend/src/finders/memory/temporal_decay.py`
- Create: `backend/src/finders/memory/mmr.py`
- Test: `backend/tests/test_memory_search.py`

**Step 1: 实现 Temporal Decay**

```python
# backend/src/finders/memory/temporal_decay.py
import math
from finders.memory.types import MemorySearchResult


DAILY_FILE_RE = r"^\d{4}-\d{2}-\d{2}\.md$"


def apply_temporal_decay(results: list[MemorySearchResult], half_life_days: float = 30) -> list[MemorySearchResult]:
    """应用时间衰减。每日记忆文件衰减，MEMORY.md 不衰减。"""
    import re
    from time import time

    now = time()
    day_seconds = 86400

    decayed = []
    for r in results:
        # Check if file is a daily file
        if not re.match(DAILY_FILE_RE, r.path):
            decayed.append(r)  # Evergreen: no decay
            continue

        # Extract date from filename
        try:
            date_str = r.path.replace(".md", "")
            import datetime
            file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            age_days = (now - file_date) / day_seconds
            lam = math.log(2) / half_life_days
            multiplier = math.exp(-lam * age_days)
            r.score *= multiplier
        except (ValueError, AttributeError):
            pass
        decayed.append(r)

    return sorted(decayed, key=lambda x: x.score, reverse=True)
```

**Step 2: 实现 MMR**

```python
# backend/src/finders/memory/mmr.py
from finders.memory.types import MemorySearchResult


def tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0


def apply_mmr(results: list[MemorySearchResult], lambda_: float = 0.7) -> list[MemorySearchResult]:
    """MMR 重排序。"""
    if len(results) <= 1:
        return results

    token_cache = {i: tokenize(r.snippet) for i, r in enumerate(results)}
    selected = []
    remaining = set(range(len(results)))

    # Normalize scores
    scores = [r.score for r in results]
    max_score = max(scores) if scores else 1
    min_score = min(scores) if scores else 0
    score_range = max_score - min_score or 1

    while remaining:
        best_idx = None
        best_mmr = -float("inf")

        for idx in remaining:
            norm_score = (results[idx].score - min_score) / score_range
            max_sim = max(
                (jaccard_similarity(token_cache[idx], token_cache[s]) for s in selected),
                default=0,
            )
            mmr = lambda_ * norm_score - (1 - lambda_) * max_sim

            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    return [results[i] for i in selected]
```

**Step 3: 实现 Search Pipeline**

```python
# backend/src/finders/memory/search.py
from finders.memory.database import MemoryDatabase
from finders.memory.types import MemorySearchResult
from finders.memory.temporal_decay import apply_temporal_decay
from finders.memory.mmr import apply_mmr


def keyword_search(
    db: MemoryDatabase,
    query: str,
    max_results: int = 6,
    half_life_days: float = 30,
    mmr_lambda: float = 0.7,
) -> list[MemorySearchResult]:
    """关键词搜索：FTS5 + 时间衰减 + MMR。"""
    candidate_count = max_results * 4

    # Keyword search
    keyword_results = db.search_keyword(query, k=candidate_count)

    # Load full details
    results = []
    for kr in keyword_results:
        chunk = db.get_chunk(kr["chunk_id"])
        if chunk:
            chunk.score = kr["score"]
            results.append(chunk)

    # Temporal decay
    results = apply_temporal_decay(results, half_life_days)

    # MMR re-ranking
    results = apply_mmr(results, mmr_lambda)

    return results[:max_results]
```

**Step 4: 编写测试**

```python
# backend/tests/test_memory_search.py
import pytest
from pathlib import Path
from finders.memory.database import MemoryDatabase
from finders.memory.search import keyword_search
from finders.memory.types import MemoryChunk


@pytest.fixture
def populated_db(tmp_path):
    db = MemoryDatabase(tmp_path / "test.db")
    db.upsert_chunk(MemoryChunk(
        file_path="MEMORY.md", start_line=1, end_line=1, content="User prefers growth stocks", content_hash="h1"
    ))
    db.upsert_chunk(MemoryChunk(
        file_path="2026-05-23.md", start_line=1, end_line=1, content="AAPL revenue analysis shows strong growth", content_hash="h2"
    ))
    return db


def test_keyword_search(populated_db):
    results = keyword_search(populated_db, "AAPL revenue")
    assert len(results) >= 1
    assert "AAPL" in results[0].snippet


def test_keyword_search_no_results(populated_db):
    results = keyword_search(populated_db, "xyznonexistent")
    assert len(results) == 0
```

**Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_search.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/memory/search.py src/memory/temporal_decay.py src/memory/mmr.py tests/test_memory_search.py
git commit -m "feat: add keyword search with temporal decay and MMR"
```

***

### Task 19: Memory Manager + Search Tool

**Files:**

- Create: `backend/src/finders/memory/manager.py`
- Create: `backend/src/finders/memory/__init__.py`
- Create: `backend/src/finders/tools/memory.py`
- Test: `backend/tests/test_memory_manager.py`

**Step 1: 实现 MemoryManager**

```python
# backend/src/finders/memory/manager.py
from pathlib import Path
from finders.utils.config import MemoryConfig
from finders.memory.store import MemoryStore
from finders.memory.database import MemoryDatabase
from finders.memory.indexer import MemoryIndexer
from finders.memory.search import keyword_search
from finders.utils.paths import finders_path


class MemoryManager:
    """Memory 系统统一入口（单例）。"""

    _instance = None

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.store = MemoryStore()
        self.db = MemoryDatabase(finders_path("memory", "index.db"))
        self.indexer = MemoryIndexer(
            self.store, self.db,
            chunk_tokens=config.chunk_tokens,
            overlap_tokens=config.chunk_overlap,
        )

    @classmethod
    def get(cls, config: MemoryConfig) -> "MemoryManager":
        if cls._instance is None:
            cls._instance = cls(config)
            cls._instance.sync()
        return cls._instance

    def sync(self) -> dict:
        return self.indexer.sync()

    async def search(self, query: str, max_results: int = 6) -> list:
        self.indexer.sync()
        return keyword_search(
            self.db, query,
            max_results=max_results,
            half_life_days=self.config.half_life_days,
            mmr_lambda=self.config.mmr_lambda,
        )

    def close(self):
        self.db.close()
```

**Step 2: 创建 Memory Search Tool**

```python
# backend/src/finders/tools/memory.py
from langchain_core.tools import tool


@tool
async def memory_search(query: str) -> str:
    """Search persistent memory and past conversation transcripts. Returns relevant stored facts."""
    from finders.memory.manager import MemoryManager
    from finders.utils.config import get_settings

    settings = get_settings()
    manager = MemoryManager.get(settings.memory)
    results = await manager.search(query, max_results=settings.memory.max_results)

    if not results:
        return "No relevant memories found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. [{r.path}:{r.start_line}] {r.snippet}")
    return "\n\n".join(lines)
```

**Step 3: 更新 Memory** __init__.py

```python
# backend/src/finders/memory/__init__.py
from finders.memory.manager import MemoryManager
from finders.memory.types import MemoryChunk, MemorySearchResult

__all__ = ["MemoryManager", "MemoryChunk", "MemorySearchResult"]
```

**Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_memory_manager.py -v`
Expected: Tests pass (create basic tests)

**Step 5: Commit**

```bash
git add src/memory/manager.py src/memory/__init__.py src/tools/memory.py
git commit -m "feat: add MemoryManager and memory_search tool"
```

***

## Phase 6: Skills + 集成测试

### Task 21: Skill 系统

**Files:**

- Create: `backend/src/finders/skills/loader.py`
- Create: `backend/src/finders/skills/registry.py`
- Create: `backend/src/finders/tools/skill.py`
- Test: `backend/tests/test_skills.py`

**Step 1: 实现 Skill Loader**

```python
# backend/src/finders/skills/loader.py
import yaml
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SkillDef:
    name: str
    description: str
    path: str
    instructions: str


def load_skill(skill_path: Path) -> SkillDef | None:
    """加载单个 SKILL.md 文件。"""
    try:
        content = skill_path.read_text(encoding="utf-8")
        # Split YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1])
                instructions = parts[2].strip()
            else:
                return None
        else:
            return None

        if not meta or "name" not in meta or "description" not in meta:
            return None

        return SkillDef(
            name=meta["name"],
            description=meta["description"],
            path=str(skill_path),
            instructions=instructions,
        )
    except Exception:
        return None
```

**Step 2: 实现 Skill Registry**

```python
# backend/src/finders/skills/registry.py
from pathlib import Path
from finders.skills.loader import SkillDef, load_skill

# Skill directories to scan
SKILL_DIRS = [
    Path(__file__).parent.parent.parent / "skills",  # Built-in skills
    Path.home() / ".finders" / "skills",  # User skills
]

_skill_cache: dict[str, SkillDef] = {}


def discover_skills() -> list[SkillDef]:
    """发现所有可用 skills。"""
    if _skill_cache:
        return list(_skill_cache.values())

    for skill_dir in SKILL_DIRS:
        if not skill_dir.exists():
            continue
        for skill_file in skill_dir.rglob("SKILL.md"):
            skill = load_skill(skill_file)
            if skill:
                _skill_cache[skill.name] = skill

    return list(_skill_cache.values())


def get_skill(name: str) -> SkillDef | None:
    """按名称获取 skill。"""
    if not _skill_cache:
        discover_skills()
    return _skill_cache.get(name)


def has_skills() -> bool:
    return len(discover_skills()) > 0
```

**Step 3: 创建 Skill Tool**

```python
# backend/src/finders/tools/skill.py
from langchain_core.tools import tool


@tool
async def skill(skill: str, args: str = "") -> str:
    """Execute a skill to get specialized instructions for complex tasks."""
    from finders.skills.registry import get_skill, discover_skills

    skill_def = get_skill(skill)
    if not skill_def:
        available = ", ".join(s.name for s in discover_skills())
        return f"Skill '{skill}' not found. Available: {available or 'none'}"

    result = f"## Skill: {skill_def.name}\n\n"
    if args:
        result += f"**Arguments:** {args}\n\n"
    result += skill_def.instructions
    return result
```

**Step 4: 编写测试**

```python
# backend/tests/test_skills.py
from finders.skills.loader import load_skill
from finders.skills.registry import discover_skills, get_skill, has_skills


def test_discover_skills_empty(tmp_path):
    """Test with no skills directory."""
    skills = discover_skills()
    # Should not crash even if no skills found
    assert isinstance(skills, list)


def test_get_skill_not_found():
    assert get_skill("nonexistent_skill_xyz") is None


def test_has_skills():
    # Initial state may or may not have skills
    result = has_skills()
    assert isinstance(result, bool)
```

**Step 5: 创建内置 Skill (DCF)**

```yaml
# backend/skills/dcf/SKILL.md
---
name: dcf-valuation
description: Performs discounted cash flow (DCF) valuation analysis to estimate intrinsic value per share.
---

# DCF Valuation Skill

## Step 1: Gather Financial Data
Call get_financials for cash flow history and key metrics.

## Step 2: Calculate FCF Growth Rate
Calculate 5-year FCF CAGR from historical data.

## Step 3: Estimate Discount Rate (WACC)
Use sector-appropriate WACC range.

## Step 4: Project Future Cash Flows
Apply growth rate with decay for Years 1-5 + Terminal value.

## Step 5: Calculate Present Value
Discount all FCFs to get Enterprise Value.
```

**Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_skills.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/skills/loader.py src/skills/registry.py src/tools/skill.py tests/test_skills.py skills/dcf/SKILL.md
git commit -m "feat: add Skill system with DCF built-in skill"
```

***

### Task 22: 全链路集成测试

**Files:**

- Create: `backend/tests/test_integration.py`

**Step 1: 编写集成测试**

```python
# backend/tests/test_integration.py
"""全链路集成测试：配置 → 工厂 → 工具注册 → Memory Store → Skills。"""

import pytest
from unittest.mock import patch, MagicMock
from finders.utils.config import Settings
from finders.tools.registry import get_core_tools, is_concurrent_safe
from finders.memory.store import MemoryStore
from finders.skills.registry import has_skills


def test_full_pipeline_no_llm(tmp_path):
    """测试不依赖 LLM 的完整 pipeline。"""
    settings = Settings()
    settings.memory.enabled = False

    # 1. Tools
    with patch("finders.skills.registry.has_skills", return_value=False):
        tools = get_core_tools(settings)
    assert len(tools) >= 4

    # 2. Concurrency metadata
    assert is_concurrent_safe("web_search") is True
    assert is_concurrent_safe("write_file") is False

    # 3. Memory Store
    store = MemoryStore(base_dir=tmp_path)
    store.write_memory_file("MEMORY.md", "Test memory")
    assert store.read_memory_file("MEMORY.md") == "Test memory"

    # 4. Skills
    assert isinstance(has_skills(), bool)


def test_settings_load_from_env():
    """测试配置从环境变量加载。"""
    import os
    os.environ["OPENAI_API_KEY"] = "test_key_123"

    # Force reload
    from finders.utils.config import get_settings
    if hasattr(get_settings, "_instance"):
        delattr(get_settings, "_instance")

    settings = get_settings()
    assert settings.openai_api_key == "test_key_123"

    # Cleanup
    del os.environ["OPENAI_API_KEY"]
```

**Step 2: 运行所有测试**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 3: 运行 linting**

Run: `cd backend && python -m ruff check src/`
Expected: No errors

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add full integration test suite"
```

***

## Phase 7: API + CLI

### Task 23: FastAPI Service + SSE

**Files:**

- Create: `backend/src/finders/api/models.py`
- Create: `backend/src/finders/api/sse.py`
- Create: `backend/src/finders/api/routes.py`
- Create: `backend/src/finders/api/app.py`
- Test: `backend/tests/test_api.py`

**Step 1: 创建 API 模型**

```python
# backend/src/finders/api/models.py
from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    query: str
    model: Optional[str] = None
    max_iterations: int = 10
    memory_enabled: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
```

**Step 2: 实现 SSE**

```python
# backend/src/finders/api/sse.py
import json
from sse_starlette.sse import EventSourceResponse
from typing import AsyncIterator


async def agent_event_stream(runner) -> AsyncIterator[dict]:
    """将 Agent Runner 事件转换为 SSE 格式。"""
    async for event in runner.run_stream():
        yield {
            "event": event.type,
            "data": json.dumps({
                "type": event.type,
                **{k: v for k, v in event.__dict__.items() if k != "type"},
            }),
        }
```

**Step 3: 实现路由**

```python
# backend/src/finders/api/routes.py
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from finders.api.models import QueryRequest, HealthResponse


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.post("/query")
async def query(request: QueryRequest):
    # 返回 SSE 流
    return EventSourceResponse(agent_event_stream(get_runner(request)))


from finders.api.sse import agent_event_stream
from finders.agent.runner import AgentRunner


def get_runner(request: QueryRequest) -> AgentRunner:
    """创建 Agent Runner 实例。"""
    from finders.utils.config import get_settings
    from finders.agent.factory import create_finders_agent

    settings = get_settings()
    if request.model:
        settings.agent.model = request.model

    agent = create_finders_agent(settings)
    return AgentRunner(agent, request.query)
```

**Step 4: 创建 FastAPI 应用**

```python
# backend/src/finders/api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from finders.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Finds", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app
```

**Step 5: 编写测试**

```python
# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from finders.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
```

**Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/api/models.py src/api/sse.py src/api/routes.py src/api/app.py tests/test_api.py
git commit -m "feat: add FastAPI service with SSE streaming"
```

***

### Task 24: CLI TUI + Agent Runner

**Files:**

- Create: `backend/src/finders/agent/runner.py`
- Create: `backend/src/finders/cli/main.py`
- Create: `backend/src/finders/cli/tui.py`

***

## 总结

本计划包含 **24 个任务**，每个任务可在 2-5 分钟内完成。按顺序执行：

| Phase                  | 任务数 | 内容                                               |
| ---------------------- | --- | ------------------------------------------------ |
| Phase 1: 项目基础          | 4   | 初始化、配置、Token 估算、事件处理（Callback）                   |
| Phase 2: 工具系统          | 4   | web\_search, web\_fetch, filesystem, registry    |
| Phase 3: Agent 核心      | 3   | Scratchpad, Factory, System Prompt               |
| Phase 4: Middleware 配置 | 2   | 配置所有内置中间件 + 自定义 MemoryMiddleware（Flush + Recall） |
| Phase 5: Memory 系统     | 6   | Types, Store, Chunker, Database, Indexer, Search |
| Phase 6: Skills + 集成测试 | 2   | Skill 系统, 集成测试                                   |
| Phase 7: API + CLI     | 2   | FastAPI + SSE, CLI TUI                           |

**关键技术决策：**

- 使用 LangChain 1.0 `create_agent` + Middleware（非旧的 `create_react_agent`）
- 大部分中间件使用 LangChain 内置版本：`SummarizationMiddleware`、`ContextEditingMiddleware`、`ToolCallLimitMiddleware`、`RateLimitMiddleware`、`HumanInTheLoopMiddleware`、`FilesystemMiddleware`
- 但需要自定义实现 `MemoryMiddleware`：`FilesystemMiddleware` 只提供底层文件存储和大结果自动转存，不包含 Memory Flush 和 Memory Recall 逻辑
- 使用 `ToDoListMiddleware`（LangChain 1.0 内置）让 Agent 自动分解复杂多步骤查询为子任务清单，配合 Scratchpad 工具计数防止 Agent 迷失方向
- 使用 LangChain `AsyncCallbackHandler` 替代自定义事件类型，通过回调函数直接驱动 UI
- 依赖项增加 `langchain-core`、`langchain-community`、`langchain-text-splitters`、`langchain-tavily` 以获取完整的内置中间件和搜索能力
- Memory 使用 SQLite FTS5（后续根据实际搜索效果决定是否添加向量搜索）
- 工具结果截断防止上下文膨胀
- 每个模块都有对应的单元测试

