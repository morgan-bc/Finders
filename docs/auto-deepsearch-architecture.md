# Auto DeepSearch 架构分析文档

> 项目：Dexter — 基于 TypeScript + LangChain 的 CLI 深度金融研究 AI Agent
> 分析日期：2026-05-23

---

## 目录

1. [整体架构概览](#1-整体架构概览)
2. [Agent 架构](#2-agent-架构)
3. [Memory 实现](#3-memory-实现)
4. [Tools 体系](#4-tools-体系)
5. [Skills 体系](#5-skills-体系)
6. [上下文管理](#6-上下文管理)
7. [事件系统](#7-事件系统)
8. [关键设计模式](#8-关键设计模式)

---

## 1. 整体架构概览

Dexter 是一个迭代式 ReAct Agent，核心循环位于 [`src/agent/agent.ts`](file:///d:/Github/dexter-main/src/agent/agent.ts)。整体架构如下：

```
用户查询
  │
  ▼
┌─────────────────────────────────────────┐
│           Agent.run() 循环               │
│                                         │
│  SystemPrompt + History + Query         │
│         │                               │
│         ▼                               │
│    ┌──────────┐                         │
│    │  LLM 调用 │ ← 流式 + 回退阻塞       │
│    └──────────┘                         │
│         │                               │
│    有 tool_calls?                        │
│    ├─ 否 → 直接回答 → done              │
│    └─ 是 → 并发执行工具                  │
│         │                               │
│         ▼                               │
│    ToolMessages 注入消息数组             │
│         │                               │
│         ▼                               │
│    上下文阈值管理 (microcompact/compaction│
│    /memory flush)                        │
│         │                               │
│         ▼                               │
│    下一轮迭代 (max 10 轮)                │
└─────────────────────────────────────────┘
  │
  ▼
最终答案 (DoneEvent)
```

技术栈：
- **运行时**：Bun (TypeScript ESM)
- **LLM 框架**：LangChain.js
- **UI**：Ink (React for CLI)
- **多 Provider**：OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama, Moonshot, DeepSeek

---

## 2. Agent 架构

### 2.1 核心类 `Agent`

[`src/agent/agent.ts`](file:///d:/Github/dexter-main/src/agent/agent.ts) 是 Agent 的核心实现。

**创建流程**：
```typescript
const agent = await Agent.create({
  model: 'gpt-5.5',
  maxIterations: 10,
  memoryEnabled: true,
  signal: abortSignal,
});
```

`Agent.create()` 静态方法负责：
1. 根据 model 名称加载工具列表 (`getTools(model)`)
2. 构建工具并发映射 (`getToolConcurrencyMap(model)`)
3. 加载 SOUL.md 和 RULES.md 身份/规则文档
4. 加载 Memory 上下文（如果启用）
5. 组装完整的 System Prompt

### 2.2 Agent 循环

`agent.run(query)` 是一个 AsyncGenerator，逐轮产出事件：

```typescript
async *run(query: string, inMemoryHistory?: InMemoryChatHistory): AsyncGenerator<AgentEvent>
```

每轮迭代的关键步骤：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | Microcompact | 每轮轻量清理旧 ToolMessage 内容 |
| 2 | Strip Old Thinking | 清除旧 AI 消息的 reasoning 文本（保留最近 2 条） |
| 3 | LLM 调用 | 流式调用，失败回退到阻塞调用 |
| 4 | 检测 tool_calls | 无 tool_calls → 直接回答 |
| 5 | 执行工具 | 并发执行安全工具，串行执行需审批工具 |
| 6 | 结果截断 | 大结果持久化到磁盘，注入预览 |
| 7 | 预算控制 | 每轮 ToolMessage 总量限制 |
| 8 | 上下文管理 | 超过阈值时触发 memory flush / compaction |
| 9 | 工具使用警告 | 接近调用限制时注入警告 |
| 10 | 队列排空 | 处理用户在 Agent 运行期间发送的后续消息 |

### 2.3 LLM 调用策略

[`src/model/llm.ts`](file:///d:/Github/dexter-main/src/model/llm.ts) 实现了多 Provider 抽象：

- **Prefix 路由**：根据 model 名称前缀自动选择 Provider（`claude-` → Anthropic, `gemini-` → Google, `deepseek-` → DeepSeek 等）
- **流式优先**：先尝试流式调用，失败后回退到阻塞调用
- **Fast Model**：compaction 等辅助任务自动使用 Provider 的 fast model（如 `claude-sonnet-4-20250514` → fast model）

### 2.4 RunContext

[`src/agent/run-context.ts`](file:///d:/Github/dexter-main/src/agent/run-context.ts) 封装了单次查询的可变状态：

```typescript
interface RunContext {
  readonly query: string;
  readonly scratchpad: Scratchpad;
  readonly tokenCounter: TokenCounter;
  readonly startTime: number;
  iteration: number;
  lastApiInputTokens: number;
}
```

### 2.5 Scratchpad

[`src/agent/scratchpad.ts`](file:///d:/Github/dexter-main/src/agent/scratchpad.ts) 是 Agent 工作的单一真相源：

- **JSONL 格式持久化**：每条记录追加写入 `.dexter/scratchpad/` 目录
- **工具调用计数**：每个工具每查询最多 3 次（软限制，仅警告不阻止）
- **查询相似度检测**：防止重试循环（Jaccard 相似度 > 0.7 时警告）
- **上下文清除标记**：Anthropic 风格，旧结果被标记为 `[cleared from context]` 而非删除
- **Skill 去重**：记录已执行的 skill，防止重复调用

---

## 3. Memory 实现

Memory 系统是 Dexter 的持久化记忆层，支持跨会话回忆用户偏好、目标和历史决策。

### 3.1 整体架构

```
┌──────────────────────────────────────────────────┐
│                  MemoryManager                     │
│  (单例, 懒加载初始化)                              │
│                                                    │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Store   │  │ Database │  │     Indexer      │ │
│  │ (文件层) │  │ (SQLite) │  │ (分块+索引+监听)  │ │
│  └─────────┘  └──────────┘  └──────────────────┘ │
│                      │                            │
│              ┌───────┴────────┐                   │
│              │   HybridSearch  │                   │
│              │ (向量 + 关键词)  │                   │
│              └───────┬────────┘                   │
│                      │                            │
│           ┌──────────┼──────────┐                 │
│           ▼          ▼          ▼                 │
│      Temporal     MMR       结果返回              │
│      Decay      重排序                            │
└──────────────────────────────────────────────────┘
```

### 3.2 文件存储层 — MemoryStore

[`src/memory/store.ts`](file:///d:/Github/dexter-main/src/memory/store.ts)

**存储结构**：
```
.dexter/memory/
├── MEMORY.md              # 长期记忆（evergreen，不衰减）
├── 2026-05-23.md          # 每日记忆（有时间衰减）
├── 2026-05-22.md
└── ...
```

**核心功能**：
- 文件的 CRUD 操作（append, edit, delete）
- 路径安全检查（防止目录穿越）
- Session 上下文加载（加载 MEMORY.md + 当日 + 昨日文件，限制 token 预算）

### 3.3 数据库层 — MemoryDatabase

[`src/memory/database.ts`](file:///d:/Github/dexter-main/src/memory/database.ts)

使用 SQLite（优先 `bun:sqlite`，回退 `better-sqlite3`）存储：

| 表 | 用途 |
|----|------|
| `chunks` | 存储分块内容、哈希、向量嵌入 |
| `chunks_fts` | FTS5 全文索引（关键词搜索） |
| `embedding_cache` | 嵌入向量缓存（避免重复调用 embedding API） |
| `meta` | 元数据（如 provider fingerprint） |

**向量存储**：向量以 `Float32Array` 二进制 BLOB 存储，使用余弦相似度计算。

### 3.4 分块器 — Chunker

[`src/memory/chunker.ts`](file:///d:/Github/dexter-main/src/memory/chunker.ts)

- 按段落分割文本
- 默认配置：400 token 块大小，80 token 重叠
- SHA-256 哈希去重
- 每个块记录文件路径、起止行号

### 3.5 索引器 — Indexer

[`src/memory/indexer.ts`](file:///d:/Github/dexter-main/src/memory/indexer.ts)

**核心职责**：
1. **文件监听**：使用 `fs.watch` 监听 memory 目录变化，1500ms 防抖同步
2. **Session 监听**：同时监听聊天历史文件变化
3. **嵌入生成**：对未缓存的块调用 embedding API
4. **Upsert**：基于 content_hash 的幂等更新

**嵌入 Provider**（[`src/memory/embeddings.ts`](file:///d:/Github/dexter-main/src/memory/embeddings.ts)）：
- 支持 OpenAI (`text-embedding-3-small`), Gemini (`gemini-embedding-001`), Ollama (`nomic-embed-text`)
- `auto` 模式：按 OpenAI → Gemini → Ollama 顺序自动检测可用 API Key
- 批量处理：64 条/批，15s 超时

### 3.6 混合搜索 — HybridSearch

[`src/memory/search.ts`](file:///d:/Github/dexter-main/src/memory/search.ts)

**五阶段搜索管道**：

```
阶段 1: 向量 + 关键词并行召回
  ├── 向量搜索: cosine similarity (需要 embedding client)
  └── 关键词搜索: FTS5 BM25 (精确 AND 查询)
  └── 加权合并: vectorWeight=0.7, textWeight=0.3

阶段 2: 加载完整详情

阶段 3: 时间衰减重排序
  └── 每日记忆文件按 30 天半衰期衰减
  └── MEMORY.md 为 evergreen，不衰减

阶段 4: MMR 重排序
  └── λ=0.7，平衡相关性与多样性
  └── Jaccard 相似度计算

阶段 5: 截取 Top-K (默认 6 条)
```

### 3.7 时间衰减 — TemporalDecay

[`src/memory/temporal-decay.ts`](file:///d:/Github/dexter-main/src/memory/temporal-decay.ts)

- **半衰期**：30 天（可配置）
- **衰减公式**：`score * exp(-λ * ageInDays)`，其中 `λ = ln(2) / halfLifeDays`
- **Evergreen 豁免**：`MEMORY.md` 和非日期命名的文件不衰减
- **Session 块**：使用 `updatedAt` 时间戳

### 3.8 MMR 重排序

[`src/memory/mmr.ts`](file:///d:/Github/dexter-main/src/memory/mmr.ts)

基于 Carbonell & Goldstein (1998) 的 MMR 算法：

```
MMR_score = λ * relevance - (1-λ) * max_similarity_to_selected
```

- `λ=0.7`：偏向相关性
- 使用 Jaccard 相似度计算内容重叠
- 预分词缓存提升性能

### 3.9 Memory Flush

[`src/memory/flush.ts`](file:///d:/Github/dexter-main/src/memory/flush.ts)

**触发时机**：上下文 token 数达到阈值（默认 100,000）时

**流程**：
1. LLM 分析当前工具结果和用户查询
2. 提取持久化事实（用户偏好、财务目标、风险承受能力等）
3. 写入当日记忆文件（如 `2026-05-23.md`）
4. 如果无内容可存储，返回特殊 token `NO_MEMORY_TO_FLUSH`

**Prompt 重点**：
- 提取用户财务目标、风险偏好、投资组合决策
- 提取生活事件（工作变动、购房等）
- 不存储临时工具输出或市场数据

### 3.10 Memory 工具

三个 Memory 相关工具：

| 工具 | 功能 | 需审批 |
|------|------|--------|
| `memory_search` | 混合搜索记忆和对话记录 | 否 |
| `memory_get` | 按行范围读取记忆文件 | 否 |
| `memory_update` | 添加/编辑/删除记忆条目 | 否 |

### 3.11 配置

通过 `.dexter/settings.json` 的 `memory` 字段配置：

```json
{
  "memory": {
    "enabled": true,
    "embeddingProvider": "auto",
    "maxSessionContextTokens": 2000,
    "chunkTokens": 400,
    "chunkOverlapTokens": 80,
    "maxResults": 6,
    "minScore": 0.1,
    "vectorWeight": 0.7,
    "textWeight": 0.3,
    "temporalDecay": { "enabled": true, "halfLifeDays": 30 },
    "mmr": { "enabled": true, "lambda": 0.7 },
    "indexSessions": true
  }
}
```

---

## 4. Tools 体系

### 4.1 工具注册表

[`src/tools/registry.ts`](file:///d:/Github/dexter-main/src/tools/registry.ts)

工具通过 `RegisteredTool` 接口注册，包含：

```typescript
interface RegisteredTool {
  name: string;
  tool: StructuredToolInterface;
  description: string;        // 完整描述（注入 system prompt）
  compactDescription: string; // 1-2 句精简描述
  concurrencySafe: boolean;   // 是否可并发执行
}
```

### 4.2 工具列表

| 工具 | 类别 | 并发安全 | 依赖 |
|------|------|----------|------|
| `get_financials` | 金融 | ✅ | `FINANCIAL_DATASETS_API_KEY` |
| `get_market_data` | 金融 | ✅ | `FINANCIAL_DATASETS_API_KEY` |
| `read_filings` | 金融 | ✅ | `FINANCIAL_DATASETS_API_KEY` |
| `stock_screener` | 金融 | ✅ | `FINANCIAL_DATASETS_API_KEY` |
| `web_fetch` | 网页 | ✅ | 无 |
| `browser` | 浏览器 | ✅ | Playwright |
| `web_search` | 搜索 | ✅ | Exa/Perplexity/Tavily/LangSearch API Key |
| `x_search` | 社交 | ✅ | `X_BEARER_TOKEN` |
| `read_file` | 文件系统 | ✅ | 无 |
| `write_file` | 文件系统 | ❌ | 需用户审批 |
| `edit_file` | 文件系统 | ❌ | 需用户审批 |
| `heartbeat` | 系统 | ✅ | 无 |
| `cron` | 系统 | ✅ | 无 |
| `memory_search` | 记忆 | ✅ | 无 |
| `memory_get` | 记忆 | ✅ | 无 |
| `memory_update` | 记忆 | ❌ | 无 |
| `skill` | 技能 | ❌ | 有可用 skills 时注册 |

### 4.3 工具执行器

[`src/agent/tool-executor.ts`](file:///d:/Github/dexter-main/src/agent/tool-executor.ts)

**并发策略**：
1. 将 tool_calls 按 `concurrencySafe` 标记分组
2. 连续的安全工具合并为并发批次（最大并发度 10）
3. 非安全工具串行执行

**审批流程**：
- `write_file` 和 `edit_file` 需要用户审批
- 支持 `allow-once`（单次）和 `allow-session`（会话级）两种审批
- 拒绝则立即终止 Agent 本轮

**进度通道**：
- 工具可通过 `onProgress` 回调发送中间进度消息
- 适用于长时间运行的工具（如 browser 操作）

### 4.4 工具描述注入

工具描述通过 `buildCompactToolDescriptions()` 注入 system prompt：

```
## Available Tools

- **get_financials**: Financial statements and metrics...
- **get_market_data**: Stock/crypto prices, company news...
- **read_filings**: SEC filings (10-K, 10-Q, 8-K)...
...
```

### 4.5 大结果处理

工具结果过大时（超过大小上限）：
1. 结果持久化到磁盘文件
2. 在 ToolMessage 中注入预览 + 文件路径
3. Agent 可通过 `read_file` 按需读取完整内容

### 4.6 每轮预算控制

每轮 ToolMessage 总量受预算限制，超出时截断最旧的结果。

---

## 5. Skills 体系

### 5.1 SKILL.md 格式

Skills 是 `SKILL.md` 文件，包含 YAML frontmatter 和 Markdown 正文：

```yaml
---
name: dcf-valuation
description: Performs discounted cash flow (DCF) valuation analysis...
---
```

```markdown
# DCF Valuation Skill

## Workflow Checklist
...

## Step 1: Gather Financial Data
...
```

### 5.2 技能发现

[`src/skills/registry.ts`](file:///d:/Github/dexter-main/src/skills/registry.ts)

**扫描目录**（按优先级）：
1. `src/skills/` — 内置 skills
2. `.dexter/skills/` — 项目级 skills

**去重策略**：同名 skill 后扫描的覆盖先扫描的。

### 5.3 内置 Skills

| Skill | 文件 | 描述 |
|-------|------|------|
| `dcf-valuation` | [`src/skills/dcf/SKILL.md`](file:///d:/Github/dexter-main/src/skills/dcf/SKILL.md) | DCF 估值分析，8 步工作流 |
| `x-research` | [`src/skills/x-research/SKILL.md`](file:///d:/Github/dexter-main/src/skills/x-research/SKILL.md) | X/Twitter 情绪研究 |

**DCF Skill 工作流**：
1. 收集财务数据（现金流、指标、资产负债表、价格）
2. 计算 FCF 增长率（CAGR，上限 15%）
3. 估算 WACC（基于行业基准）
4. 预测未来现金流（5 年 + 终值，Gordon Growth 2.5%）
5. 计算现值和每股公允价值
6. 敏感性分析（3×3 矩阵）
7. 结果验证（EV 偏差 < 30%，终值占比 50-80%）
8. 输出结果

### 5.4 Skill 工具

[`src/tools/skill.ts`](file:///d:/Github/dexter-main/src/tools/skill.ts)

**调用流程**：
1. LLM 根据 query 匹配 skill 描述
2. 调用 `skill` 工具，传入 skill 名称和可选参数
3. 加载 SKILL.md 正文（指令）
4. 解析相对路径链接为绝对路径（如 `sector-wacc.md`）
5. 返回指令供 Agent 执行

**去重**：Scratchpad 记录已执行的 skill，每查询仅执行一次。

### 5.5 System Prompt 注入

Skills 的元数据（名称 + 描述）在启动时注入 system prompt：

```
## Available Skills

- **dcf-valuation**: Performs discounted cash flow...
- **x-research**: X/Twitter public sentiment research...

## Skill Usage Policy

- Check if available skills can help...
- When a skill is relevant, invoke it IMMEDIATELY...
```

---

## 6. 上下文管理

Dexter 使用三层上下文管理策略，从轻量到重量：

### 6.1 Microcompact（每轮轻量清理）

[`src/agent/microcompact.ts`](file:///d:/Github/dexter-main/src/agent/microcompact.ts)

**触发条件**（满足任一）：
- 可清理的 ToolMessage 数量 > 8
- 可清理的 ToolMessage 总 token > 80,000

**清理策略**：
- 保留最近 4 条 ToolMessage
- 清除更旧的（替换为 `[Old tool result content cleared]`）
- 仅清理只读工具的结果

### 6.2 上下文溢出处理

当 LLM 返回 context overflow 错误时：
- 最多重试 2 次
- 每次保留最近 3 轮对话（AI + ToolMessage）
- 清除更早的轮次

### 6.3 Memory Flush + Compaction（完整压缩）

[`src/agent/compact.ts`](file:///d:/Github/dexter-main/src/agent/compact.ts)

**触发条件**：上下文 token 数超过模型阈值

**阈值计算**：
```
effectiveWindow = contextWindow - 20,000 (输出预留)
compactThreshold = effectiveWindow - 13,000 (缓冲)
```

例如 GPT-5.5（假设 200K 上下文）：
- effectiveWindow = 180,000
- compactThreshold = 167,000

**Compaction 流程**：
1. **Memory Flush**：LLM 提取持久化事实写入记忆
2. **LLM 摘要**：使用 fast model 将所有工具结果压缩为结构化摘要
3. **消息替换**：用摘要替换原始工具结果
4. **失败回退**：连续 3 次失败后停止尝试

**Compaction Prompt 结构**：
- 要求 LLM 先输出 `<analysis>` 思考过程
- 然后输出 `<summary>` 结构化摘要
- 包含 9 个部分：原始查询、关键概念、数据检索、错误、分析进度、数值数据、待获取数据、当前状态、下一步

**失败处理**：
- 最多连续失败 3 次
- 失败后回退到简单清除（保留最近 5 条工具结果）

### 6.4 Thinking 内容清理

每轮 LLM 调用前，清除旧 AI 消息的 reasoning 文本：
- 保留最近 2 条 AI 消息的完整内容
- 更早的 AI 消息仅保留 `tool_calls` 结构（清空 `content`）

---

## 7. 事件系统

Agent 通过 AsyncGenerator 产出类型化事件，支持实时 UI 更新：

| 事件类型 | 用途 |
|----------|------|
| `thinking` | Agent 正在思考（LLM 输出 reasoning） |
| `tool_start` | 工具开始执行 |
| `tool_end` | 工具执行成功 |
| `tool_error` | 工具执行失败 |
| `tool_progress` | 工具中间进度 |
| `tool_approval` | 工具审批请求 |
| `tool_denied` | 工具被用户拒绝 |
| `tool_limit` | 工具调用次数警告 |
| `stream_progress` | LLM 流式输出进度 |
| `microcompact` | 轻量清理完成 |
| `compaction` | 完整压缩生命周期 |
| `context_cleared` | 上下文溢出清除 |
| `memory_flush` | 记忆刷新生成 |
| `memory_recalled` | 记忆加载完成 |
| `queue_drain` | 用户后续消息注入 |
| `done` | 查询完成 |

---

## 8. 关键设计模式

### 8.1 增长式消息数组

与传统的"每轮重建消息"不同，Dexter 使用增长式消息数组：
- SystemMessage + History + Query 作为初始消息
- 每轮追加 AIMessage 和 ToolMessage
- 通过 microcompact/compaction 控制增长

### 8.2 并发工具执行

```
LLM 返回: [tool_call_1, tool_call_2, tool_call_3]
                │           │           │
         concurrent?   concurrent?   concurrent?
                │           │           │
           ┌────┴────┐      │           │
           │  Batch  │◄─────┘           │
           │ (并行)   │                  │
           └────┬────┘                  │
                │                  serial (串行)
                ▼                       │
           [result_1, result_2]         │
                                        ▼
                                   result_3
```

### 8.3 流式 + 回退

```
streamLlmWithMessages()
    │
    ├─ 成功 → 逐 chunk 产出 StreamProgressEvent
    │
    └─ 失败 → callLlmWithMessages() (阻塞)
```

### 8.4 工具结果持久化

```
工具结果 > 大小上限?
    ├─ 是 → 写入 .dexter/results/ 文件
    │        ToolMessage = 预览 + 文件路径
    │
    └─ 否 → 直接放入 ToolMessage
```

### 8.5 多 Provider 路由

```
model name: "claude-sonnet-4-20250514"
    │
    ▼
resolveProvider() → prefix "claude-" → Anthropic
    │
    ▼
ChatAnthropic({ model: "claude-sonnet-4-20250514", ... })
```

### 8.6 记忆系统集成

```
Agent.create()
    │
    ├── MemoryManager.get() → 单例初始化
    │       │
    │       ├── Store: 确保目录存在
    │       ├── EmbeddingClient: 自动检测 Provider
    │       ├── Database: 打开 SQLite
    │       └── Indexer: 开始文件监听
    │
    ├── listFiles() → 获取记忆文件列表
    ├── loadSessionContext() → 加载到 system prompt
    │
    └── run() 中:
            ├── memory_search 工具 → hybridSearch
            └── 上下文超阈值 → memory flush
```

---

## 附录：关键文件索引

| 文件 | 职责 |
|------|------|
| [`src/agent/agent.ts`](file:///d:/Github/dexter-main/src/agent/agent.ts) | Agent 核心循环 |
| [`src/agent/scratchpad.ts`](file:///d:/Github/dexter-main/src/agent/scratchpad.ts) | 工作记录与工具计数 |
| [`src/agent/prompts.ts`](file:///d:/Github/dexter-main/src/agent/prompts.ts) | System Prompt 构建 |
| [`src/agent/compact.ts`](file:///d:/Github/dexter-main/src/agent/compact.ts) | LLM 上下文压缩 |
| [`src/agent/microcompact.ts`](file:///d:/Github/dexter-main/src/agent/microcompact.ts) | 轻量上下文清理 |
| [`src/agent/tool-executor.ts`](file:///d:/Github/dexter-main/src/agent/tool-executor.ts) | 工具执行与并发 |
| [`src/agent/types.ts`](file:///d:/Github/dexter-main/src/agent/types.ts) | 类型定义 |
| [`src/agent/run-context.ts`](file:///d:/Github/dexter-main/src/agent/run-context.ts) | 单次查询状态 |
| [`src/memory/index.ts`](file:///d:/Github/dexter-main/src/memory/index.ts) | MemoryManager 入口 |
| [`src/memory/store.ts`](file:///d:/Github/dexter-main/src/memory/store.ts) | 文件存储层 |
| [`src/memory/database.ts`](file:///d:/Github/dexter-main/src/memory/database.ts) | SQLite 数据库层 |
| [`src/memory/indexer.ts`](file:///d:/Github/dexter-main/src/memory/indexer.ts) | 分块索引与监听 |
| [`src/memory/search.ts`](file:///d:/Github/dexter-main/src/memory/search.ts) | 混合搜索管道 |
| [`src/memory/embeddings.ts`](file:///d:/Github/dexter-main/src/memory/embeddings.ts) | Embedding Provider |
| [`src/memory/chunker.ts`](file:///d:/Github/dexter-main/src/memory/chunker.ts) | 文本分块 |
| [`src/memory/temporal-decay.ts`](file:///d:/Github/dexter-main/src/memory/temporal-decay.ts) | 时间衰减 |
| [`src/memory/mmr.ts`](file:///d:/Github/dexter-main/src/memory/mmr.ts) | MMR 重排序 |
| [`src/memory/flush.ts`](file:///d:/Github/dexter-main/src/memory/flush.ts) | 记忆刷新生成 |
| [`src/tools/registry.ts`](file:///d:/Github/dexter-main/src/tools/registry.ts) | 工具注册表 |
| [`src/tools/skill.ts`](file:///d:/Github/dexter-main/src/tools/skill.ts) | Skill 工具 |
| [`src/skills/registry.ts`](file:///d:/Github/dexter-main/src/skills/registry.ts) | Skill 发现 |
| [`src/skills/loader.ts`](file:///d:/Github/dexter-main/src/skills/loader.ts) | Skill 加载 |
| [`src/model/llm.ts`](file:///d:/Github/dexter-main/src/model/llm.ts) | 多 Provider LLM 抽象 |
| [`src/utils/tokens.ts`](file:///d:/Github/dexter-main/src/utils/tokens.ts) | Token 估算与阈值 |
