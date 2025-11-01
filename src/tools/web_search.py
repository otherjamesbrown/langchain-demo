"""
Web search tool for LangChain agents using Tavily Search API.

This module provides a LangChain tool that agents can use to search the web
for company information, with support for result formatting and filtering.
"""

import os
from typing import Optional
from langchain_core.tools import tool
import requests

from src.tools.models import SearchResult


class TavilySearchAPI:
    """Wrapper for Tavily Search API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Tavily Search API client.
        
        Args:
            api_key: Tavily API key. If None, reads from TAVILY_API_KEY env var
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Tavily API key is required. Set TAVILY_API_KEY environment variable"
            )
        self.base_url = "https://api.tavily.com/search"
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """
        Perform web search using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 5)
            include_domains: Optional list of domains to search (e.g., ['example.com'])
            exclude_domains: Optional list of domains to exclude
            
        Returns:
            List of SearchResult objects containing search results
            
        Raises:
            requests.RequestException: If API request fails
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",  # Use advanced search for better results
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    relevance_score=item.get("score")
                ))
            
            return results
            
        except requests.RequestException as e:
            raise Exception(f"Tavily search failed: {str(e)}")


# Global Tavily client instance
_tavily_client: Optional[TavilySearchAPI] = None


def _get_tavily_client() -> TavilySearchAPI:
    """Get or create global Tavily client instance."""
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = TavilySearchAPI()
    return _tavily_client


@tool
def web_search_tool(query: str) -> str:
    """
    Search the web for information about companies.
    
    Use this tool to find:
    - Industry classification and sector information
    - Company size (number of employees)
    - Revenue and financial information
    - Founded year and company history
    - Headquarters location
    - Products, services, and offerings
    - Funding stage and ownership
    - Competitors and market position
    - Recent news and updates
    
    The tool will search the web and return relevant results with titles,
    URLs, and content snippets that can be used to answer questions.
    
    Args:
        query: Search query string (e.g., "BitMovin company information")
        
    Returns:
        Formatted string containing search results with titles, URLs, and content
        
    Example:
        query="BitMovin employee count video streaming company"
        Returns formatted results from multiple sources
    """
    client = _get_tavily_client()
    results = client.search(query=query, max_results=5)
    
    # Format results for agent consumption
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_results.append(
            f"Result {i}:\n"
            f"Title: {result.title}\n"
            f"URL: {result.url}\n"
            f"Content: {result.content}\n"
        )
    
    if not formatted_results:
        return "No search results found."
    
    return "\n---\n".join(formatted_results)


# Create a list of tools for agent usage
TOOLS = [web_search_tool]


# Alternative: Serper API support (optional)
class SerperSearchAPI:
    """Wrapper for Serper Search API (alternative to Tavily)."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Serper Search API client."""
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Serper API key is required. Set SERPER_API_KEY environment variable"
            )
        self.base_url = "https://google.serper.dev/search"
    
    def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Perform web search using Serper API."""
        payload = {"q": query, "num": num}
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("organic", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    content=item.get("snippet", ""),
                    relevance_score=None
                ))
            
            return results
            
        except requests.RequestException as e:
            raise Exception(f"Serper search failed: {str(e)}")


def get_search_api_provider() -> str:
    """
    Determine which search API provider to use.
    
    Returns:
        Provider name ('tavily' or 'serper')
    """
    if os.getenv("SERPER_API_KEY"):
        return "serper"
    elif os.getenv("TAVILY_API_KEY"):
        return "tavily"
    else:
        raise ValueError(
            "No search API configured. Set TAVILY_API_KEY or SERPER_API_KEY"
        )

