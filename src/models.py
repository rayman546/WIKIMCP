"""
Response models and error handling for the Wikipedia MCP API.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field("error", const=True)
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class SuccessResponse(BaseModel):
    """Base success response model."""
    status: str = Field("success", const=True)
    message: Optional[str] = Field(None, description="Optional success message")

class WikipediaArticle(BaseModel):
    """Wikipedia article model."""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    content: str = Field(..., description="Article content")
    sections: List[str] = Field(default_factory=list, description="Article sections")
    images: List[str] = Field(default_factory=list, description="Article images")
    references: List[str] = Field(default_factory=list, description="Article references")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Article metadata")

class ArticleResponse(SuccessResponse):
    """Article response model."""
    article: WikipediaArticle = Field(..., description="Wikipedia article data")
    cache_info: Optional[Dict[str, Any]] = Field(None, description="Cache information")

class SearchResult(BaseModel):
    """Search result model (Simplified to match client capabilities)."""
    title: str = Field(..., description="Article title")
    # Removed url, snippet, score as they are not provided by the client

class SearchResponse(SuccessResponse):
    """Search response model (Simplified)."""
    query: str = Field(..., description="Search query")
    results: List[SearchResult] = Field(..., description="Search results (titles only)") # Updated description
    total: int = Field(..., description="Total number of results")
    cache_info: Optional[Dict[str, Any]] = Field(None, description="Cache information")

class CacheStats(BaseModel):
    """Cache statistics model."""
    hits: int = Field(..., description="Number of cache hits")
    misses: int = Field(..., description="Number of cache misses")
    size: int = Field(..., description="Current cache size")
    max_size: int = Field(..., description="Maximum cache size")
    type: str = Field(..., description="Cache type")

class StatsResponse(SuccessResponse):
    """Statistics response model."""
    cache: CacheStats = Field(..., description="Cache statistics")
    api: Dict[str, Any] = Field(..., description="API statistics")

# Error codes and messages
class APIError(Exception):
    """Base API error."""
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class NotFoundError(APIError):
    """Resource not found error."""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NOT_FOUND", 404, details)

class ValidationError(APIError):
    """Input validation error."""
    def __init__(self, message: str = "Invalid input", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, details)

class RateLimitError(APIError):
    """Rate limit exceeded error."""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", 429, details)

class ParsingError(APIError):
    """Article parsing error."""
    def __init__(self, message: str = "Failed to parse article", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PARSING_ERROR", 500, details)

class WikipediaError(APIError):
    """Wikipedia API error."""
    def __init__(self, message: str = "Wikipedia API error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "WIKIPEDIA_ERROR", 502, details)

class CacheError(APIError):
    """Cache operation error."""
    def __init__(self, message: str = "Cache error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CACHE_ERROR", 500, details)

class DisambiguationAPIError(APIError):
    """Disambiguation error when multiple articles match."""
    def __init__(self, message: str = "Multiple articles found", options: List[str] = [], details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["options"] = options # Add options to details
        super().__init__(message, "DISAMBIGUATION_ERROR", 400, details) # Use 400 Bad Request
