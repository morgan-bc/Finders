"""Agent scratchpad for tracking tool calls and persisting to JSONL."""
import json
from pathlib import Path
from dataclasses import dataclass
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
