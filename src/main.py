import os
import sys
import logging

# Define debug log function for console output
def debug_log(message):
    """Log to stderr so it doesn't interfere with JSON-RPC communication"""
    print(message, file=sys.stderr)

# Setup logging
logger = logging.getLogger(__name__)

# Configure logging to use stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr  # Ensure logs go to stderr
)

# Load environment variables
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    # Import routes - Move these into try block to catch import errors
    try:
        from .api_routes import router as wiki_router, SummaryLevel
    except ImportError as e:
        debug_log(f"Error importing routes: {e}")
        debug_log("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)

    # Create FastAPI app
    app = FastAPI(
        title="Wikipedia MCP API",
        description="A Model Context Protocol (MCP) API for interacting with Wikipedia content",
        version="0.2.0",  # Updated version for refactored API
        docs_url="/",  # Swagger UI at root path
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development; restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(wiki_router, prefix="/api")

    @app.get("/ping", tags=["Health"])
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "ok", "message": "Wikipedia MCP API is running"}

    # Define Model Context Protocol (MCP) endpoint
    @app.get("/mcp", tags=["MCP"])
    async def mcp_definitions():
        """
        Return the Model Context Protocol (MCP) definitions for LLM tool use.
        This endpoint provides the schema that enables LLMs to use this API as a tool.
        """
        return {
            "schema_version": "v1",
            "tools": [
                {
                    "name": "wikipedia_search",
                    "description": "Search for Wikipedia articles matching a term",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "term": {
                                "type": "string",
                                "description": "The search term to look for on Wikipedia"
                            },
                            "results": {
                                "type": "integer",
                                "description": "Number of results to return (1-50)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["term"]
                    },
                    "endpoint": "/api/search"
                },
                {
                    "name": "wikipedia_article",
                    "description": "Get a complete Wikipedia article by title with all parsed components",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the Wikipedia article to retrieve"
                            },
                            "auto_suggest": {
                                "type": "boolean",
                                "description": "Whether to auto-suggest similar titles",
                                "default": True
                            }
                        },
                        "required": ["title"]
                    },
                    "endpoint": "/api/article"
                },
                {
                    "name": "wikipedia_summary",
                    "description": "Get a summary of a Wikipedia article at a specific detail level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the Wikipedia article to summarize"
                            },
                            "level": {
                                "type": "string",
                                "description": "Summary detail level (short, medium, long)",
                                "enum": [e.value for e in SummaryLevel],
                                "default": SummaryLevel.MEDIUM.value
                            }
                        },
                        "required": ["title"]
                    },
                    "endpoint": "/api/summary"
                },
                {
                    "name": "wikipedia_citations",
                    "description": "Get citations and references from a Wikipedia article",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the Wikipedia article to get citations from"
                            }
                        },
                        "required": ["title"]
                    },
                    "endpoint": "/api/citations"
                },
                {
                    "name": "wikipedia_structured",
                    "description": "Get structured data (tables, infobox) from a Wikipedia article",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the Wikipedia article to get structured data from"
                            }
                        },
                        "required": ["title"]
                    },
                    "endpoint": "/api/structured"
                },
                {
                    "name": "wikipedia_sections",
                    "description": "Get the section structure and content from a Wikipedia article",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the Wikipedia article to get sections from"
                            }
                        },
                        "required": ["title"]
                    },
                    "endpoint": "/api/sections"
                }
            ]
        }

except ImportError as e:
    debug_log(f"Error importing dependencies: {e}")
    debug_log("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    debug_log(f"Unexpected error: {e}")
    sys.exit(1)

if __name__ == "__main__":
    debug_log(f"Starting Wikipedia MCP API on {HOST}:{PORT}")
    uvicorn.run("src.main:app", host=HOST, port=PORT, reload=RELOAD) 