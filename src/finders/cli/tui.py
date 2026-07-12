"""CLI terminal UI for Finders."""
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

from langchain_core.messages import AIMessageChunk, ToolMessage


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

    def print_answer(self, answer: str) -> None:
        self.console.print()
        self.console.print(Panel(Markdown(answer), title="Answer", style="green"))
        self.console.print()

    def print_tool_start(self, tool: str, args: dict) -> None:
        query = args.get("query", args.get("url", ""))
        preview = str(query)[:80] if query else ""
        self.console.print(f"  [dim]Tool:[/dim] {tool} {f'[dim]({preview})[/dim]' if preview else ''}")

    def print_tool_end(self, tool: str, duration_ms: int) -> None:
        self.console.print(f"  [dim]Done: {tool} ({duration_ms}ms)[/dim]")

    def print_tool_error(self, tool: str, error: str) -> None:
        self.console.print(f"  [red]Error: {tool} - {error}[/red]")

    def print_thinking(self) -> None:
        self.console.print(f"  [yellow]Thinking...[/yellow]")

    def print_separator(self) -> None:
        self.console.print()

    async def run_query(self, agent, query: str) -> None:
        """运行查询并流式显示事件。"""
        import time

        tool_start_times: dict[str, float] = {}

        with Live(Spinner("dots", text="Thinking...", style="yellow"), refresh_per_second=10, transient=True):
            async for event in agent.astream_events(
                {"messages": [("user", query)]},
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_start":
                    self.print_thinking()

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_start_times[tool_name] = time.time()
                    args = event["data"].get("input", {})
                    self.print_tool_start(tool_name, args)

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    start_time = tool_start_times.pop(tool_name, time.time())
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.print_tool_end(tool_name, duration_ms)

                elif kind == "on_tool_error":
                    tool_name = event["name"]
                    error = str(event["data"].get("error", "Unknown error"))
                    self.print_tool_error(tool_name, error)

                elif kind == "on_chat_model_end":
                    # 最终回答
                    chunks = event["data"].get("output", {})
                    if hasattr(chunks, "content") and chunks.content:
                        self.print_answer(chunks.content)
                        break
