# Wikipedia MCP API

A Model Context Protocol (MCP) API for interacting with Wikipedia content in Claude Desktop and other MCP-compatible clients.

## Features

- Search Wikipedia articles
- Get complete article content with parsed components
- Get article summaries at different detail levels (short, medium, long)
- Extract citations and references
- Get structured data (tables, infoboxes)
- Extract article sections with hierarchical structure
- Caching for improved performance
- Proper rate limiting to respect the Wikipedia API

## Installation

### Automatic Installation (Windows)

The easiest way to install the Wikipedia MCP API is to use the PowerShell installer script:

```powershell
# Download and run the installer script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/YOUR_USERNAME/WIKIMCP/mcp-implementation/install.ps1" -OutFile "install.ps1"
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The installer will:
1. Clone the repository or update an existing one
2. Create a Python virtual environment
3. Install all dependencies
4. Configure Claude Desktop to use the Wikipedia MCP API

For more detailed installation options, see the [installation checklist](./INSTALL_CHECKLIST.md).

### Configure Claude Desktop

You can configure Claude Desktop to use the Wikipedia MCP API by running the provided configuration script:

```powershell
# Update Claude Desktop configuration
powershell -ExecutionPolicy Bypass -File .\update_config.ps1
```

This script will:
1. Locate the Claude Desktop configuration file
2. Add or update the Wikipedia MCP server configuration
3. Point to the correct Python executable and script
4. Set appropriate host and port settings

### Manual Installation

1. Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/WIKIMCP.git
cd WIKIMCP
git checkout mcp-implementation
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the server:

```bash
python run.py --host 127.0.0.1 --port 8765
```

4. Configure Claude Desktop:
   - Edit your Claude Desktop configuration file at `%APPDATA%\Claude\claude_desktop_config.json`
   - Add the Wikipedia MCP server configuration to the `mcpServers` section

## Usage in Claude Desktop

Once installed and configured, you'll have the following tools available in Claude Desktop:

- `wikipedia_search`: Search for Wikipedia articles matching a term
- `wikipedia_article`: Get a complete Wikipedia article by title
- `wikipedia_summary`: Get a summary of a Wikipedia article
- `wikipedia_citations`: Get citations from a Wikipedia article
- `wikipedia_structured`: Get structured data (tables, infobox) from a Wikipedia article
- `wikipedia_sections`: Get section structure and content from a Wikipedia article

Example usage in Claude:

```
Can you search Wikipedia for information about quantum computing?

/wikipedia_search term="quantum computing" results=5
```

## Configuration Options

The MCP server accepts the following configuration options:

- `--host`: Host to bind the server to (default: `0.0.0.0`)
- `--port`: Port to bind the server to (default: `8000`)
- `--cache-type`: Type of cache to use (`ttl`, `lru`, or `persist`) (default: `ttl`)
- `--cache-ttl`: Time-to-live for cache entries in seconds (default: `3600`)
- `--cache-maxsize`: Maximum number of items in the cache (default: `1000`)
- `--cache-dir`: Directory for persistent cache
- `--rate-limit`: Delay between Wikipedia API requests in seconds (default: `1.0`)

## Development

### Testing

Run the tests to verify the server is working correctly:

```bash
python test_mcp_server.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 