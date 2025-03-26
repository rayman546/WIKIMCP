import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock

from src.main import app
from src.parser import WikipediaParser
from src.api_routes import get_wikipedia_client, get_cache_service, SummaryLevel

client = TestClient(app)

# Mock data
MOCK_SEARCH_RESULTS = ["Python (programming language)", "Python", "Monty Python"]
MOCK_ARTICLE_DATA = {
    "title": "Python (programming language)",
    "content": "Python is a high-level, general-purpose programming language.",
    "summary": "Python is a programming language.",
    "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "html": "<html><body><p>Python is a programming language.</p></body></html>",
    "images": ["https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png"],
    "links": ["Programming language", "High-level programming language"],
    "categories": ["Programming languages"],
    "references": ["https://www.python.org/"],
    "sections": []
}

# Mock for the parser
MOCK_FORMATTED_DATA = {
    "type": "article",
    "title": "Python (programming language)",
    "summary": "Python is a programming language.",
    "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "sections": [],
    "citations": [],
    "tables": [],
    "images": [],
    "infobox": {},
    "categories": ["Programming languages"],
    "links": ["Programming language", "High-level programming language"]
}

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_mcp_definitions():
    """Test the MCP definitions endpoint."""
    response = client.get("/mcp")
    assert response.status_code == 200
    assert "tools" in response.json()
    assert "schema_version" in response.json()

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
@patch("src.api_routes.cached")
def test_search_endpoint(mock_cached, mock_cache_service, mock_wiki_client):
    """Test the search endpoint using more specific mocks."""
    # Setup WikipediaClient mock
    mock_wiki_instance = Mock()
    mock_wiki_instance.search.return_value = MOCK_SEARCH_RESULTS
    mock_wiki_client.return_value = mock_wiki_instance
    
    # Setup CachingService mock
    mock_cache_instance = Mock()
    mock_cache_service.return_value = mock_cache_instance
    
    # Create a function that passes through to the mocked search method
    def cached_decorator(cache_service, **kwargs):
        def decorator(func):
            return mock_wiki_instance.search
        return decorator
    
    # Apply our mocked cached decorator
    mock_cached.side_effect = cached_decorator
    
    # Test the endpoint
    response = client.get("/api/search?term=python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "python"
    assert data["results"] == MOCK_SEARCH_RESULTS
    assert data["count"] == len(MOCK_SEARCH_RESULTS)

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
@patch("src.api_routes.cached")
@patch("src.api_routes.WikipediaParser.format_for_llm")
def test_article_endpoint(mock_format, mock_cached, mock_cache_service, mock_wiki_client):
    """Test the article endpoint."""
    # Setup WikipediaClient mock
    mock_wiki_instance = Mock()
    mock_wiki_instance.get_article.return_value = MOCK_ARTICLE_DATA
    mock_wiki_client.return_value = mock_wiki_instance
    
    # Setup CachingService mock
    mock_cache_instance = Mock()
    mock_cache_service.return_value = mock_cache_instance
    
    # Create a function that passes through to the mocked get_article method
    def cached_decorator(cache_service, **kwargs):
        def decorator(func):
            return mock_wiki_instance.get_article
        return decorator
    
    # Apply our mocked cached decorator
    mock_cached.side_effect = cached_decorator
    
    # Mock the parser
    mock_format.return_value = MOCK_FORMATTED_DATA
    
    # Test the endpoint
    response = client.get("/api/article?title=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_ARTICLE_DATA["title"]
    assert data["type"] == "article"

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
@patch("src.api_routes.cached")
@patch("src.api_routes.WikipediaParser.generate_summary")
def test_summary_endpoint(mock_generate, mock_cached, mock_cache_service, mock_wiki_client):
    """Test the summary endpoint."""
    # Setup WikipediaClient mock
    mock_wiki_instance = Mock()
    mock_wiki_instance.get_article.return_value = MOCK_ARTICLE_DATA
    mock_wiki_client.return_value = mock_wiki_instance
    
    # Setup CachingService mock
    mock_cache_instance = Mock()
    mock_cache_instance.get.return_value = None  # Cache miss
    mock_cache_service.return_value = mock_cache_instance
    
    # Create a function that passes through to the mocked get_article method
    def cached_decorator(cache_service, **kwargs):
        def decorator(func):
            return mock_wiki_instance.get_article
        return decorator
    
    # Apply our mocked cached decorator
    mock_cached.side_effect = cached_decorator
    
    # Mock the summary generator
    mock_generate.return_value = "Short summary"
    
    # Test the endpoint with string value for level
    response = client.get("/api/summary?title=Python&level=short")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_ARTICLE_DATA["title"]
    assert data["summary"] == "Short summary"
    assert data["level"] == "short"

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
def test_invalid_level_parameter(mock_cache_service, mock_wiki_client):
    """Test invalid level parameter in summary endpoint."""
    # Setup minimal mocks - we just need the dependencies to exist
    mock_wiki_client.return_value = Mock()
    mock_cache_service.return_value = Mock()
    
    # Test the endpoint with invalid level - route should catch validation error
    with patch("src.api_routes.cached", side_effect=lambda *args, **kwargs: lambda f: f):
        response = client.get("/api/summary?title=Python&level=invalid")
        
        assert response.status_code == 422  # FastAPI validation error status code
        assert "Input should be" in response.json()["detail"][0]["msg"] 