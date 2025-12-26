"""
Web Search Module - Tavily AI integration for real-time web search.
Provides the assistant with access to current information beyond its training data.

Design for low latency:
- Fast keyword detection (no LLM call needed)
- Short timeout (2 seconds max)
- Concise result formatting
"""

import re
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import sys
sys.path.append('..')
from config import config


# Check if Tavily is available
TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    pass


class WebSearchHandler:
    """
    Handles web search using Tavily AI API.
    
    Features:
    - Smart detection of queries needing web search
    - Fast timeout to maintain low latency
    - Concise result formatting for voice responses
    """
    
    # Keywords that strongly indicate need for web search
    SEARCH_KEYWORDS = [
        # Time-sensitive
        "today", "yesterday", "this week", "this month", "this year",
        "latest", "recent", "current", "now", "currently",
        "breaking", "update", "new", "just happened",
        
        # News & Events
        "news", "headlines", "announced", "released", "launched",
        "election", "vote", "results",
        
        # Real-time data
        "weather", "forecast", "temperature",
        "stock", "price", "market", "trading",
        "score", "match", "game", "won", "lost", "playing",
        
        # Information queries
        "who is", "what is happening", "what happened",
        "when is", "where is", "how much",
        
        # Explicit search intent
        "search", "look up", "find out", "google",
    ]
    
    # Patterns that indicate web search need
    SEARCH_PATTERNS = [
        r"\b(in\s+)?202[3-9]\b",  # Years 2023-2029
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+202[3-9]\b",
    ]
    
    # Timeout for web search (seconds) - keep low for latency
    SEARCH_TIMEOUT = 2.0
    
    def __init__(self):
        """Initialize the web search handler."""
        self.enabled = False
        self.client = None
        
        if not TAVILY_AVAILABLE:
            if config.DEBUG:
                print("[WARN] Tavily not installed. Web search disabled.")
            return
            
        if not config.TAVILY_API_KEY:
            if config.DEBUG:
                print("[WARN] TAVILY_API_KEY not set. Web search disabled.")
            return
        
        try:
            self.client = TavilyClient(api_key=config.TAVILY_API_KEY)
            self.enabled = True
            if config.DEBUG:
                print("[OK] Web search enabled (Tavily AI)")
        except Exception as e:
            print(f"[WARN] Failed to initialize Tavily: {e}")
    
    def should_search(self, query: str) -> bool:
        """
        Determine if a query needs web search.
        Uses fast keyword matching - no LLM call needed.
        
        Args:
            query: User's question
            
        Returns:
            True if web search would help answer this query
        """
        if not self.enabled:
            return False
        
        query_lower = query.lower()
        
        # Check for search keywords
        for keyword in self.SEARCH_KEYWORDS:
            if keyword in query_lower:
                if config.DEBUG:
                    print(f"[SEARCH] Web search triggered by keyword: '{keyword}'")
                return True
        
        # Check for date patterns
        for pattern in self.SEARCH_PATTERNS:
            if re.search(pattern, query_lower):
                if config.DEBUG:
                    print(f"[SEARCH] Web search triggered by date pattern")
                return True
        
        return False
    
    def search(self, query: str, max_results: int = 3) -> Optional[str]:
        """
        Perform web search and return formatted results.
        Uses timeout to maintain low latency.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Formatted search results or None if search failed
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Use ThreadPoolExecutor for timeout support
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._perform_search,
                    query,
                    max_results
                )
                
                try:
                    result = future.result(timeout=self.SEARCH_TIMEOUT)
                    return result
                except FuturesTimeoutError:
                    if config.DEBUG:
                        print(f"[WARN] Web search timed out after {self.SEARCH_TIMEOUT}s")
                    return None
                    
        except Exception as e:
            if config.DEBUG:
                print(f"[ERROR] Web search error: {e}")
            return None
    
    def _perform_search(self, query: str, max_results: int) -> Optional[str]:
        """
        Internal method to perform the actual search.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            Formatted results string
        """
        try:
            response = self.client.search(
                query=query,
                search_depth="basic",  # "basic" is faster than "advanced"
                max_results=max_results,
                include_raw_content=False,  # Don't need full page content
                include_images=False,
            )
            
            return self._format_results(response)
            
        except Exception as e:
            if config.DEBUG:
                print(f"[ERROR] Tavily search error: {e}")
            return None
    
    def _format_results(self, response: Dict) -> str:
        """
        Format search results for LLM context.
        Keeps it concise for voice responses.
        
        Args:
            response: Tavily API response
            
        Returns:
            Formatted string with search results
        """
        results = response.get("results", [])
        
        if not results:
            return "No relevant web results found."
        
        formatted_parts = ["[Web Search Results]"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "")
            content = result.get("content", "")
            
            # Truncate content to keep response concise
            if len(content) > 200:
                content = content[:200] + "..."
            
            formatted_parts.append(f"{i}. {title}: {content}")
        
        return "\n".join(formatted_parts)
    
    def get_search_context(self, query: str) -> Optional[str]:
        """
        Get search context to augment LLM response.
        This is the main entry point for the LLM handler.
        
        Args:
            query: User's question
            
        Returns:
            Search context string or None
        """
        if not self.should_search(query):
            return None
        
        if config.DEBUG:
            print("Searching the web...")
        
        return self.search(query)
