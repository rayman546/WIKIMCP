import os
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from enum import Enum

from .wikipedia_client import WikipediaClient
from .caching_service import CachingService, cached
from .parser import WikipediaParser

# Load environment variables
CACHE_TYPE = os.getenv("CACHE_TYPE", "ttl")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "1000"))
CACHE_DIR = os.getenv("CACHE_DIR", None)
RATE_LIMIT = float(os.getenv("RATE_LIMIT", "1.0"))

# Create router
router = APIRouter(tags=["Wikipedia"])

# Define enum for level parameter validation
class SummaryLevel(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

# Initialize services (will be dependency injected)
def get_wikipedia_client() -> WikipediaClient:
    return WikipediaClient(rate_limit_delay=RATE_LIMIT)

def get_cache_service() -> CachingService:
    return CachingService(
        cache_type=CACHE_TYPE,
        maxsize=CACHE_MAXSIZE,
        ttl=CACHE_TTL,
        cache_dir=CACHE_DIR
    )

# Routes
@router.get("/search", response_model=Dict[str, Any])
async def search_wikipedia(
    term: str = Query(..., description="Search term"),
    results: int = Query(10, description="Number of results to return", ge=1, le=50),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Search for Wikipedia articles matching the term.
    
    Args:
        term: Search term
        results: Number of results to return (1-50)
        
    Returns:
        List of matching article titles
    """
    try:
        # Create cache decorator
        cached_search = cached(cache_service, key_prefix="search")(wiki_client.search)
        
        # Perform search
        search_results = cached_search(term, results=results)
        
        return {
            "query": term,
            "results": search_results,
            "count": len(search_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/article", response_model=Dict[str, Any])
async def get_article(
    title: str = Query(..., description="Article title"),
    auto_suggest: bool = Query(True, description="Whether to auto-suggest similar titles"),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Get a Wikipedia article by title.
    
    Args:
        title: Article title
        auto_suggest: Whether to auto-suggest similar titles
        
    Returns:
        Formatted article data
    """
    try:
        # Create cache decorator
        cached_get_article = cached(cache_service, key_prefix="article")(wiki_client.get_article)
        
        # Get article data
        article_data = cached_get_article(title, auto_suggest=auto_suggest)
        
        # Format for LLM consumption
        formatted_data = WikipediaParser.format_for_llm(article_data)
        
        return formatted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=Dict[str, Any])
async def get_summary(
    title: str = Query(..., description="Article title"),
    level: SummaryLevel = Query(SummaryLevel.MEDIUM, description="Detail level (short, medium, long)"),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Get a summary of a Wikipedia article.
    
    Args:
        title: Article title
        level: Detail level (short, medium, long)
        
    Returns:
        Article summary
    """
    try:
        # Create cache decorator for get_article
        cached_get_article = cached(cache_service, key_prefix="article")(wiki_client.get_article)
        
        # Create cache key for the summary
        cache_key = f"summary:{title}:{level}"
        
        # Try to get from cache first
        cached_summary = cache_service.get(cache_key)
        if cached_summary:
            return cached_summary
        
        # Get article data
        article_data = cached_get_article(title)
        
        # Handle disambiguation pages
        if "error" in article_data and article_data["error"] == "disambiguation":
            return {
                "type": "disambiguation",
                "title": title,
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }
        
        # Generate summary
        summary = WikipediaParser.generate_summary(article_data, level=level)
        
        # Create response
        response = {
            "type": "summary",
            "title": article_data.get("title", title),
            "level": level,
            "summary": summary,
            "url": article_data.get("url", "")
        }
        
        # Cache the result
        cache_service.set(cache_key, response)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/citations", response_model=Dict[str, Any])
async def get_citations(
    title: str = Query(..., description="Article title"),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Get citations from a Wikipedia article.
    
    Args:
        title: Article title
        
    Returns:
        List of citations
    """
    try:
        # Create cache decorator
        cached_get_article = cached(cache_service, key_prefix="article")(wiki_client.get_article)
        
        # Create cache key for citations
        cache_key = f"citations:{title}"
        
        # Try to get from cache first
        cached_citations = cache_service.get(cache_key)
        if cached_citations:
            return cached_citations
        
        # Get article data
        article_data = cached_get_article(title)
        
        # Handle disambiguation pages
        if "error" in article_data and article_data["error"] == "disambiguation":
            return {
                "type": "disambiguation",
                "title": title,
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }
        
        # Extract citations
        html_content = article_data.get("html", "")
        citations = WikipediaParser.extract_citations(html_content)
        
        # Create response
        response = {
            "type": "citations",
            "title": article_data.get("title", title),
            "url": article_data.get("url", ""),
            "count": len(citations),
            "citations": citations
        }
        
        # Cache the result
        cache_service.set(cache_key, response)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/structured", response_model=Dict[str, Any])
async def get_structured(
    title: str = Query(..., description="Article title"),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Get structured data (tables, infobox) from a Wikipedia article.
    
    Args:
        title: Article title
        
    Returns:
        Structured data
    """
    try:
        # Create cache decorator
        cached_get_article = cached(cache_service, key_prefix="article")(wiki_client.get_article)
        
        # Create cache key for structured data
        cache_key = f"structured:{title}"
        
        # Try to get from cache first
        cached_structured = cache_service.get(cache_key)
        if cached_structured:
            return cached_structured
        
        # Get article data
        article_data = cached_get_article(title)
        
        # Handle disambiguation pages
        if "error" in article_data and article_data["error"] == "disambiguation":
            return {
                "type": "disambiguation",
                "title": title,
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }
        
        # Extract structured data
        html_content = article_data.get("html", "")
        tables = WikipediaParser.extract_tables(html_content)
        infobox = WikipediaParser.extract_infobox(html_content)
        
        # Create response
        response = {
            "type": "structured",
            "title": article_data.get("title", title),
            "url": article_data.get("url", ""),
            "tables": tables,
            "tables_count": len(tables),
            "infobox": infobox
        }
        
        # Cache the result
        cache_service.set(cache_key, response)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 