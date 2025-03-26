# Wikipedia MCP API

A local Python server implementing the Model Context Protocol (MCP) to enable Language Learning Models (LLMs) like Claude Desktop and Cursor IDE to access and process English Wikipedia content efficiently.

## Overview

This project provides a RESTful API that serves as a bridge between LLMs and Wikipedia content. It allows LLMs to:

- Search for Wikipedia articles
- Retrieve full article content
- Get article summaries at different detail levels
- Extract citations
- Access structured data (tables, infoboxes)

The API implements caching to optimize performance and reduce load on the Wikipedia API.

## Architecture

The Wikipedia MCP API is built with the following components:

- **FastAPI**: A modern, high-performance web framework for building APIs
- **Wikipedia Python Library**: For interacting with the Wikipedia API
- **BeautifulSoup4**: For HTML parsing and content extraction
- **Caching System**: Multiple caching strategies (TTL, LRU, persistent)

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/wikipedia-mcp-api.git
   cd wikipedia-mcp-api
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```
     .\venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Starting the Server

```
python -m src.main
```

This will start the server at `http://localhost:8000` with auto-reload enabled for development.

### API Documentation

Once the server is running, you can access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/`
- ReDoc: `http://localhost:8000/redoc`

### MCP Schema

To get the Model Context Protocol schema for tool use by LLMs:

```
GET http://localhost:8000/mcp
```

## API Endpoints

### Health Check

```
GET /ping
```

Returns a simple response to verify the server is running.

### Search

```
GET /api/search?term={search_term}&results={num_results}
```

Searches for Wikipedia articles matching the term.

### Get Article

```
GET /api/article?title={article_title}&auto_suggest={true|false}
```

Gets the full content of a Wikipedia article, formatted for LLM consumption.

### Get Summary

```
GET /api/summary?title={article_title}&level={short|medium|long}
```

Gets a summary of a Wikipedia article with adjustable detail level.

### Get Citations

```
GET /api/citations?title={article_title}
```

Extracts citations from a Wikipedia article.

### Get Structured Data

```
GET /api/structured?title={article_title}
```

Extracts tables and infobox data from a Wikipedia article.

## Configuration

The server can be configured through environment variables:

- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
- `CACHE_TYPE`: Caching strategy (ttl, lru, persist) (default: ttl)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 3600)
- `CACHE_MAXSIZE`: Maximum cache size (default: 1000)
- `CACHE_DIR`: Directory for persistent cache (default: src/.cache)
- `RATE_LIMIT`: Delay between Wikipedia API requests in seconds (default: 1.0)

## Setting up for Claude Desktop

To use this API with Claude Desktop:

1. Ensure the API is running locally
2. In Claude Desktop, define a tool with the following specifications:

```json
{
  "name": "wikipedia_search",
  "description": "Search for Wikipedia articles matching a term",
  "input_schema": {
    "type": "object",
    "properties": {
      "term": {
        "type": "string",
        "description": "The search term to look for on Wikipedia"
      },
      "results": {
        "type": "integer",
        "description": "Number of results to return (1-50)",
        "default": 10
      }
    },
    "required": ["term"]
  },
  "url": "http://localhost:8000/api/search"
}
```

Similar tool definitions can be created for the other endpoints.

## Setting up for Cursor IDE

To use this API with Cursor IDE:

1. Ensure the API is running locally
2. Configure the tool in Cursor's settings following their documentation for external API tools
3. Point the tool to the `/mcp` endpoint to get the complete tool definition

## Performance

The API is designed to meet the following performance constraints:

- Memory usage: <500MB
- Cached response time: <2s
- Efficient caching to reduce Wikipedia API calls

## Testing

To run tests:

```
pytest
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 