"""
API routes for the Wikipedia MCP API.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from .models import (
    ArticleResponse,
    SearchResponse,
    StatsResponse,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ParsingError,
    WikipediaError,
    CacheError
)
from .api_utils import (
    create_error_response,
    create_success_response,
    add_cors_headers,
    add_security_headers,
    log_request,
    get_cache_info
)
from .wikipedia_client import WikipediaClient
from .caching_service import CachingService
from .parser import WikipediaParser
from .config import settings
from .models import APIError # Import APIError base class

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency functions to get singletons from app.state
def get_wikipedia_client_instance(request: Request) -> WikipediaClient:
    """Get singleton Wikipedia client instance from app state."""
    return request.app.state.wikipedia_client

def get_cache_service_instance(request: Request) -> CachingService:
    """Get singleton cache service instance from app state."""
    return request.app.state.cache_service

def get_parser_instance(request: Request) -> WikipediaParser:
    """Get singleton parser instance from app state."""
    return request.app.state.parser

@router.get("/article/{title}")
async def get_article(
    request: Request,
    response: Response,
    title: str,
    # Removed unused parameters: sections, images, references
    wikipedia: WikipediaClient = Depends(get_wikipedia_client_instance),
    cache: CachingService = Depends(get_cache_service_instance),
    parser: WikipediaParser = Depends(get_parser_instance)
) -> ArticleResponse:
    """
    Get Wikipedia article by title.
    
    Args:
        request: FastAPI request
        response: FastAPI response
        title: Article title
        # Removed unused parameters from docstring
        wikipedia: Wikipedia client
        cache: Cache service
        parser: Wikipedia parser

    Returns:
        Article response
    """
    # Increment request counter
    request.app.state.api_stats["requests"] += 1
    try:
        # Check cache first (Cache key simplified as params are removed)
        cache_key = f"article:{title}"
        cached_article = cache.get(cache_key)
        if cached_article:
            logger.debug(f"Cache hit for article: {title}")
            return create_success_response(
                {
                    "article": cached_article,
                    "cache_info": get_cache_info(request, hit=True)
                },
                ArticleResponse
            )
        logger.debug(f"Cache miss for article: {title}")

        # Get article from Wikipedia using executor for sync call
        article = await request.app.loop.run_in_executor(
            None, wikipedia.get_article, title
        )

        # Handle disambiguation or not found directly from client
        # (Will refactor client to raise specific errors later)
        if isinstance(article, dict) and article.get("error") == "disambiguation":
             # TODO: Refactor client to raise DisambiguationAPIError
             raise ValidationError("Disambiguation error", details={"options": article.get("options", [])})
        if not article: # Should be handled by client raising NotFoundError
             raise NotFoundError(f"Article not found: {title}")

        # Parse article using executor for sync call
        # TODO: Pass sections, images, references if parser supports them
        parsed = await request.app.loop.run_in_executor(
            None, parser.parse_article, article
        )

        # Cache the parsed result
        cache.set(cache_key, parsed)

        # Create response
        return create_success_response(
            {
                "article": parsed,
                "cache_info": get_cache_info(request, hit=False)
            },
            ArticleResponse
        )

    except APIError as e:
        # Increment error counter for known API errors
        request.app.state.api_stats["errors"] += 1
        logger.warning(f"API Error getting article '{title}': {e.code} - {e.message}")
        raise e # Re-raise to be handled by the exception handler
    except Exception as e:
        # Increment error counter for unexpected errors
        request.app.state.api_stats["errors"] += 1
        logger.error(f"Unexpected error getting article '{title}': {str(e)}", exc_info=True)
        # Wrap unexpected errors in a generic APIError
        raise WikipediaError(f"An unexpected error occurred: {str(e)}")
    # finally block removed - headers/logging can be handled by middleware or dependencies

@router.get("/search")
async def search_articles(
    request: Request,
    response: Response,
    query: str,
    limit: Optional[int] = 10,
    wikipedia: WikipediaClient = Depends(get_wikipedia_client_instance),
    cache: CachingService = Depends(get_cache_service_instance)
) -> SearchResponse:
    """
    Search Wikipedia articles.
    
    Args:
        request: FastAPI request
        response: FastAPI response
        query: Search query
        limit: Maximum number of results
        wikipedia: Wikipedia client
        cache: Cache service

    Returns:
        Search response
    """
    # Increment request counter
    request.app.state.api_stats["requests"] += 1
    try:
        # Validate input
        if not query:
            raise ValidationError("Search query is required")
        if not 1 <= limit <= 50:
            raise ValidationError("Limit must be between 1 and 50")

        # Check cache first
        cache_key = f"search:{query}:{limit}"
        cached_results = cache.get(cache_key)
        if cached_results:
             logger.debug(f"Cache hit for search: {query}")
             return create_success_response(
                 {
                     "query": query,
                     "results": cached_results, # Assuming cached_results matches SearchResult model
                     "total": len(cached_results),
                     "cache_info": get_cache_info(request, hit=True)
                 },
                 SearchResponse
             )
        logger.debug(f"Cache miss for search: {query}")

        # Search articles using executor for sync call
        results = await request.app.loop.run_in_executor(
            None, wikipedia.search, query, limit=limit
        )

        # Format results to match the simplified SearchResult model (title only)
        search_results_formatted = [{"title": title} for title in results]

        # Cache the formatted results
        cache.set(cache_key, search_results_formatted)

        # Create response using the formatted results
        return create_success_response(
            {
                "query": query,
                "results": search_results_formatted, # Use the formatted list
                "total": len(search_results_formatted),
                "cache_info": get_cache_info(request, hit=False)
            },
            SearchResponse
        )

    except APIError as e:
        request.app.state.api_stats["errors"] += 1
        logger.warning(f"API Error searching articles '{query}': {e.code} - {e.message}")
        raise e
    except Exception as e:
        request.app.state.api_stats["errors"] += 1
        logger.error(f"Unexpected error searching articles '{query}': {str(e)}", exc_info=True)
        raise WikipediaError(f"An unexpected error occurred during search: {str(e)}")
    # finally block removed

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    request: Request,
    response: Response,
    cache: CachingService = Depends(get_cache_service_instance)
) -> StatsResponse: # Return type hint should match response_model if used
    """
    Get API statistics.
    
    Args:
        request: FastAPI request
        response: FastAPI response
        cache: Cache service

    Returns:
        Statistics response
    """
    # Increment request counter
    request.app.state.api_stats["requests"] += 1
    try:
        # Get cache stats
        cache_stats = cache.get_stats()

        # Get API stats directly from app state
        api_stats = request.app.state.api_stats

        # Create response (using the model directly for validation)
        response_data = StatsResponse(
             cache=cache_stats,
             api=api_stats
        )
        # Return the Pydantic model instance, FastAPI handles serialization
        return response_data

    except APIError as e:
        request.app.state.api_stats["errors"] += 1
        logger.warning(f"API Error getting stats: {e.code} - {e.message}")
        raise e
    except Exception as e:
        request.app.state.api_stats["errors"] += 1
        logger.error(f"Unexpected error getting stats: {str(e)}", exc_info=True)
        raise CacheError(f"An unexpected error occurred while getting stats: {str(e)}")
    # finally block removed

@router.exception_handler(APIError)
async def api_error_handler(request: Request, error: APIError) -> JSONResponse:
    """Handle API errors."""
    return create_error_response(error)
