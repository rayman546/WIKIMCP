"""
Security middleware and utilities.
"""
import logging
import time
from typing import Callable, Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings
from .models import RateLimitError

# Setup logging
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(
        self,
        app: FastAPI,
        rate_limit: float = settings.RATE_LIMIT,
        window_size: int = 1
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            rate_limit: Requests per second per IP
            window_size: Time window in seconds
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_size = window_size
        self.requests: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        current_time = time.time()
        if not self._check_rate_limit(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise RateLimitError()
        
        # Call next middleware/handler
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, client_ip, current_time)
        
        return response
    
    def _check_rate_limit(self, client_ip: str, current_time: float) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            client_ip: Client IP address
            current_time: Current timestamp
            
        Returns:
            Whether request is allowed
        """
        # Get request times for this IP
        ip_times = self.requests.get(client_ip, [])
        
        # Remove old requests outside window
        cutoff = current_time - self.window_size
        ip_times = [t for t in ip_times if t > cutoff]
        
        # Check rate limit
        if len(ip_times) >= self.rate_limit:
            return False
        
        # Add current request
        ip_times.append(current_time)
        self.requests[client_ip] = ip_times
        
        return True
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str, current_time: float) -> None:
        """
        Add rate limit headers to response.
        
        Args:
            response: FastAPI response
            client_ip: Client IP address
            current_time: Current timestamp
        """
        # Get request times for this IP
        ip_times = self.requests.get(client_ip, [])
        
        # Calculate remaining requests
        remaining = max(0, self.rate_limit - len(ip_times))
        
        # Add headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https:;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

def setup_security(app: FastAPI) -> None:
    """
    Setup security middleware for FastAPI application.
    
    Args:
        app: FastAPI application
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        rate_limit=settings.RATE_LIMIT
    )
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Security middleware configured") 