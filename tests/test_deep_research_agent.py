"""Test script for deep-research subagent.

Runs the deep-research subagent with a research query and prints the result.
Requires valid LLM and API keys configured in .env.

Usage:
    python tests/test_deep_research_agent.py
    python tests/test_deep_research_agent.py --query "Your custom research question"
"""

import argparse
import asyncio
import sys
import time

from finders.subagents.builtins.deep_research import DEEP_RESEARCH_CONFIG
from finders.subagents.executor import SubagentExecutor, SubagentStatus
from finders.tools.registry import get_core_tools
from finders.utils.config import Settings


DEFAULT_QUERY = "What are the latest developments in AI agents frameworks in 2026? Compare LangChain, CrewAI, and AutoGen."


def print_config():
    """Print the deep-research subagent configuration."""
    print("=" * 60)
    print("Deep Research Subagent Configuration")
    print("=" * 60)
    print(f"Name:            {DEEP_RESEARCH_CONFIG.name}")
    print(f"Model:           {DEEP_RESEARCH_CONFIG.model}")
    print(f"Max turns:       {DEEP_RESEARCH_CONFIG.max_turns}")
    print(f"Timeout:         {DEEP_RESEARCH_CONFIG.timeout_seconds}s")
    print(f"Disallowed tools: {DEEP_RESEARCH_CONFIG.disallowed_tools}")
    print(f"Allowed skills:  {DEEP_RESEARCH_CONFIG.allowed_skills}")
    print(f"Disallowed skills: {DEEP_RESEARCH_CONFIG.disallowed_skills}")
    print(f"System prompt length: {len(DEEP_RESEARCH_CONFIG.system_prompt)} chars")
    print("=" * 60)


async def run_deep_research(query: str):
    """Run the deep-research subagent with the given query."""
    settings = Settings()
    settings.memory.enabled = False

    # Load tools and filter out "task" tool as per config
    all_tools = get_core_tools(settings)
    disallowed = set(DEEP_RESEARCH_CONFIG.disallowed_tools or [])
    tools = [t for t in all_tools if t.name not in disallowed]

    print(f"\nAvailable tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool.name}")

    excluded = [t for t in all_tools if t.name in disallowed]
    if excluded:
        print(f"\nExcluded tools ({len(excluded)}):")
        for tool in excluded:
            print(f"  - {tool.name}")

    executor = SubagentExecutor(
        config=DEEP_RESEARCH_CONFIG,
        tools=tools,
        parent_model=settings.agent.model,
    )

    print(f"\n{'=' * 60}")
    print(f"Research Query: {query}")
    print(f"{'=' * 60}\n")
    print("Running deep research...\n")

    start_time = time.time()
    result = await executor._aexecute(query)
    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"Status:    {result.status.value}")
    print(f"Duration:  {elapsed:.1f}s")
    print(f"AI turns:  {len(result.ai_messages)}")

    if result.status == SubagentStatus.COMPLETED:
        print(f"\n{'=' * 60}")
        print("Research Result:")
        print(f"{'=' * 60}\n")
        print(result.result)
    else:
        print(f"\nError: {result.error}")

    print(f"\n{'=' * 60}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Test deep-research subagent")
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=DEFAULT_QUERY,
        help="Research query to test",
    )
    args = parser.parse_args()

    print_config()
    result = asyncio.run(run_deep_research(args.query))

    if result.status != SubagentStatus.COMPLETED:
        sys.exit(1)


if __name__ == "__main__":
    main()
