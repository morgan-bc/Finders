"""MemoryMiddleware — Memory Flush + Recall 中间件。

FilesystemMiddleware 只提供底层文件存储，本中间件负责：
- before_model: Recall 记忆并注入到系统提示
- after_model: 检查是否需要 Flush（上下文接近压缩阈值时）
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.middleware import Runtime
from langchain_core.messages import SystemMessage

from finders.utils.tokens import estimate_tokens

MEMORY_FLUSH_TOKEN = "NO_MEMORY_TO_FLUSH"

FLUSH_PROMPT = """Session context is close to compaction. Summarize durable facts and user preferences worth remembering long-term.

Rules:
- Output concise markdown bullet points.
- Include durable facts, explicit user preferences, and stable decisions.
- Prioritize capturing personal financial information:
  - Financial goals (retirement targets, savings goals, income targets)
  - Risk tolerance and investment philosophy
  - Portfolio decisions and allocation changes
  - Trade history and the reasoning behind buy/sell decisions
- Also capture personal context that affects financial advice:
  - Life events (job changes, home purchase, family changes)
  - Tax situation or jurisdiction
  - Time horizons and liquidity needs
- Do not include temporary tool output, market data, or stock prices.
- If nothing should be stored, reply exactly with ${MEMORY_FLUSH_TOKEN}.
"""


def _get_today_file() -> str:
    """获取今日记忆文件名。"""
    return f"{datetime.now().strftime('%Y-%m-%d')}.md"


class MemoryMiddleware(AgentMiddleware):
    """Memory flush + recall 中间件。"""

    def __init__(
        self,
        memory_dir: str,
        flush_threshold: int = 140_000,
    ):
        self.memory_dir = Path(memory_dir) / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.flush_threshold = flush_threshold
        self._already_flushed = False
        self._flush_prompt = FLUSH_PROMPT.replace("${MEMORY_FLUSH_TOKEN}", MEMORY_FLUSH_TOKEN)

    def _load_permanent_memories(self) -> str:
        """Recall: 读取永久记忆和近期每日记忆。"""
        parts = []

        # 1. 读取 MEMORY.md（永久记忆）
        permanent = self.memory_dir / "MEMORY.md"
        if permanent.exists():
            parts.append(f"## Long-term Memory\n{permanent.read_text(encoding='utf-8')}")

        # 2. 读取最近 3 天的每日记忆文件
        today = datetime.now()
        for i in range(3):
            day = today - timedelta(days=i)
            filename = f"{day.strftime('%Y-%m-%d')}.md"
            daily_file = self.memory_dir / filename
            if daily_file.exists():
                parts.append(f"## Memory from {filename.replace('.md', '')}\n{daily_file.read_text(encoding='utf-8')}")

        return "\n\n".join(parts) if parts else ""

    def before_model(self, state, runtime: Runtime) -> dict[str, Any] | None:
        """Recall: 加载记忆并注入到系统提示。"""
        memories = self._load_permanent_memories()
        if not memories:
            return None

        # Prepend memory context to the system message
        messages = list(state.get("messages", []))
        if messages and isinstance(messages[0], SystemMessage):
            original_content = messages[0].content
            if isinstance(original_content, str) and "## Memory Context" not in original_content:
                memory_prefix = f"## Memory Context\n\n{memories}\n\n---\n\n"
                messages[0] = SystemMessage(content=memory_prefix + original_content)
                return {"messages": messages}

        return None

    async def after_model(self, state, runtime: Runtime) -> dict[str, Any] | None:
        """Flush: 检查上下文 token 数，接近阈值时提取关键事实。"""
        if self._already_flushed:
            return None

        # Estimate current context token count
        messages = state.get("messages", [])
        total_tokens = sum(
            estimate_tokens(getattr(m, "content", ""))
            for m in messages
        )

        if total_tokens < self.flush_threshold:
            return None

        # Trigger flush — extract key facts from recent conversation
        self._already_flushed = True

        # Get recent conversation text for extraction
        recent_messages = messages[-10:]  # Last 10 messages
        recent_text = "\n".join(
            getattr(m, "content", "") for m in recent_messages
            if hasattr(m, "content") and isinstance(getattr(m, "content", ""), str)
        )

        if not recent_text:
            return None

        # Use the LLM to extract facts (via runtime model call)
        # This is deferred — we append a system message to trigger extraction
        flush_message = SystemMessage(
            content=f"{self._flush_prompt}\n\nRecent conversation:\n{recent_text[:5000]}"
        )

        return {"messages": [flush_message]}

    def _append_to_daily(self, content: str) -> None:
        """追加内容到当日记忆文件。"""
        today_file = self.memory_dir / _get_today_file()
        with open(today_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Pre-compaction memory flush — {datetime.now().isoformat()}\n\n")
            f.write(content)
            f.write("\n")
