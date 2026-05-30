from langchain_tavily import TavilySearch
import asyncio

async def test():
    s = TavilySearch(max_results=3)
    r = await s.ainvoke({'query': 'test'})
    print(type(r))
    print(r)

asyncio.run(test())
