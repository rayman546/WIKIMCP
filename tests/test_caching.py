import pytest
import time
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

from src.caching_service import CachingService, cached

class TestCachingService:
    """Tests for the CachingService class."""
    
    def test_ttl_cache_basic(self):
        """Test basic TTL cache functionality."""
        cache = CachingService(cache_type="ttl", maxsize=10, ttl=10)
        
        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Non-existent key
        assert cache.get("nonexistent") is None
        
        # Invalidation
        cache.invalidate("key1")
        assert cache.get("key1") is None
        
        # Clear
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key2") is None
    
    def test_lru_cache_basic(self):
        """Test basic LRU cache functionality."""
        cache = CachingService(cache_type="lru", maxsize=2)
        
        # Set and get
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Test LRU eviction (key1 should be evicted)
        cache.set("key3", "value3")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_ttl_expiration(self):
        """Test TTL cache expiration."""
        cache = CachingService(cache_type="ttl", maxsize=10, ttl=1)
        
        # Set and immediately get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_persist_cache(self):
        """Test persistent cache functionality."""
        # Create a temporary directory for cache
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache
            cache = CachingService(cache_type="persist", maxsize=10, ttl=10, cache_dir=temp_dir)
            
            # Set values
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            
            # Verify cache file exists
            cache_file = os.path.join(temp_dir, "wikipedia_cache.json")
            assert os.path.exists(cache_file)
            
            # Check file content
            with open(cache_file, "r") as f:
                data = json.load(f)
                assert "key1" in data
                assert "key2" in data
                assert data["key1"]["value"] == "value1"
            
            # Create a new cache instance to test loading from disk
            cache2 = CachingService(cache_type="persist", maxsize=10, ttl=10, cache_dir=temp_dir)
            assert cache2.get("key1") == "value1"
            assert cache2.get("key2") == "value2"
            
            # Test invalidation
            cache2.invalidate("key1")
            assert cache2.get("key1") is None
            assert cache2.get("key2") == "value2"
            
            # Ensure invalidation is saved
            with open(cache_file, "r") as f:
                data = json.load(f)
                assert "key1" not in data
                assert "key2" in data
    
    def test_persist_cache_expiration(self):
        """Test persistent cache expiration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache with short TTL
            cache = CachingService(cache_type="persist", maxsize=10, ttl=1, cache_dir=temp_dir)
            
            # Set value
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"
            
            # Wait for expiration
            time.sleep(1.1)
            assert cache.get("key1") is None
            
            # Check file content after expiration
            cache_file = os.path.join(temp_dir, "wikipedia_cache.json")
            with open(cache_file, "r") as f:
                data = json.load(f)
                assert "key1" not in data

    def test_cached_decorator(self):
        """Test the cached decorator."""
        # Real function to cache
        def test_func(arg, kwarg1=None):
            return f"result-{arg}-{kwarg1}"
        
        # Create cache
        cache = CachingService(cache_type="ttl", maxsize=10, ttl=10)
        
        # Create decorated function
        decorated = cached(cache, key_prefix="test")(test_func)
        
        # First call should call the function and cache result
        result1 = decorated("arg1", kwarg1="kwval1")
        assert result1 == "result-arg1-kwval1"
        
        # Verify it's in the cache
        cache_key = "test:test_func:arg1:kwarg1=kwval1"
        assert cache.get(cache_key) == "result-arg1-kwval1"
        
        # Second call with same args should use cache
        result2 = decorated("arg1", kwarg1="kwval1")
        assert result2 == "result-arg1-kwval1"
        
        # Call with different args should return new result
        result3 = decorated("arg2", kwarg1="kwval1")
        assert result3 == "result-arg2-kwval1"
    
    def test_cached_decorator_custom_key(self):
        """Test the cached decorator with custom key function."""
        # Real function to cache
        def test_func(arg, kwarg1=None):
            return f"result-{arg}-{kwarg1}"
        
        # Create cache
        cache = CachingService(cache_type="ttl", maxsize=10, ttl=10)
        
        # Custom key function
        def key_func(*args, **kwargs):
            return f"custom:{args[0]}"
        
        # Create decorated function
        decorated = cached(cache, key_func=key_func)(test_func)
        
        # First call should call the function
        result1 = decorated("arg1", kwarg1="kwval1")
        assert result1 == "result-arg1-kwval1"
        
        # Call with different kwargs but same custom key should use cache
        result2 = decorated("arg1", kwarg1="different")
        assert result2 == "result-arg1-kwval1"  # Should get cached result, not new result
    
    def test_cached_decorator_custom_ttl(self):
        """Test the cached decorator with custom TTL."""
        # Real function to cache
        def test_func(arg):
            return f"result-{arg}"
        
        # Create cache
        cache = CachingService(cache_type="ttl", maxsize=10, ttl=10)
        
        # Create decorated function with short TTL
        decorated = cached(cache, ttl=1)(test_func)
        
        # First call should call the function
        result1 = decorated("arg1")
        assert result1 == "result-arg1"
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Call again should call function again (cache expired)
        result2 = decorated("arg1")
        assert result2 == "result-arg1" 