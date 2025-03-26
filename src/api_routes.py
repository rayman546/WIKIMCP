import os
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from enum import Enum

from .wikipedia_client import WikipediaClient, ArticleNotFoundError
from .caching_service import CachingService, cached
from .parser import WikipediaParser

# Setup logging
logger = logging.getLogger(__name__)

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

# Helper functions
def handle_disambiguation(article_data: Dict[str, Any], title: str) -> Dict[str, Any]:
    """Handle disambiguation pages consistently across endpoints."""
    if "error" in article_data and article_data["error"] == "disambiguation":
        return {
            "type": "disambiguation",
            "title": title,
            "options": article_data.get("options", []),
            "message": article_data.get("message", "")
        }
    return None

def get_parsed_article(title: str, auto_suggest: bool, wiki_client: WikipediaClient, cache_service: CachingService) -> Dict[str, Any]:
    """
    Central function to get and parse a Wikipedia article.
    
    Args:
        title: Article title
        auto_suggest: Whether to auto-suggest similar titles
        wiki_client: WikipediaClient instance
        cache_service: CachingService instance
        
    Returns:
        Parsed article data
    """
    # Create cache key for the parsed article
    cache_key = f"parsed_article:{title}"
    
    # Try to get from cache first
    cached_article = cache_service.get(cache_key)
    if cached_article:
        return cached_article
    
    try:
        # Get raw article data
        cached_get_article = cached(cache_service, key_prefix="raw_article")(wiki_client.get_article)
        raw_article_data = cached_get_article(title, auto_suggest=auto_suggest)
        
        # Check for disambiguation
        disambiguation = handle_disambiguation(raw_article_data, title)
        if disambiguation:
            return disambiguation
        
        # Parse the article
        parsed_article = WikipediaParser.parse_article(raw_article_data)
        
        # Cache the parsed result
        cache_service.set(cache_key, parsed_article)
        
        return parsed_article
    except ArticleNotFoundError as e:
        logger.warning(f"Article not found: {title}")
        raise HTTPException(status_code=404, detail=f"Article not found: {title}")
    except Exception as e:
        logger.error(f"Error retrieving article: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving article: {str(e)}")

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
        logger.error(f"Search error: {str(e)}")
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
    return get_parsed_article(title, auto_suggest, wiki_client, cache_service)

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
    # Get parsed article data
    parsed_article = get_parsed_article(title, True, wiki_client, cache_service)
    
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
    # Get parsed article data
    parsed_article = get_parsed_article(title, True, wiki_client, cache_service)
    
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
    # Get parsed article data
    parsed_article = get_parsed_article(title, True, wiki_client, cache_service)
    
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

@router.get("/sections", response_model=Dict[str, Any])
async def get_sections(
    title: str = Query(..., description="Article title"),
    wiki_client: WikipediaClient = Depends(get_wikipedia_client),
    cache_service: CachingService = Depends(get_cache_service)
):
    """
    Get sections from a Wikipedia article.
    
    Args:
        title: Article title
        
    Returns:
        List of sections with content
    """
    # Get parsed article data
    parsed_article = get_parsed_article(title, True, wiki_client, cache_service)
    
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