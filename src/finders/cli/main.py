"""CLI entry point for Finders."""
from __future__ import annotations

import asyncio
import sys

from finders.agents.factory import create_finders_agent
from finders.cli.tui import TUI
from finders.utils.config import get_settings


def main() -> None:
    """CLI 入口点：交互式问答。"""
    settings = get_settings()
    tui = TUI()
    agent = create_finders_agent(settings)

    tui.print_banner()
    tui.print_welcome()

    while True:
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
                settings.agent.model = parts[1]
                tui.console.print(f"Model set to: {settings.agent.model}", style="cyan")
            continue

        asyncio.run(tui.run_query(agent, query))
        tui.print_separator()

    tui.console.print("Goodbye!", style="dim")


def serve() -> None:
    """启动 API 服务器。"""
    import uvicorn
    from finders.api.app import create_app

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
