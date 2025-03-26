import os
import json
import time
from typing import Dict, Any, Optional, Callable
from cachetools import TTLCache, LRUCache

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
        elif self.cache_type == "lru":
            self.cache = LRUCache(maxsize=maxsize)
        elif self.cache_type == "persist":
            self.cache = {}
            self._load_persistent_cache()
        else:
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
                return self.cache.get(key)
            elif self.cache_type == "persist":
                # Check if item exists and is not expired
                if key in self.cache:
                    item = self.cache[key]
                    if "expiry" not in item or item["expiry"] > time.time():
                        return item["value"]
                    else:
                        # Item is expired, remove it
                        del self.cache[key]
                        self._save_persistent_cache()
                return None
        except Exception as e:
            print(f"Cache get error: {str(e)}")
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
            elif self.cache_type == "persist":
                expiry = time.time() + (ttl if ttl is not None else self.ttl)
                self.cache[key] = {"value": value, "expiry": expiry}
                self._save_persistent_cache()
        except Exception as e:
            print(f"Cache set error: {str(e)}")
    
    def invalidate(self, key: str) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key to invalidate
        """
        try:
            if key in self.cache:
                del self.cache[key]
                if self.cache_type == "persist":
                    self._save_persistent_cache()
        except Exception as e:
            print(f"Cache invalidation error: {str(e)}")
    
    def clear(self) -> None:
        """Clear the entire cache."""
        try:
            if self.cache_type in ["ttl", "lru"]:
                self.cache.clear()
            elif self.cache_type == "persist":
                self.cache = {}
                self._save_persistent_cache()
        except Exception as e:
            print(f"Cache clear error: {str(e)}")
    
    def _get_cache_file_path(self) -> str:
        """Get the path to the persistent cache file."""
        if not self.cache_dir:
            self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
        
        os.makedirs(self.cache_dir, exist_ok=True)
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
                
                # Clean expired entries on load
                current_time = time.time()
                expired_keys = [
                    key for key, item in self.cache.items() 
                    if "expiry" in item and item["expiry"] <= current_time
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    self._save_persistent_cache()
        except Exception as e:
            print(f"Error loading persistent cache: {str(e)}")
            self.cache = {}
    
    def _save_persistent_cache(self) -> None:
        """Save cache to disk for persistent cache."""
        if self.cache_type != "persist":
            return
            
        try:
            cache_file = self._get_cache_file_path()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving persistent cache: {str(e)}")

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