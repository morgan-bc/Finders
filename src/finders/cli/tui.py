"""CLI terminal UI for Finders."""
from __future__ import annotations

import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

from finders.agent.runner import AgentRunner


class TUI:
    """Rich-based terminal UI for Finders."""

    def __init__(self) -> None:
        self.console = Console()
        self._thinking_msg = ""

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

    def print_tool_end(self, tool: str, preview: str, duration_ms: int) -> None:
        self.console.print(f"  [dim]Done: {tool} ({duration_ms}ms)[/dim]")

    def print_tool_error(self, tool: str, error: str) -> None:
        self.console.print(f"  [red]Error: {tool} - {error}[/red]")

    def print_thinking(self, msg: str) -> None:
        self._thinking_msg = msg
        self.console.print(f"  [yellow]{msg}[/yellow]")

    def print_separator(self) -> None:
        self.console.print()

    async def run_query(self, runner: AgentRunner) -> None:
        """运行查询并流式显示事件。"""
        self._thinking_msg = ""
        with Live(Spinner("dots", text="Thinking...", style="yellow"), refresh_per_second=10, transient=True):
            async for event in runner.run_stream():
                if event.type == "thinking":
                    self.print_thinking(event.data.get("message", ""))
                elif event.type == "tool_start":
                    self.print_tool_start(
                        event.data.get("tool", ""),
                        event.data.get("args", {}),
                    )
                elif event.type == "tool_end":
                    self.print_tool_end(
                        event.data.get("tool", ""),
                        event.data.get("result_preview", ""),
                        event.data.get("duration_ms", 0),
                    )
                elif event.type == "tool_error":
                    self.print_tool_error(
                        event.data.get("tool", ""),
                        event.data.get("error", ""),
                    )
                elif event.type == "answer":
                    answer = event.data.get("answer", "")
                    if answer:
                        self.print_answer(answer)
                    break
