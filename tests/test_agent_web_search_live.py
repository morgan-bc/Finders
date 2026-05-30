"""Agent integration test: run the full agent with a real query and observe web_search behavior."""
import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from finders.agents.factory import create_finders_agent
from finders.utils.config import Settings
from finders.tools.web_search import web_search


async def test_direct_web_search():
    """Test web search tool directly with real API call."""
    print("=" * 60)
    print("=== TEST 1: Direct Web Search Tool ===")
    print("=" * 60)

    query = "比亚迪2026年第一季度财报"
    print(f"Query: {query}\n")

    result = await web_search.ainvoke(query)
    print(f"Result:\n{result}")
    print()

    assert result, "web_search should return non-empty results"
    assert "Error" not in result, f"web_search returned an error: {result}"
    assert "**" in result, "Results should contain formatted titles"
    assert "http" in result, "Results should contain URLs"

    print("✅ Direct web search test PASSED")
    print("=" * 60)


async def test_agent_run():
    """Test full agent with async run."""
    print("\n" + "=" * 60)
    print("=== TEST 2: Full Agent Run ===")
    print("=" * 60)

    query = "分析比亚迪2026年第一季度财报"
    settings = Settings()
    settings.memory.enabled = False

    print(f"Query: {query}")
    print(f"Model: {settings.agent.model}")
    print(f"Tavily API Key: {'***' + settings.tavily_api_key[-4:] if settings.tavily_api_key else 'NOT SET'}")
    print()

    agent = create_finders_agent(settings)

    print("[AGENT] Invoking agent...")
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}],
    })

    messages = result.get("messages", [])
    print(f"\n[AGENT] Total messages in conversation: {len(messages)}")

    tool_calls_found = 0
    ai_response = ""
    for msg in messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_found += 1
                print(f"\n[TOOL CALL] {tc.get('name', '')}")
                print(f"  Args: {tc.get('args', {})}")
        elif hasattr(msg, 'content') and getattr(msg, 'type', None) != 'tool':
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if content.strip():
                ai_response = content

    assert tool_calls_found > 0, "Agent should have made at least one tool call"
    assert ai_response, "Agent should have produced a final response"

    print(f"\n[AI RESPONSE]\n{ai_response[:2000]}")
    print(f"\n✅ Agent run test PASSED (found {tool_calls_found} tool call(s))")
    print("=" * 60)


async def main():
    await test_direct_web_search()
    await test_agent_run()
    print("\n🎉 All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
