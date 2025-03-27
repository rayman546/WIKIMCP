"""
Configuration management for the Wikipedia MCP API.
Uses Pydantic's BaseSettings for environment variable loading and validation.
"""
from typing import Optional
from pydantic import BaseSettings, Field, validator
from enum import Enum


class CacheType(str, Enum):
    """Supported cache types."""
    TTL = "ttl"
    LRU = "lru"
    PERSIST = "persist"
    DISK = "disk"  # New disk-based cache option


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(default=8000, description="Port to bind the server to")
    RELOAD: bool = Field(default=True, description="Enable auto-reload in development")
    DEBUG: bool = Field(default=False, description="Enable debug mode (e.g., for docs UI)") # Added missing DEBUG setting
    
    # Cache settings
    CACHE_TYPE: CacheType = Field(default=CacheType.TTL, description="Type of cache to use")
    CACHE_TTL: int = Field(default=3600, description="Time-to-live for cache entries in seconds")
    CACHE_MAXSIZE: int = Field(default=1000, description="Maximum number of items in the cache")
    CACHE_DIR: Optional[str] = Field(default=None, description="Directory for persistent or disk cache")

    # Wikipedia Client settings
    WIKIPEDIA_RATE_LIMIT: float = Field(default=1.0, description="Delay between Wikipedia API requests in seconds")

    # API Rate Limiting settings
    API_RATE_LIMIT: int = Field(default=10, description="Number of allowed requests per window per client IP")
    API_RATE_LIMIT_WINDOW: int = Field(default=1, description="Time window in seconds for API rate limiting")

    # Security settings
    API_KEY: str = Field(description="Required API key for accessing protected endpoints") # Added missing API_KEY

    # CORS settings
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="List of allowed CORS origins. Use ['*'] for development only."
    )
    
    # Logging settings
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    @validator("CACHE_TTL")
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache TTL is positive."""
        if v <= 0:
            raise ValueError("CACHE_TTL must be positive")
        return v
    
    @validator("CACHE_MAXSIZE")
    def validate_cache_maxsize(cls, v: int) -> int:
        """Validate cache max size is positive."""
        if v <= 0:
            raise ValueError("CACHE_MAXSIZE must be positive")
        return v

    @validator("WIKIPEDIA_RATE_LIMIT")
    def validate_wikipedia_rate_limit(cls, v: float) -> float:
        """Validate Wikipedia rate limit is non-negative."""
        # Allow 0 for no delay, but not negative
        if v < 0:
            raise ValueError("WIKIPEDIA_RATE_LIMIT cannot be negative")
        return v

    @validator("API_RATE_LIMIT")
    def validate_api_rate_limit(cls, v: int) -> int:
        """Validate API rate limit is positive."""
        if v <= 0:
            raise ValueError("API_RATE_LIMIT must be positive")
        return v

    @validator("API_RATE_LIMIT_WINDOW")
    def validate_api_rate_limit_window(cls, v: int) -> int:
        """Validate API rate limit window is positive."""
        if v <= 0:
            raise ValueError("API_RATE_LIMIT_WINDOW must be positive")
        return v

    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins."""
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot mix '*' with other origins")
        return v
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
