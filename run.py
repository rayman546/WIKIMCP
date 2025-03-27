#!/usr/bin/env python3
"""
Command-line interface for running the Wikipedia MCP API server.
"""
import os
import logging
import argparse
from src.config import settings

# Setup logging
logger = logging.getLogger(__name__)

def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except socket.error:
            return True

def main():
    """Main entry point for running the server."""
    parser = argparse.ArgumentParser(description="Start the Wikipedia MCP API server")
    parser.add_argument("--host", default=settings.HOST, help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind the server to")
    parser.add_argument("--cache-type", choices=["ttl", "lru", "persist", "disk"], default=settings.CACHE_TYPE,
                      help="Type of cache to use")
    parser.add_argument("--cache-ttl", type=int, default=settings.CACHE_TTL,
                      help="Time-to-live for cache entries in seconds")
    parser.add_argument("--cache-maxsize", type=int, default=settings.CACHE_MAXSIZE,
                      help="Maximum number of items in the cache")
    parser.add_argument("--cache-dir", default=settings.CACHE_DIR,
                      help="Directory for persistent cache")
    parser.add_argument("--rate-limit", type=float, default=settings.RATE_LIMIT,
                      help="Delay between Wikipedia API requests in seconds")
    parser.add_argument("--no-reload", action="store_true",
                      help="Disable auto-reload in development")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      default=settings.LOG_LEVEL,
                      help="Set the logging level")
    
    args = parser.parse_args()
    
    # Check if port is already in use
    if is_port_in_use(args.host, args.port):
        logger.info(f"Wikipedia MCP API is already running on {args.host}:{args.port}")
        logger.info("Using existing server instance.")
        return
    
    # Update settings from command line arguments
    os.environ["HOST"] = args.host
    os.environ["PORT"] = str(args.port)
    os.environ["CACHE_TYPE"] = args.cache_type
    os.environ["CACHE_TTL"] = str(args.cache_ttl)
    os.environ["CACHE_MAXSIZE"] = str(args.cache_maxsize)
    os.environ["RATE_LIMIT"] = str(args.rate_limit)
    os.environ["RELOAD"] = str(not args.no_reload).lower()
    os.environ["LOG_LEVEL"] = args.log_level
    
    if args.cache_dir:
        os.environ["CACHE_DIR"] = args.cache_dir
    
    # Import and run the server
    try:
        import uvicorn
        from src.main import app
        
        logger.info(f"Starting Wikipedia MCP API on {args.host}:{args.port}")
        logger.info(f"Cache: {args.cache_type} (TTL: {args.cache_ttl}s, Max Size: {args.cache_maxsize})")
        logger.info(f"Rate Limit: {args.rate_limit}s between requests")
        logger.info(f"Log Level: {args.log_level}")
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=not args.no_reload
        )
    except ImportError as e:
        logger.error(f"Error importing dependencies: {e}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        raise
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    main() 