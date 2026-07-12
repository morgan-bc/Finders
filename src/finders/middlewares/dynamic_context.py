"""Dynamic context middleware for injecting current date into system prompt."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse


CURRENT_DATE_PROMPT = """
<system_reminder>
Current Date: {date}

Always use this actual date when forming search queries, referencing time-sensitive information, or generating reports. Never use hardcoded past years or placeholder dates.
</system_reminder>
"""


class DynamicContextMiddleware(AgentMiddleware):
    """Middleware for injecting dynamic context (current date) into the system prompt.

    This runs on every model call to ensure the date is always fresh and accurate,
    which is critical for time-sensitive research and web search queries.
    """

    
    def modify_request(self, request):
        """Modify the request by injecting the current date into the system prompt.

        Args:
            request: The original request.

        Returns:
            The modified request with the current date. 

        Args:
            state: Current agent state.
            runtime: Runtime context.

        Returns:
            Updated state with modified system message, or None.
        """
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        date_section = CURRENT_DATE_PROMPT.format(date=date_str)
        system_prompt = request.system_prompt
        if system_prompt is not None:
            system_prompt = system_prompt + "\n\n" + date_section
            request = request.override(system_prompt=system_prompt)

        return request

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        """Wrap the model call to inject dynamic context.

        Args:
            request: The original request.

        Returns:
            The model response with the current date injected.
        """
        request = self.modify_request(request)
        return handler(request)
    
    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        """Wrap the model call to inject dynamic context.

        Args:
            request: The original request.

        Returns:
            The model response with the current date injected.
        """
        request = self.modify_request(request)
        return await handler(request)
