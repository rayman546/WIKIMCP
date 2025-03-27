"""
Caching service for the Wikipedia MCP API.
"""
import asyncio # Import asyncio
import os
import json
import logging
import functools
from typing import Any, Optional, Callable
import aiofiles # Import aiofiles
from cachetools import TTLCache, LRUCache
from diskcache import Cache as DiskCacheCache # Rename to avoid conflict
from .config import settings, CacheType

# Setup logging
logger = logging.getLogger(__name__)

class CachingService:
    """Service for caching API responses."""
    
    def __init__(
        self,
        cache_type: CacheType = settings.CACHE_TYPE,
        ttl: int = settings.CACHE_TTL,
        maxsize: int = settings.CACHE_MAXSIZE,
        cache_dir: Optional[str] = settings.CACHE_DIR
    ):
        """
        Initialize the caching service.
        
        Args:
            cache_type: Type of cache to use (ttl, lru, persist, disk)
            ttl: Time-to-live for cache entries in seconds
            maxsize: Maximum number of items in the cache
            cache_dir: Directory for persistent cache
        """
        self.cache_type = cache_type
        self.ttl = ttl
        self.maxsize = maxsize
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), ".cache")
        self.cache = None # Initialize cache attribute

        # Create cache based on type
        if cache_type == CacheType.TTL:
            self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        elif cache_type == CacheType.LRU:
            self.cache = LRUCache(maxsize=maxsize)
        elif cache_type == CacheType.DISK:
            # Use diskcache for disk-based caching
            os.makedirs(self.cache_dir, exist_ok=True)
            # Correct size_limit interpretation (it's in bytes)
            self.cache = DiskCacheCache(
                directory=self.cache_dir,
                size_limit=maxsize * 1024 * 1024, # Assuming maxsize is in MB
                eviction_policy="least-recently-used",
                statistics=True
            )
        elif cache_type == CacheType.PERSIST:
            # Legacy JSON-based persistent cache (in-memory dict)
            self.cache = {}
            self.cache_file = os.path.join(self.cache_dir, "cache.json")
            # Loading is now done asynchronously via initialize method
        else:
            raise ValueError(f"Invalid cache type: {cache_type}")

        logger.info(f"Initialized {cache_type.value} cache config (TTL={ttl}s, maxsize={maxsize})")

    async def initialize(self):
        """Asynchronously initialize the cache, e.g., load from disk."""
        if self.cache_type == CacheType.PERSIST:
            await self._load_cache()
        logger.info(f"Cache Service initialized ({self.cache_type.value}).")


    async def get(self, key: str) -> Any:
        """Get a value from the cache (async)."""
        loop = asyncio.get_running_loop()
        try:
            if self.cache_type == CacheType.DISK:
                # Run blocking diskcache get in executor
                return await loop.run_in_executor(None, self.cache.get, key)
            elif self.cache_type == CacheType.PERSIST:
                 # In-memory dict access is fast, no executor needed
                return self.cache.get(key)
            else: # TTL, LRU (cachetools) are also in-memory
                # cachetools get might expire item, potentially blocking? Check docs.
                # Assuming quick enough for now.
                return self.cache.get(key)
        except Exception as e:
            logger.error(f"Error getting from cache (key: {key}): {str(e)}", exc_info=True)
            return None

    async def set(self, key: str, value: Any) -> None:
        """Set a value in the cache (async)."""
        loop = asyncio.get_running_loop()
        try:
            if self.cache_type == CacheType.DISK:
                # Run blocking diskcache set in executor
                await loop.run_in_executor(None, self.cache.set, key, value)
            elif self.cache_type == CacheType.PERSIST:
                # In-memory dict access is fast
                self.cache[key] = value
                # REMOVED sync save: self._save_cache()
            else: # TTL, LRU
                # Assuming cachetools set is quick enough
                self.cache[key] = value
        except Exception as e:
            logger.error(f"Error setting cache value (key: {key}): {str(e)}", exc_info=True)

    async def delete(self, key: str) -> None:
        """Delete a value from the cache (async)."""
        loop = asyncio.get_running_loop()
        try:
            if self.cache_type == CacheType.DISK:
                # Run blocking diskcache delete in executor
                await loop.run_in_executor(None, self.cache.delete, key)
            elif self.cache_type == CacheType.PERSIST:
                if key in self.cache:
                    del self.cache[key]
                    # REMOVED sync save: self._save_cache()
            else: # TTL, LRU
                if key in self.cache:
                    # Assuming cachetools del is quick enough
                    del self.cache[key]
        except Exception as e:
            logger.error(f"Error deleting from cache (key: {key}): {str(e)}", exc_info=True)

    async def clear(self) -> None:
        """Clear all values from the cache (async)."""
        loop = asyncio.get_running_loop()
        try:
            if self.cache_type == CacheType.DISK:
                # Run blocking diskcache clear in executor
                await loop.run_in_executor(None, self.cache.clear)
            elif self.cache_type == CacheType.PERSIST:
                self.cache.clear()
                # REMOVED sync save: self._save_cache()
            else: # TTL, LRU
                self.cache.clear()
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}", exc_info=True)

    async def get_stats(self) -> dict:
        """Get cache statistics (async)."""
        loop = asyncio.get_running_loop()
        try:
            if self.cache_type == CacheType.DISK:
                # Run blocking diskcache stats in executor
                hits, misses = await loop.run_in_executor(None, self.cache.stats)
                # Run blocking diskcache size in executor
                size = await loop.run_in_executor(None, getattr, self.cache, 'size')
                return {
                    "hits": hits,
                    "misses": misses,
                    "size": size, # Size in bytes
                    "max_size": self.maxsize * 1024 * 1024, # Assuming maxsize is MB
                    "type": self.cache_type.value
                }
            else: # TTL, LRU, PERSIST (in-memory)
                # Assuming len() is quick enough
                return {
                    "size": len(self.cache),
                    "max_size": self.maxsize, # Max items for cachetools/persist
                    "type": self.cache_type.value,
                    # Add hits/misses if cachetools provides them easily
                    "hits": getattr(self.cache, 'hits', None),
                    "misses": getattr(self.cache, 'misses', None),
                }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}", exc_info=True)
            return {}

    async def _load_cache(self) -> None:
        """Load cache from disk for persistent cache (async)."""
        if self.cache_type != CacheType.PERSIST or not self.cache_file:
            return

        try:
            # Ensure directory exists (sync is ok here, happens once)
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            if os.path.exists(self.cache_file):
                logger.info(f"Loading persistent cache from {self.cache_file}")
                async with aiofiles.open(self.cache_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    # Run potentially blocking json.loads in executor
                    loop = asyncio.get_running_loop()
                    self.cache = await loop.run_in_executor(None, json.loads, content)
                    logger.info(f"Loaded {len(self.cache)} items from persistent cache.")
            else:
                 logger.info(f"Persistent cache file not found: {self.cache_file}")
                 self.cache = {}
        except Exception as e:
            logger.error(f"Error loading cache from disk ({self.cache_file}): {str(e)}", exc_info=True)
            self.cache = {} # Reset cache on error

    async def _save_cache(self) -> None:
        """Save cache to disk for persistent cache (async)."""
        if self.cache_type != CacheType.PERSIST or not self.cache_file:
            return

        logger.info(f"Saving persistent cache to {self.cache_file} ({len(self.cache)} items)")
        try:
            # Ensure directory exists (sync is ok here)
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
             # Run potentially blocking json.dumps in executor
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(None, json.dumps, self.cache, indent=2)
            async with aiofiles.open(self.cache_file, "w", encoding="utf-8") as f:
                await f.write(content)
            logger.info("Persistent cache saved successfully.")
        except Exception as e:
            logger.error(f"Error saving cache to disk ({self.cache_file}): {str(e)}", exc_info=True)

    # Removed __del__ method - cleanup handled in main.py shutdown

# Decorator needs to be async now
def cached(cache_service: CachingService, key_prefix: str = "") -> Callable:
    """
    Decorator for caching async function results.

    Args:
        cache_service: CachingService instance
        key_prefix: Prefix for cache keys

    Returns:
        Decorated async function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any: # Make wrapper async
            # TODO: Improve cache key generation (Phase 2)
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache (await the async get)
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # Call async function and cache result
            logger.debug(f"Cache miss for {cache_key}")
            result = await func(*args, **kwargs) # Await the original async function
            await cache_service.set(cache_key, result) # Await the async set

            return result
        return wrapper
    return decorator
