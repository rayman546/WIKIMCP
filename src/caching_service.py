import os
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
from cachetools import TTLCache, LRUCache

# Setup logging
logger = logging.getLogger(__name__)

class CachingService:
    """Service for caching Wikipedia API responses."""
    
    def __init__(
        self, 
        cache_type: str = "ttl", 
        maxsize: int = 1000, 
        ttl: int = 3600,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the caching service.
        
        Args:
            cache_type: Type of cache to use ('ttl', 'lru', or 'persist')
            maxsize: Maximum number of items in the cache
            ttl: Time-to-live for cache entries in seconds (for TTL cache)
            cache_dir: Directory for persistent cache (if cache_type is 'persist')
        """
        self.cache_type = cache_type
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache_dir = cache_dir
        
        # Initialize in-memory cache
        if self.cache_type == "ttl":
            self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
            logger.info(f"Initialized TTL cache with maxsize={maxsize}, ttl={ttl}")
        elif self.cache_type == "lru":
            self.cache = LRUCache(maxsize=maxsize)
            logger.info(f"Initialized LRU cache with maxsize={maxsize}")
        elif self.cache_type == "persist":
            self.cache = {}
            self._load_persistent_cache()
            logger.info(f"Initialized persistent cache with maxsize={maxsize}, ttl={ttl}, dir={self.cache_dir}")
        else:
            logger.error(f"Unsupported cache type: {cache_type}")
            raise ValueError(f"Unsupported cache type: {cache_type}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            if self.cache_type in ["ttl", "lru"]:
                value = self.cache.get(key)
                if value is not None:
                    logger.debug(f"Cache hit for key: {key}")
                else:
                    logger.debug(f"Cache miss for key: {key}")
                return value
            elif self.cache_type == "persist":
                # Check if item exists and is not expired
                if key in self.cache:
                    item = self.cache[key]
                    if "expiry" not in item or item["expiry"] > time.time():
                        logger.debug(f"Cache hit for key: {key}")
                        return item["value"]
                    else:
                        # Item is expired, remove it
                        logger.debug(f"Cache item expired for key: {key}")
                        del self.cache[key]
                        self._save_persistent_cache()
                else:
                    logger.debug(f"Cache miss for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL (overrides default)
        """
        try:
            if self.cache_type in ["ttl", "lru"]:
                self.cache[key] = value
                logger.debug(f"Cached value for key: {key}")
            elif self.cache_type == "persist":
                expiry = time.time() + (ttl if ttl is not None else self.ttl)
                self.cache[key] = {"value": value, "expiry": expiry}
                logger.debug(f"Cached value for key: {key} with expiry: {expiry}")
                self._save_persistent_cache()
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
    
    def invalidate(self, key: str) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key to invalidate
        """
        try:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Invalidated cache for key: {key}")
                if self.cache_type == "persist":
                    self._save_persistent_cache()
        except Exception as e:
            logger.error(f"Cache invalidation error for key {key}: {str(e)}")
    
    def clear(self) -> None:
        """Clear the entire cache."""
        try:
            if self.cache_type in ["ttl", "lru"]:
                self.cache.clear()
            elif self.cache_type == "persist":
                self.cache = {}
                self._save_persistent_cache()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
    
    def _get_cache_file_path(self) -> str:
        """Get the path to the persistent cache file."""
        if not self.cache_dir:
            self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
        
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.debug(f"Using cache directory: {self.cache_dir}")
        return os.path.join(self.cache_dir, "wikipedia_cache.json")
    
    def _load_persistent_cache(self) -> None:
        """Load cache from disk for persistent cache."""
        if self.cache_type != "persist":
            return
            
        try:
            cache_file = self._get_cache_file_path()
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                
                logger.info(f"Loaded {len(self.cache)} items from persistent cache")
                
                # Clean expired entries on load
                current_time = time.time()
                expired_keys = [
                    key for key, item in self.cache.items() 
                    if "expiry" in item and item["expiry"] <= current_time
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    logger.info(f"Removed {len(expired_keys)} expired items from persistent cache")
                    self._save_persistent_cache()
            else:
                logger.info("No persistent cache file found, starting with empty cache")
        except Exception as e:
            logger.error(f"Error loading persistent cache: {str(e)}")
            self.cache = {}
    
    def _save_persistent_cache(self) -> None:
        """Save cache to disk for persistent cache."""
        if self.cache_type != "persist":
            return
            
        try:
            cache_file = self._get_cache_file_path()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
            logger.debug(f"Saved {len(self.cache)} items to persistent cache")
        except Exception as e:
            logger.error(f"Error saving persistent cache: {str(e)}")

# Decorator for caching function results
def cached(
    cache_service: CachingService,
    key_prefix: str = "",
    key_func: Optional[Callable] = None,
    ttl: Optional[int] = None
):
    """
    Decorator for caching function results.
    
    Args:
        cache_service: CachingService instance
        key_prefix: Prefix for cache keys
        key_func: Function to generate cache key from arguments
        ttl: Custom TTL for cache entries
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                arg_str = ",".join(str(arg) for arg in args)
                kwarg_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func.__name__}:{arg_str}:{kwarg_str}"
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            return result
        
        return wrapper
    
    return decorator 