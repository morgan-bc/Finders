"""Finders Agent Demo - 实际可运行的示例"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from finders.utils.config import Settings
from finders.agents.factory import create_finders_agent
from langchain_core.messages import AIMessage



async def main():

    state = {
        "messages": [
            {"role": "user", "content": "分析赣锋锂业基本面"},
        ],
    }


    settings = Settings()
    agent = create_finders_agent(settings)
    final_state = None
    async for chunk in agent.astream(state, version="v2", stream_mode="values"):
        final_state = chunk
        
    messages = final_state["messages"]
    last_ai_message = None
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            last_ai_message = message
            break
    if last_ai_message:
        print(last_ai_message.content)
    else:
        print("No AIMessage found in messages")
    


if __name__ == "__main__":
    asyncio.run(main())
