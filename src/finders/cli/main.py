"""CLI entry point for Finders."""
from __future__ import annotations

import asyncio
from dotenv import load_dotenv
from rich.panel import Panel

from finders.agents.factory import create_finders_agent
from finders.utils.checkpointing import (
    delete_thread_sync,
    get_thread_id,
    list_thread_ids,
    get_session_preview,
    load_thread_history,
    open_saver,
)
from finders.cli.tui import TUI
from finders.utils.config import get_settings

load_dotenv()


class SessionShell:
    """交互式会话：管理当前 thread_id 及 /session 子菜单。"""

    def __init__(self, tui, settings) -> None:
        self.tui = tui
        self.settings = settings
        self.thread_id = get_thread_id()
        self.saver = None  # set after open_saver()

    async def session_menu(self) -> None:
        """/session 会话管理页面：上下键选择，enter 载入，d <光标> 删除。"""
        sessions = list_thread_ids()
        if not sessions:
            self.tui.console.print(Panel("Session Manager", style="cyan"))
            self.tui.console.print("  [dim]- no saved sessions -[/dim]")
            return

        # 预取每个会话的预览
        rows: list[tuple[str, str]] = []
        for tid, _ in sessions:
            preview = await get_session_preview(self.saver, tid) or "(empty)"
            rows.append((tid, preview))

        selected_tid = await _interactive_session_picker(rows, self)
        if selected_tid:
            await self._load_session(selected_tid)

    async def _load_session(self, tid: str) -> None:
        """载入历史会话：切换 thread_id 并回放历史消息。

        与实时对话采用同一渲染模式：用户/助手走统一 Markdown，工具走统一
        工具行（仅展示参数，不展示工具执行结果）。
        """
        history = await load_thread_history(self.saver, tid)
        self.thread_id = tid
        self.tui.console.print(Panel(f"Session loaded: {tid[:8]}", style="cyan"))

        for entry in history:
            role = entry["role"]
            if role == "user":
                self.tui.render_user_message(entry["content"])
            elif role == "assistant":
                self.tui.print_answer(entry["content"])
            elif role == "tool_call":
                self.tui.console.print(self.tui._tool_line(entry["content"], entry.get("args", {})))
            self.tui.console.print()


async def _interactive_session_picker(
    rows: list[tuple[str, str]], shell, _input=None, _output=None
) -> str | None:
    """prompt_toolkit 方向键选择器（异步版本）。

    按键：↑/↓ 移动，Enter 载入，d 删除当前项，q/Esc 退出。
    返回被选中（载入）的 thread_id，退出返回 None。
    """
    from prompt_toolkit import Application
    from prompt_toolkit.application import get_app
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl

    items: list[tuple[str, str]] = list(rows)
    selected = 0
    status = ""
    result: dict[str, str | None] = {"tid": None}

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        nonlocal selected
        if selected > 0:
            selected -= 1
            get_app().invalidate()

    @kb.add("down")
    def _(event):
        nonlocal selected
        if selected < len(items) - 1:
            selected += 1
            get_app().invalidate()

    @kb.add("enter")
    def _(event):
        if items:
            result["tid"] = items[selected][0]
        event.app.exit()

    def delete_current(event):
        nonlocal selected, status
        if not items:
            return
        tid = items[selected][0]
        delete_thread_sync(tid)
        if tid == shell.thread_id:
            shell.thread_id = get_thread_id()  # 避免复用已删态
        status = f"deleted {tid[:8]}"
        del items[selected]
        if items:
            selected = min(selected, len(items) - 1)
        else:
            status = "no sessions left"
        get_app().invalidate()

    kb.add("d")(delete_current)
    kb.add("q")(lambda event: event.app.exit())
    kb.add("escape")(lambda event: event.app.exit())

    def render():
        lines = [("bold ansicyan", "Session Manager\n")]
        for i, (tid, preview) in enumerate(items):
            marker = ">"
            if i == selected:
                lines.append(("bold ansicyan", f"  {marker} {tid[:8]}  {preview}\n"))
            else:
                lines.append(("", f"   {marker} {tid[:8]}  {preview}\n"))
        hint = ("ansibrightblack", "\n[up/down] move   [enter] load   [d] delete   [q] quit")
        lines.append(("", status))
        lines.append(hint)
        return lines

    control = FormattedTextControl(render, focusable=True)
    app = Application(
        layout=Layout(Window(control)),
        key_bindings=kb,
        full_screen=False,
        input=_input,
        output=_output,
    )
    await app.run_async()
    return result["tid"]


async def run_repl(shell: SessionShell, tui: TUI, agent) -> None:
    """主输入循环。"""
    tui.print_banner()
    tui.print_welcome()

    while True:
        if shell.thread_id is None:
            shell.thread_id = get_thread_id()

        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue

        if query.lower() in ("/quit", "/exit", "/q"):
            break

        if query.startswith("/model"):
            parts = query.split(maxsplit=1)
            if len(parts) == 2:
                shell.settings.agent.model = parts[1]
                tui.console.print(f"Model set to: {shell.settings.agent.model}", style="cyan")
            continue

        if query.lower() == "/session":
            await shell.session_menu()
            tui.print_separator()
            continue

        await tui.run_query(agent, query, shell.thread_id, shell.settings.agent.recursion_limit)
        tui.print_separator()

    tui.console.print("Goodbye!", style="dim")


async def main() -> None:
    """CLI 入口点：带持久化会话的交互式问答。"""
    settings = get_settings()
    tui = TUI()
    async with open_saver() as saver:
        await saver.setup()
        agent = create_finders_agent(settings, checkpointer=saver)

        shell = SessionShell(tui, settings)
        shell.saver = saver

        await run_repl(shell, tui, agent)


def cli() -> None:
    """console script 同步入口（finders）：内部负责启动事件循环。"""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())