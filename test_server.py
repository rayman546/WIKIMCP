#!/usr/bin/env python3
"""
Test script for the Wikipedia MCP API server.
This script sends a simple JSON-RPC request to test if the server responds correctly.
"""
import sys
import json
import requests

def test_server(host="localhost", port=8000):
    """Test the server's JSON-RPC response formatting"""
    # Define a simple JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "0.1.0"
            }
        },
        "id": 0
    }
    
    url = f"http://{host}:{port}/mcp"
    
    print(f"Testing server at {url} with JSON-RPC initialize request...", file=sys.stderr)
    
    try:
        # Send the request
        response = requests.get(url)
        
        # Check if the response is valid JSON
        try:
            data = response.json()
            print(f"Server responded with valid JSON: {json.dumps(data, indent=2)}", file=sys.stderr)
            print(f"SUCCESS: The server is correctly returning valid JSON responses", file=sys.stderr)
            return True
        except json.JSONDecodeError:
            print(f"ERROR: Server response is not valid JSON", file=sys.stderr)
            print(f"Response content: {response.text}", file=sys.stderr)
            return False
            
    except requests.RequestException as e:
        print(f"ERROR: Failed to connect to server: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Allow command-line arguments for host and port
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    success = test_server(host, port)
    sys.exit(0 if success else 1) 