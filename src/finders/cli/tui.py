"""CLI terminal UI for Finders."""
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

from langchain_core.messages import AIMessageChunk, ToolMessage


def _extract_text(content) -> str:
    """从消息 content 中提取纯文本（跳过 thinking/reasoning 块）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


class TUI:
    """Rich-based terminal UI for Finders."""

    def __init__(self) -> None:
        self.console = Console()

    def print_banner(self) -> None:
        self.console.print(Panel("Finders - Deep Financial Research", style="bold cyan"))
        self.console.print()

    def print_welcome(self) -> None:
        self.console.print("Enter a financial question, or [bold]/quit[/bold] to exit.", style="dim")
        self.console.print()
        
    def print_assistant_start(self) -> None:
        self.console.print()
        self.console.print("[bold][blue]Assistant:[/blue][/bold]")

    def print_answer(self, answer: str) -> None:
        if not answer:
            return
        self.console.print()
        self.console.print(Panel(Markdown(answer), title="Answer", style="green"))
        self.console.print()

    def render_user_message(self, content: str) -> None:
        """渲染用户消息（与历史/实时对话一致）。"""
        self.console.print()
        self.console.print("[bold][green]You:[/green][/bold]")
        if content:
            self.console.print(Markdown(content))

    @staticmethod
    def _tool_line(tool: str, args) -> str:
        """统一的工具调用行格式。"""
        args_preview = str(args)
        if len(args_preview) > 200:
            args_preview = args_preview[:200] + "..."
        return f"  [dim]Tool:[/dim] {tool} [dim]({args_preview})[/dim]"

    def print_tool_start(self, tool: str, args) -> None:
        self.console.print(self._tool_line(tool, args))

    def print_tool_end(self, tool: str, duration_ms: int) -> None:
        self.console.print(f"  [dim]Done: {tool} ({duration_ms}ms)[/dim]")

    def print_tool_error(self, tool: str, error: str) -> None:
        self.console.print(f"  [red]Error: {tool} - {error}[/red]")

    def print_thinking(self) -> None:
        self.console.print(f"  [yellow]Thinking...[/yellow]")

    def print_separator(self) -> None:
        self.console.print()

    async def run_query(self, agent, query: str, thread_id: str, recursion_limit: int = 100) -> None:
        """运行查询并流式显示事件。

        回答消息以流水方式在 “Answer” 面板内实时渲染 Markdown（与历史会话
        print_answer 渲染一致）；结束后面板定格显示，不再重复打印。
        """
        import time

        tool_start_times: dict[str, float] = {}
        answer_chunks: list[str] = []
        streamed_any = False
        final_output = None
        config = {
            "recursion_limit": recursion_limit,
            "configurable": {"thread_id": thread_id},
        }

        spinner = Spinner("dots", text="Thinking...", style="yellow")
        self.render_user_message(query)
        self.print_assistant_start()

        # transient=False：停止后最后一帧（Answer 面板）确定性地保留在屏幕上
        live = Live(spinner, refresh_per_second=10, transient=False)
        live.start()
        try:
            async for event in agent.astream_events(
                {"messages": [("user", query)]},
                version="v2",
                config=config,
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    # 流式累积最终回答文本，实时在 Answer 面板内渲染 Markdown
                    chunk = event["data"].get("chunk")
                    if chunk is not None:
                        txt = _extract_text(getattr(chunk, "content", None))
                        if txt:
                            streamed_any = True
                            answer_chunks.append(txt)
                            live.update(
                                Panel(
                                    Markdown("".join(answer_chunks)),
                                    title="Answer",
                                    style="green",
                                )
                            )

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_start_times[tool_name] = time.time()
                    args = event["data"].get("input", {})
                    live.console.print(self._tool_line(tool_name, args))

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    start_time = tool_start_times.pop(tool_name, time.time())
                    duration_ms = int((time.time() - start_time) * 1000)
                    live.console.print(f"  [dim]Done: {tool_name} ({duration_ms}ms)[/dim]")

                elif kind == "on_tool_error":
                    tool_name = event["name"]
                    error = str(event["data"].get("error", "Unknown error"))
                    live.console.print(f"  [red]Error: {tool_name} - {error}[/red]")

                elif kind == "on_chat_model_end":
                    output = event["data"].get("output")
                    has_tool_calls = output is not None and getattr(output, "tool_calls", None)
                    if has_tool_calls:
                        # 本次模型输出是工具调用计划：丢弃已累积文本，回到 thinking
                        answer_chunks = []
                        streamed_any = False
                        live.update(spinner)
                    else:
                        final_output = output
        finally:
            if streamed_any:
                # 流式面板已定格显示，直接停止 live，不再重复打印
                live.stop()
            else:
                # 未产生流式文本：清掉残留 spinner，必要时补打一次最终输出
                live.update("")
                live.stop()
                content = (
                    _extract_text(getattr(final_output, "content", None))
                    if final_output is not None
                    else ""
                )
                if content:
                    self.print_answer(content)
