import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

# These endpoints reflect the live URL structures for basic queries.
SEARCH_ENDPOINTS = {
    "Google": "https://www.google.com/search",
    "Bing": "https://www.bing.com/search",
    "DuckDuckGo": "https://duckduckgo.com/html/"
}

async def fetch_search_results(engine, query):
    """Fetch search results from a given search engine."""
    url = SEARCH_ENDPOINTS.get(engine)
    params = {"q": query}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.text

async def aggregate_search(query):
    """Aggregate search results from multiple engines."""
    tasks = [fetch_search_results(engine, query) for engine in SEARCH_ENDPOINTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    aggregated = {}
    for engine, result in zip(SEARCH_ENDPOINTS.keys(), results):
        if isinstance(result, Exception):
            logging.error(f"Error fetching results from {engine}: {result}")
            aggregated[engine] = "Error fetching results"
        else:
            aggregated[engine] = result[:200] + "..."  # Return a snippet.
    return aggregated

if __name__ == '__main__':
    import asyncio
    query = "latest AI assistant technology"
    results = asyncio.run(aggregate_search(query))
    for engine, snippet in results.items():
        print(f"{engine}:\n{snippet}\n")