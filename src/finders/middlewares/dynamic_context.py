"""Dynamic context middleware for injecting current date into system prompt."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage


CURRENT_DATE_PROMPT = """
## System reminder

Current Date: {date}

Always use this actual date when forming search queries, referencing time-sensitive information, or generating reports. Never use hardcoded past years or placeholder dates.
"""


class DynamicContextMiddleware(AgentMiddleware):
    """Middleware for injecting dynamic context (current date) into the system prompt.

    This runs on every model call to ensure the date is always fresh and accurate,
    which is critical for time-sensitive research and web search queries.
    """

    def before_model(self, state: dict[str, Any], runtime) -> dict[str, Any] | None:
        """Inject current date into the system prompt.

        Args:
            state: Current agent state.
            runtime: Runtime context.

        Returns:
            Updated state with modified system message, or None.
        """
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        date_section = CURRENT_DATE_PROMPT.format(date=date_str)

        messages = list(state.get("messages", []))
        if messages and isinstance(messages[0], SystemMessage):
            original_content = messages[0].content
            if isinstance(original_content, str) and "## System reminder" not in original_content:
                messages[0] = SystemMessage(content=original_content + "\n\n" + date_section)
                return {"messages": messages}

        return None
