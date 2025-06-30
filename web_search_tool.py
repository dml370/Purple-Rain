# FILE: tools/web_search_tool.py
# Final, Unabridged Version: June 29, 2025

import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class WebSearchTool:
    """Provides full web access: searching for pages and reading their content."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        }

    async def search(self, query: str) -> dict:
        """Performs a web search and returns a list of results."""
        logger.info(f"Searching web for: '{query}'")
        search_url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(timeout=15, headers=self.headers) as client:
                response = await client.get(search_url, params={'q': query})
                response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = [{'title': r.find('a', class_='result__a').text, 'snippet': r.find('div', class_='result__snippet').text, 'url': r.find('a', 'result__url')['href']} for r in soup.find_all('div', class_='result', limit=7) if r.find('a', class_='result__a')]
            return {"status": "success", "results": results or "No results found."}
        except Exception as e:
            logger.error(f"Web search failed for query '{query}': {e}")
            return {"error": f"An error occurred during the web search: {str(e)}"}

    async def read_page_content(self, url: str) -> dict:
        """Navigates to a URL and reads its primary text content."""
        logger.info(f"Reading page content from: {url}")
        try:
            async with httpx.AsyncClient(timeout=20, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
                element.decompose()
            text = soup.get_text(separator='\n', strip=True)
            return {"status": "success", "url": url, "content": text[:8000]} # Truncate for context
        except Exception as e:
            logger.error(f"Failed to read page content from '{url}': {e}")
            return {"error": f"An error occurred while reading the page: {str(e)}"}
    
    def get_schema(self) -> dict:
        """Defines the tool's structure for the AI."""
        return {
            "name": "web_browser",
            "description": "A tool for Browse the web. It can either search for a query or read the full content of a specific URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_to_perform": {"type": "string", "enum": ["search", "read_page_content"]},
                    "query": {"type": "string", "description": "The search term. Use only with the 'search' action."},
                    "url": {"type": "string", "description": "The URL to read. Use only with the 'read_page_content' action."}
                },
                "required": ["action_to_perform"]
            }
        }
