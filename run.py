#!/usr/bin/env python3
"""
Run script for starting the Wikipedia MCP API server.
"""
import os
import sys
import argparse

def debug_log(message):
    """Log to stderr so it doesn't interfere with JSON-RPC communication"""
    print(message, file=sys.stderr)

def main():
    """Main entry point for running the server."""
    parser = argparse.ArgumentParser(description="Start the Wikipedia MCP API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--cache-type", choices=["ttl", "lru", "persist"], default="ttl",
                        help="Type of cache to use")
    parser.add_argument("--cache-ttl", type=int, default=3600,
                        help="Time-to-live for cache entries in seconds")
    parser.add_argument("--cache-maxsize", type=int, default=1000,
                        help="Maximum number of items in the cache")
    parser.add_argument("--cache-dir", help="Directory for persistent cache")
    parser.add_argument("--rate-limit", type=float, default=1.0,
                        help="Delay between Wikipedia API requests in seconds")
    parser.add_argument("--no-reload", action="store_true",
                        help="Disable auto-reload in development")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["HOST"] = args.host
    os.environ["PORT"] = str(args.port)
    os.environ["CACHE_TYPE"] = args.cache_type
    os.environ["CACHE_TTL"] = str(args.cache_ttl)
    os.environ["CACHE_MAXSIZE"] = str(args.cache_maxsize)
    os.environ["RATE_LIMIT"] = str(args.rate_limit)
    os.environ["RELOAD"] = str(not args.no_reload).lower()
    
    if args.cache_dir:
        os.environ["CACHE_DIR"] = args.cache_dir
    
    # Import and run the app
    try:
        from src.main import app
        import uvicorn
        
        debug_log(f"Starting Wikipedia MCP API on {args.host}:{args.port}")
        debug_log(f"Cache: {args.cache_type} (TTL: {args.cache_ttl}s, Max Size: {args.cache_maxsize})")
        debug_log(f"Rate Limit: {args.rate_limit}s between requests")
        debug_log(f"Auto-reload: {'disabled' if args.no_reload else 'enabled'}")
        
        uvicorn.run("src.main:app", host=args.host, port=args.port, reload=not args.no_reload)
    except ImportError as e:
        debug_log(f"Error: {e}")
        debug_log("Make sure you have installed all dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        debug_log(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 