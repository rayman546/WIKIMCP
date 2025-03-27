#!/usr/bin/env python3
"""
Test script for the Wikipedia MCP server.
"""
import sys
import json
import requests
import subprocess
import time
import argparse
from typing import Dict, Any

def debug_log(message):
    """Log to stderr."""
    print(message, file=sys.stderr)

def start_mcp_server(host="localhost", port=8000):
    """Start the MCP server as a subprocess for testing."""
    debug_log(f"Starting MCP server on {host}:{port}...")
    
    try:
        # Start the server process
        process = subprocess.Popen(
            ["python", "mcp_server.py", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a moment to start up
        time.sleep(2)
        
        # Check if it's running
        try:
            response = requests.get(f"http://{host}:{port}/health")
            if response.status_code == 200:
                debug_log("MCP server started successfully")
                return process
        except requests.RequestException:
            debug_log("Waiting for server to start...")
            time.sleep(3)
        
        return process
    except Exception as e:
        debug_log(f"Failed to start server: {e}")
        return None

def stop_mcp_server(process):
    """Stop the MCP server subprocess."""
    if process:
        debug_log("Stopping MCP server...")
        process.terminate()
        process.wait(timeout=5)
        debug_log("MCP server stopped")

def test_search(host="localhost", port=8000):
    """Test the wikipedia_search tool."""
    debug_log("\nTesting wikipedia_search...")
    
    # Create the JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "wikipedia_search",
        "params": {
            "term": "Python programming",
            "results": 3
        }
    }
    
    try:
        # Send the request
        response = requests.post(
            f"http://{host}:{port}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        
        # Parse the response
        data = response.json()
        debug_log(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify the response
        if "result" in data and "results" in data["result"]:
            debug_log("✓ wikipedia_search test passed")
            return True
        else:
            debug_log("✗ wikipedia_search test failed")
            return False
    except Exception as e:
        debug_log(f"✗ wikipedia_search test failed: {e}")
        return False

def test_article(host="localhost", port=8000):
    """Test the wikipedia_article tool."""
    debug_log("\nTesting wikipedia_article...")
    
    # Create the JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "wikipedia_article",
        "params": {
            "title": "Python (programming language)"
        }
    }
    
    try:
        # Send the request
        response = requests.post(
            f"http://{host}:{port}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        
        # Parse the response
        data = response.json()
        debug_log(f"Response status: {response.status_code}, ID: {data.get('id')}")
        
        # Verify the response
        if "result" in data and "title" in data["result"]:
            debug_log("✓ wikipedia_article test passed")
            return True
        else:
            debug_log("✗ wikipedia_article test failed")
            return False
    except Exception as e:
        debug_log(f"✗ wikipedia_article test failed: {e}")
        return False

def test_summary(host="localhost", port=8000):
    """Test the wikipedia_summary tool."""
    debug_log("\nTesting wikipedia_summary...")
    
    # Create the JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "wikipedia_summary",
        "params": {
            "title": "Python (programming language)",
            "level": "short"
        }
    }
    
    try:
        # Send the request
        response = requests.post(
            f"http://{host}:{port}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        
        # Parse the response
        data = response.json()
        debug_log(f"Response status: {response.status_code}, ID: {data.get('id')}")
        
        # Verify the response
        if "result" in data and "summary" in data["result"]:
            debug_log("✓ wikipedia_summary test passed")
            return True
        else:
            debug_log("✗ wikipedia_summary test failed")
            return False
    except Exception as e:
        debug_log(f"✗ wikipedia_summary test failed: {e}")
        return False

def run_tests(host="localhost", port=8000, start_server=True):
    """Run all tests."""
    server_process = None
    
    try:
        # Start the server if requested
        if start_server:
            server_process = start_mcp_server(host, port)
        
        # Run the tests
        search_result = test_search(host, port)
        article_result = test_article(host, port)
        summary_result = test_summary(host, port)
        
        # Summarize results
        debug_log("\nTest Results:")
        debug_log(f"wikipedia_search: {'Passed' if search_result else 'Failed'}")
        debug_log(f"wikipedia_article: {'Passed' if article_result else 'Failed'}")
        debug_log(f"wikipedia_summary: {'Passed' if summary_result else 'Failed'}")
        
        success = search_result and article_result and summary_result
        debug_log(f"\nOverall: {'All tests passed!' if success else 'Some tests failed!'}")
        
        return success
    finally:
        # Stop the server if we started it
        if start_server and server_process:
            stop_mcp_server(server_process)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Wikipedia MCP server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--no-start", action="store_true", help="Don't start the server (use existing one)")
    
    args = parser.parse_args()
    
    success = run_tests(
        host=args.host,
        port=args.port,
        start_server=not args.no_start
    )
    
    sys.exit(0 if success else 1) 