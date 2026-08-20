# Finders - 金融深度研究 Agent

Finders 是一个基于 **Python + LangChain 1.0 + LangGraph** 构建的金融深度研究 Agent。它采用**编排者（Orchestrator）**模式：将复杂问题拆解为子任务，通过 `task_tool` 委派给专门的**子 Agent（Subagent）**，协调并行执行，并综合各方结果生成基于证据的完整研究报告。

## 功能特性

- **编排者式 Agent** —— 主 Agent 负责规划、委派、协调与综合；研究任务由子 Agent 完成
- **内置子 Agent** —— `general-purpose` 与 `deep-research`，各自拥有独立的系统提示、工具白/黑名单、模型与轮次预算
- **富终端界面** —— 流式 Markdown 回答（Answer 面板内渲染）、实时工具调用行（`Tool: <name> (args)`）、"Thinking..." 加载动画
- **持久化会话** —— 每次对话通过 `langgraph-checkpoint-sqlite`（WAL 模式）写入 SQLite，可随时恢复或回看历史会话
- **会话管理** —— `/session` 交互式选择器，支持键盘导航
- **技能系统** —— 可插拔的 Markdown 技能加载到 Agent 上下文中（深度研究方法论、公司基本面、数据分析）
- **完整工具集** —— 网页搜索/抓取、文件系统操作、代码执行、记忆检索、子 Agent 委派
- **FastAPI + SSE 服务** —— 通过 HTTP 以流式事件暴露 Agent

## 架构

```
用户查询
   │
   ▼
┌────────────────────────── 主 Agent（编排者） ──────────────────────────┐
│  中间件流水线：                                                         │
│   SkillsMiddleware → DynamicContextMiddleware → TodoListMiddleware      │
│   → SummarizationMiddleware → ContextEditingMiddleware → ToolRetryMiddleware│
│   → ModelRetryMiddleware → [MemoryMiddleware]                            │
│                                                                          │
│  工具：web_search, web_fetch, read_file, write_file, edit_file,          │
│        list_dir, glob, grep, execute, task_tool, [memory_search_tool]    │
└───────────────┬──────────────────────────────────────────┬────────────────┘
                │ task_tool（委派）                          │ 直接调用工具
                ▼                                           ▼
  ┌─────────────────────────┐                 ┌─────────────────────────┐
  │ 子 Agent                 │                 │ 技能 / 记忆              │
  │  • general-purpose       │                 │  • deep-research        │
  │  • deep-research         │                 │  • company-fundamentals │
  └─────────────────────────┘                 │  • data-analyzer        │
                                              └─────────────────────────┘
```

### 中间件

| 中间件 | 作用 |
| --- | --- |
| `SkillsMiddleware` | 将 Markdown 技能（项目 + 用户）加载到上下文中 |
| `DynamicContextMiddleware` | 管理动态上下文窗口 |
| `TodoListMiddleware` | 将复杂任务拆解为 TODO 清单 |
| `SummarizationMiddleware` | 当 token 超过阈值时压缩对话 |
| `ContextEditingMiddleware` | 允许上下文裁剪 |
| `ToolRetryMiddleware` | 工具调用失败重试（2 次） |
| `ModelRetryMiddleware` | 模型调用失败重试（3 次） |
| `MemoryMiddleware` | 可选记忆刷新/召回（按配置启用） |

### 内置子 Agent

| 子 Agent | 说明 |
| --- | --- |
| `deep-research` | 遵循四阶段方法论进行系统性多角度网络研究（广泛探索 → 深入挖掘 → 多样性与验证 → 综合检查），最多 1000 轮 |
| `general-purpose` | 通用委派目标，处理各类子任务 |

## 快速开始

```bash
# 1. 安装（可编辑模式，含开发依赖）
pip install -e ".[dev]"

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key（见下方「配置」）

# 3. 运行 CLI
finders
```

## 配置（`.env`）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_BASE` | 是 | OpenAI 兼容的 API 地址（如 DeepSeek） |
| `LLM_API_KEY` | 是 | LLM API Key |
| `BASE_MODEL` | 否 | 默认模型（默认 `deepseek-v4-flash`） |
| `FAST_MODEL` | 否 | 快速模型（用于压缩等辅助任务） |
| `TAVILY_API_KEY` | 否 | 网页搜索服务 Key |
| `TUSHARE_TOKEN` | 否 | Tushare 金融数据 Token |
| `JINA_WEB_FETCH_BASE` | 否 | Jina Reader 地址（`https://r.jina.ai`；中国大陆可用 `https://r.jinaai.cn`） |
| `FINDERS_WORKSPACE` | 否 | 沙箱/工作区根目录（默认 `~/.finders/workspace`） |

其余运行时设置（模型、`recursion_limit`、压缩阈值、记忆、工具并发）见 `src/finders/utils/config.py`。

## CLI 使用

```bash
finders
```

交互式命令：

| 命令 | 说明 |
| --- | --- |
| `>`（任意问题） | 发起查询，回答以 Markdown 流式输出 |
| `/session` | 打开会话管理器：`↑/↓` 选择，`Enter` 载入，`d` 删除，`q`/`Esc` 退出 |
| `/model <名称>` | 切换当前模型 |
| `/quit` `/exit` `/q` | 退出 |

会话数据存储在 `$FINDERS_WORKSPACE/sessions/chat.db`。载入历史会话时，会以与实时对话一致的渲染方式回放（用户/助手消息用 Markdown，工具调用仅展示参数、不展示执行结果）。

## API 服务

```bash
python -m uvicorn finders.api.app:create_app --factory
```

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/health` | GET | 健康检查 |
| `/api/query` | POST | 运行查询，返回 SSE 事件流 |

`POST /api/query` 请求体：

```json
{
  "query": "深度研究一下中国平安的基本数据",
  "model": null,
  "fast_model": null,
  "max_iterations": 10,
  "memory_enabled": true
}
```

SSE 事件类型：`thinking`、`tool_start`、`tool_end`、`tool_error`、`answer`。

## 项目结构

```
src/finders/
├── agents/          # Agent 工厂、系统提示、草稿板
├── api/             # FastAPI 应用、路由（SSE）、模型
├── cli/             # 终端界面（tui.py）+ 入口点（main.py）
├── memory/          # 记忆分块、索引、检索
├── middlewares/     # DynamicContext、Memory
├── sandbox/         # 沙箱化执行
├── skills/          # 技能加载 + SkillsMiddleware
├── subagents/       # 子 Agent 配置、注册、执行器、内置实现
├── tools/           # 工具注册与实现
└── utils/           # 配置、路径、检查点（会话）、token
skills/              # Markdown 技能（deep-research、company-fundamentals、data-analyzer）
```

## 开发

```bash
ruff check src/       # Lint 检查
pytest tests/ -v      # 运行测试
```

## 注意事项

- 主 Agent 是**编排者**——复杂研究一律通过 `task_tool` 委派给子 Agent，自身不做研究。
- 简单/事实性问题应只调用一次 `web_search`；无依赖的工具调用应在同一轮内并行发起。
- `astream_events` 调用需传入 `config={"recursion_limit": ...}`（默认 100），以避免 `GraphRecursionError`。
