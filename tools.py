import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


class SearchInput(BaseModel):
    query: str = Field(description="The exact search keywords or phrase to look up on the web")


class ScrapeInput(BaseModel):
    url: str = Field(description="The full web URL to fetch and scrape clean text content from (e.g. 'https://...')")


@tool("tavily_search", args_schema=SearchInput)
def tavily_search(query: str) -> str:
    """Search the web using Tavily for recent, reliable information on a topic. Returns titles, URLs, and text snippets."""
    results = tavily.search(query=query, max_results=3)
    out = []
    for r in results.get("results", []):
        out.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:250]}\n")
    return "\n----\n".join(out)


@tool("scrape_url", args_schema=ScrapeInput)
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:1800]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"


# Aliases for backwards compatibility
web_search = tavily_search
search = tavily_search

if __name__ == "__main__":
    print(scrape_url.invoke({"url": "https://www.theguardian.com/technology/2026/nov/14/jensen-huang-affair-nvidia-nightmare"}))
