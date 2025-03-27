#!/usr/bin/env python3
"""
Model Context Protocol server implementation for Wikipedia API.
"""
import os
import sys
import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any

# Import MCP SDK
from mcp.server.fastmcp import FastMCP, Context

# Import existing functionality
from src.wikipedia_client import WikipediaClient, ArticleNotFoundError
from src.caching_service import CachingService
from src.parser import WikipediaParser

# Debug log function for console output
def debug_log(message):
    """Log to stderr so it doesn't interfere with JSON-RPC communication"""
    print(message, file=sys.stderr)

# Setup logging to use stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Define enum for summary level
class SummaryLevel(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

# Initialize global clients
wikipedia_client = None
cache_service = None

# Create MCP server
mcp = FastMCP("Wikipedia API")

# Add lifespan hooks for setup and teardown
@mcp.on_startup()
async def startup():
    """Initialize services on startup."""
    global wikipedia_client, cache_service
    
    # Load environment variables
    rate_limit = float(os.getenv("RATE_LIMIT", "1.0"))
    cache_type = os.getenv("CACHE_TYPE", "ttl")
    cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
    cache_maxsize = int(os.getenv("CACHE_MAXSIZE", "1000"))
    cache_dir = os.getenv("CACHE_DIR", None)
    
    # Initialize services
    wikipedia_client = WikipediaClient(rate_limit_delay=rate_limit)
    cache_service = CachingService(
        cache_type=cache_type,
        ttl=cache_ttl,
        maxsize=cache_maxsize,
        cache_dir=cache_dir
    )
    
    debug_log("Wikipedia MCP server initialized successfully")
    debug_log(f"Rate limit: {rate_limit}s between requests")
    debug_log(f"Cache: {cache_type} (TTL: {cache_ttl}s, Max Size: {cache_maxsize})")

@mcp.on_shutdown()
async def shutdown():
    """Clean up resources on shutdown."""
    debug_log("Shutting down Wikipedia MCP server")
    # Nothing to clean up for now

# Helper function for disambiguation handling
def handle_disambiguation(article_data, title):
    """Handle disambiguation pages and return appropriate response."""
    if "error" in article_data and article_data["error"] == "disambiguation":
        options = article_data.get("options", [])
        options_formatted = [f"- {option}" for option in options[:10]]
        if len(options) > 10:
            options_formatted.append(f"- ... and {len(options) - 10} more options")
        
        options_str = "\n".join(options_formatted)
        message = f"The article '{title}' could refer to multiple articles:\n\n{options_str}\n\nPlease specify a more specific title."
        
        debug_log(f"Disambiguation found for '{title}' with {len(options)} options")
        return {
            "type": "disambiguation",
            "title": title,
            "message": message,
            "options": options
        }
    return None

def get_parsed_article(title: str, auto_suggest: bool) -> Dict[str, Any]:
    """
    Central function to get and parse a Wikipedia article.
    
    Args:
        title: Article title
        auto_suggest: Whether to auto-suggest similar titles
        
    Returns:
        Parsed article data
    """
    global wikipedia_client, cache_service
    
    # Create cache key for the parsed article
    cache_key = f"parsed_article:{title}"
    
    # Try to get from cache first
    cached_article = cache_service.get(cache_key)
    if cached_article:
        debug_log(f"Cache hit for article: {title}")
        return cached_article
    
    try:
        debug_log(f"Cache miss for article: {title}, fetching from Wikipedia")
        
        # Get raw article data
        raw_article_data = wikipedia_client.get_article(title, auto_suggest=auto_suggest)
        
        # Check for disambiguation
        disambiguation = handle_disambiguation(raw_article_data, title)
        if disambiguation:
            return disambiguation
        
        # Parse the article
        debug_log(f"Parsing article: {raw_article_data.get('title', title)}")
        parsed_article = WikipediaParser.parse_article(raw_article_data)
        
        # Cache the parsed result
        cache_service.set(cache_key, parsed_article)
        
        return parsed_article
    except ArticleNotFoundError as e:
        logger.warning(f"Article not found: {title}")
        debug_log(f"Article not found: {title}")
        raise Exception(f"Article not found: {title}")
    except Exception as e:
        logger.error(f"Error retrieving article: {str(e)}")
        debug_log(f"Error retrieving article: {str(e)}")
        raise Exception(f"Error retrieving article: {str(e)}")

# Implement MCP tools

@mcp.tool()
def wikipedia_search(term: str, results: int = 10) -> Dict[str, Any]:
    """
    Search for Wikipedia articles matching a term.
    
    Args:
        term: Search term to look for on Wikipedia
        results: Number of results to return (1-50)
    
    Returns:
        Dictionary containing search results
    """
    global wikipedia_client, cache_service
    
    # Validate results parameter
    if results < 1:
        results = 1
    elif results > 50:
        results = 50
    
    try:
        debug_log(f"Searching Wikipedia for '{term}' with {results} results")
        
        # Perform search
        search_results = wikipedia_client.search(term, results=results)
        
        # Return formatted response
        return {
            "query": term,
            "results": search_results,
            "count": len(search_results)
        }
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        debug_log(f"Search error: {str(e)}")
        raise Exception(f"Search error: {str(e)}")

@mcp.tool()
def wikipedia_article(title: str, auto_suggest: bool = True) -> Dict[str, Any]:
    """
    Get a complete Wikipedia article by title with all parsed components.
    
    Args:
        title: The title of the Wikipedia article to retrieve
        auto_suggest: Whether to auto-suggest similar titles
    
    Returns:
        Dictionary containing the complete article data
    """
    try:
        return get_parsed_article(title, auto_suggest)
    except Exception as e:
        raise Exception(str(e))

@mcp.tool()
def wikipedia_summary(title: str, level: SummaryLevel = SummaryLevel.MEDIUM) -> Dict[str, Any]:
    """
    Get a summary of a Wikipedia article at a specific detail level.
    
    Args:
        title: The title of the Wikipedia article to summarize
        level: Summary detail level (short, medium, long)
    
    Returns:
        Dictionary containing the article summary
    """
    try:
        # Get parsed article data
        parsed_article = get_parsed_article(title, True)
        
        # For disambiguation pages, just return as is
        if parsed_article.get("type") == "disambiguation":
            return parsed_article
        
        # Generate summary
        summary = WikipediaParser.generate_summary(parsed_article, level=level)
        
        # Create response
        return {
            "type": "summary",
            "title": parsed_article.get("title", title),
            "level": level,
            "summary": summary,
            "url": parsed_article.get("url", "")
        }
    except Exception as e:
        raise Exception(str(e))

@mcp.tool()
def wikipedia_citations(title: str) -> Dict[str, Any]:
    """
    Get citations and references from a Wikipedia article.
    
    Args:
        title: The title of the Wikipedia article to get citations from
    
    Returns:
        Dictionary containing the article citations
    """
    try:
        # Get parsed article data
        parsed_article = get_parsed_article(title, True)
        
        # For disambiguation pages, just return as is
        if parsed_article.get("type") == "disambiguation":
            return parsed_article
        
        # Extract citations from parsed data
        citations = parsed_article.get("citations", [])
        
        # Create response
        return {
            "type": "citations",
            "title": parsed_article.get("title", title),
            "url": parsed_article.get("url", ""),
            "count": len(citations),
            "citations": citations
        }
    except Exception as e:
        raise Exception(str(e))

@mcp.tool()
def wikipedia_structured(title: str) -> Dict[str, Any]:
    """
    Get structured data (tables, infobox) from a Wikipedia article.
    
    Args:
        title: The title of the Wikipedia article to get structured data from
    
    Returns:
        Dictionary containing structured data from the article
    """
    try:
        # Get parsed article data
        parsed_article = get_parsed_article(title, True)
        
        # For disambiguation pages, just return as is
        if parsed_article.get("type") == "disambiguation":
            return parsed_article
        
        # Extract structured data from parsed data
        tables = parsed_article.get("tables", [])
        infobox = parsed_article.get("infobox", {})
        
        # Create response
        return {
            "type": "structured",
            "title": parsed_article.get("title", title),
            "url": parsed_article.get("url", ""),
            "tables": tables,
            "infobox": infobox,
            "tables_count": len(tables)
        }
    except Exception as e:
        raise Exception(str(e))

@mcp.tool()
def wikipedia_sections(title: str) -> Dict[str, Any]:
    """
    Get the section structure and content from a Wikipedia article.
    
    Args:
        title: The title of the Wikipedia article to get sections from
    
    Returns:
        Dictionary containing sections from the article
    """
    try:
        # Get parsed article data
        parsed_article = get_parsed_article(title, True)
        
        # For disambiguation pages, just return as is
        if parsed_article.get("type") == "disambiguation":
            return parsed_article
        
        # Extract sections from parsed data
        sections = parsed_article.get("sections", [])
        
        # Create response
        return {
            "type": "sections",
            "title": parsed_article.get("title", title),
            "url": parsed_article.get("url", ""),
            "count": len(sections),
            "sections": sections
        }
    except Exception as e:
        raise Exception(str(e))

# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start the Wikipedia MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--cache-type", choices=["ttl", "lru", "persist"], default="ttl",
                      help="Type of cache to use")
    parser.add_argument("--cache-ttl", type=int, default=3600,
                      help="Time-to-live for cache entries in seconds")
    parser.add_argument("--cache-maxsize", type=int, default=1000,
                      help="Maximum number of items in the cache")
    parser.add_argument("--cache-dir", help="Directory for persistent cache")
    parser.add_argument("--rate-limit", type=float, default=1.0,
                      help="Delay between Wikipedia API requests in seconds")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["CACHE_TYPE"] = args.cache_type
    os.environ["CACHE_TTL"] = str(args.cache_ttl)
    os.environ["CACHE_MAXSIZE"] = str(args.cache_maxsize)
    os.environ["RATE_LIMIT"] = str(args.rate_limit)
    
    if args.cache_dir:
        os.environ["CACHE_DIR"] = args.cache_dir
    
    # Run the server
    debug_log(f"Starting Wikipedia MCP API on {args.host}:{args.port}")
    debug_log(f"Cache: {args.cache_type} (TTL: {args.cache_ttl}s, Max Size: {args.cache_maxsize})")
    debug_log(f"Rate Limit: {args.rate_limit}s between requests")
    
    mcp.run(host=args.host, port=args.port) 