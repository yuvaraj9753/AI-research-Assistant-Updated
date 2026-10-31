import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_core.tools import tool


load_dotenv()


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise ValueError(
        "TAVILY_API_KEY not found in .env file."
    )


client = TavilyClient(
    api_key=TAVILY_API_KEY
)


def search_web(
    query: str,
    max_results: int = 5
):
    """
    Search the web using Tavily.
    """

    try:

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )

        results = []
        sources = []

        for item in response.get("results", []):

            content = item.get("content", "")
            url = item.get("url", "")
            title = item.get("title", "")

            if content:

                results.append({
                    "title": title,
                    "url": url,
                    "content": content
                })

            if url:
                sources.append(url)

        return {
            "query": query,
            "results": results,
            "sources": sources,
            "total_sources": len(sources)
        }

    except Exception as e:

        return {
            "query": query,
            "results": [],
            "sources": [],
            "total_sources": 0,
            "error": str(e)
        }


@tool
def web_search(query: str) -> str:
    """
    Search the web using Tavily.

    Use this tool when current web information is required
    for research.
    """

    data = search_web(
        query=query,
        max_results=5
    )

    if "error" in data:

        return json.dumps({
            "error": data["error"],
            "query": query
        })

    return json.dumps(
        data,
        ensure_ascii=False
    )