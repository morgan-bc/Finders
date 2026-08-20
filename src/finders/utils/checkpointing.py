"""Session checkpoint manager for Finders.

Uses ``AsyncSqliteSaver`` (from ``langgraph-checkpoint-sqlite``) to persist agent
conversation state keyed by ``thread_id``. The database lives at
``$FINDERS_WORKSPACE/sessions/chat.db``.
"""
from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from finders.utils.config import get_settings


def get_sessions_db_path() -> Path:
    """Return the path to the sessions SQLite database, creating its directory."""
    ws = get_settings().get_workspace_path()
    path = ws / "sessions" / "chat.db"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Enable WAL so concurrent connections (main + subagent threads) don't lock.
    con = sqlite3.connect(path)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA wal_autocheckpoint=100")
        con.commit()
    finally:
        con.close()
    return path


def get_thread_id() -> str:
    """Generate a unique thread/session id."""
    import uuid

    return str(uuid.uuid4())


@asynccontextmanager
async def open_saver(db_path: Optional[str] = None) -> AsyncIterator[AsyncSqliteSaver]:
    """Open an ``AsyncSqliteSaver`` for the given database path.

    Usage::

        async with open_saver() as saver:
            await saver.setup()
            # pass threading config + saver to the agent
    """
    path = Path(db_path) if db_path else get_sessions_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        yield saver


def list_thread_ids(db_path: Optional[str] = None, limit: int = 50) -> list[tuple[str, str]]:
    """Return ``[(thread_id, updated_at_checkpoint_id)]`` sorted newest first.

    ``updated_at`` is the checkpoint_id (timestamp-ordered) of the thread's latest
    checkpoint, which we use for display ordering.
    """
    path = Path(db_path) if db_path else get_sessions_db_path()
    if not path.exists():
        return []

    con = sqlite3.connect(path)
    try:
        rows = con.execute(
            """
            SELECT thread_id, MAX(checkpoint_id) AS latest FROM checkpoints
            GROUP BY thread_id
            ORDER BY latest DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(r[0], r[1] or "") for r in rows]
    finally:
        con.close()


async def get_session_preview(saver, thread_id: str, max_chars: int = 60) -> str:
    """Return a short preview (last user/assistant message) for a thread."""
    tup = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
    if tup is None:
        return ""

    try:
        messages = tup.checkpoint["channel_values"].get("messages", [])
    except Exception:
        return ""

    last = messages[-1] if messages else None
    if last is None:
        return ""

    try:
        content = getattr(last, "content", "")
    except Exception:
        return ""

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        content = "".join(parts)
    return str(content).replace("\n", " ")[:max_chars]


async def delete_thread(saver, thread_id: str) -> None:
    """Delete every checkpoint/write for a thread."""
    await saver.adelete_thread(thread_id)


def delete_thread_sync(thread_id: str, db_path: Optional[str] = None) -> None:
    """Synchronously delete a thread's checkpoints/writes.

    Useful inside keyboard-driven UI loops where awaiting isn't available.
    """
    path = Path(db_path) if db_path else get_sessions_db_path()
    if not path.exists():
        return
    con = sqlite3.connect(path)
    try:
        con.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        con.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        con.commit()
    finally:
        con.close()


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


async def load_thread_history(saver, thread_id: str) -> list[dict]:
    """Return structured recorded messages for a thread.

    Each entry is ``{"role": "user"|"assistant"|"tool_call", ...}``.
    Tool results (``ToolMessage``) are intentionally omitted.
    """
    tup = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
    if tup is None:
        return []

    entries: list[dict] = []
    for msg in tup.checkpoint["channel_values"].get("messages", []):
        mtype = getattr(msg, "type", "")

        if mtype == "human":
            content = _extract_text(getattr(msg, "content", None))
            if content:
                entries.append({"role": "user", "content": content})

        elif mtype == "ai":
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                # 只展示工具调用及参数，不展示结果
                for tc in tool_calls:
                    name = tc.get("name", "?")
                    args = tc.get("args", {})
                    entries.append({"role": "tool_call", "content": name, "args": args})
            else:
                content = _extract_text(getattr(msg, "content", None))
                if content:
                    entries.append({"role": "assistant", "content": content})

        # ToolMessage / system: skipped (结果为工具执行输出，不展示)
    return entries