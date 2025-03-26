import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock

from src.main import app
from src.parser import WikipediaParser
from src.api_routes import get_wikipedia_client, get_cache_service, SummaryLevel, get_parsed_article, ArticleNotFoundError

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
}

# Mock for the parsed article
MOCK_PARSED_ARTICLE = {
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
    
    # Check that all expected tools are defined
    tools = response.json()["tools"]
    tool_names = [tool["name"] for tool in tools]
    expected_tools = [
        "wikipedia_search", 
        "wikipedia_article", 
        "wikipedia_summary",
        "wikipedia_citations",
        "wikipedia_structured", 
        "wikipedia_sections"
    ]
    for tool in expected_tools:
        assert tool in tool_names

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

@patch("src.api_routes.get_parsed_article")
def test_article_endpoint(mock_get_parsed_article):
    """Test the article endpoint."""
    # Setup get_parsed_article mock
    mock_get_parsed_article.return_value = MOCK_PARSED_ARTICLE
    
    # Test the endpoint
    response = client.get("/api/article?title=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_PARSED_ARTICLE["title"]
    assert data["type"] == "article"
    assert "sections" in data
    assert "citations" in data
    assert "tables" in data
    assert "infobox" in data

@patch("src.api_routes.get_parsed_article")
@patch("src.api_routes.WikipediaParser.generate_summary")
def test_summary_endpoint(mock_generate_summary, mock_get_parsed_article):
    """Test the summary endpoint."""
    # Setup mocks
    mock_get_parsed_article.return_value = MOCK_PARSED_ARTICLE
    mock_generate_summary.return_value = "Generated summary text"
    
    # Test the endpoint
    response = client.get("/api/summary?title=Python&level=short")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_PARSED_ARTICLE["title"]
    assert data["summary"] == "Generated summary text"
    assert data["level"] == "short"
    assert data["type"] == "summary"

@patch("src.api_routes.get_parsed_article")
def test_citations_endpoint(mock_get_parsed_article):
    """Test the citations endpoint."""
    # Setup mock with citations
    article_with_citations = MOCK_PARSED_ARTICLE.copy()
    article_with_citations["citations"] = [
        {"id": "citation-1", "text": "Citation 1", "urls": ["https://example.com/1"]},
        {"id": "citation-2", "text": "Citation 2", "urls": ["https://example.com/2"]}
    ]
    mock_get_parsed_article.return_value = article_with_citations
    
    # Test the endpoint
    response = client.get("/api/citations?title=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_PARSED_ARTICLE["title"]
    assert data["type"] == "citations"
    assert data["count"] == 2
    assert len(data["citations"]) == 2
    assert data["citations"][0]["id"] == "citation-1"

@patch("src.api_routes.get_parsed_article")
def test_structured_endpoint(mock_get_parsed_article):
    """Test the structured endpoint."""
    # Setup mock with structured data
    article_with_structured = MOCK_PARSED_ARTICLE.copy()
    article_with_structured["tables"] = [
        {"caption": "Table 1", "headers": ["Col1", "Col2"], "rows": [["A", "B"], ["C", "D"]]}
    ]
    article_with_structured["infobox"] = {"Created by": "Guido van Rossum"}
    mock_get_parsed_article.return_value = article_with_structured
    
    # Test the endpoint
    response = client.get("/api/structured?title=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_PARSED_ARTICLE["title"]
    assert data["type"] == "structured"
    assert len(data["tables"]) == 1
    assert data["tables"][0]["caption"] == "Table 1"
    assert data["infobox"]["Created by"] == "Guido van Rossum"

@patch("src.api_routes.get_parsed_article")
def test_sections_endpoint(mock_get_parsed_article):
    """Test the new sections endpoint."""
    # Setup mock with sections
    article_with_sections = MOCK_PARSED_ARTICLE.copy()
    article_with_sections["sections"] = [
        {"level": 1, "title": "Introduction", "text_content": "Intro text", "html_content": "<p>Intro text</p>"},
        {"level": 2, "title": "History", "text_content": "History text", "html_content": "<p>History text</p>"}
    ]
    mock_get_parsed_article.return_value = article_with_sections
    
    # Test the endpoint
    response = client.get("/api/sections?title=Python")
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == MOCK_PARSED_ARTICLE["title"]
    assert data["type"] == "sections"
    assert data["count"] == 2
    assert data["sections"][0]["title"] == "Introduction"
    assert data["sections"][1]["title"] == "History"

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
def test_invalid_level_parameter(mock_cache_service, mock_wiki_client):
    """Test invalid level parameter in summary endpoint."""
    # Setup minimal mocks
    mock_wiki_client.return_value = Mock()
    mock_cache_service.return_value = Mock()
    
    # Test the endpoint with invalid level - route should catch validation error
    with patch("src.api_routes.cached", side_effect=lambda *args, **kwargs: lambda f: f):
        response = client.get("/api/summary?title=Python&level=invalid")
        
        assert response.status_code == 422  # FastAPI validation error status code
        assert "Input should be" in response.json()["detail"][0]["msg"]

@patch("src.api_routes.WikipediaClient")
@patch("src.api_routes.CachingService")
@patch("src.api_routes.cached")
def test_article_not_found(mock_cached, mock_cache_service, mock_wiki_client):
    """Test handling of article not found errors."""
    # Setup WikipediaClient mock to raise ArticleNotFoundError
    mock_wiki_instance = Mock()
    mock_wiki_instance.get_article.side_effect = ArticleNotFoundError("Page not found: NonexistentArticle")
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
    
    # Test the endpoint
    response = client.get("/api/article?title=NonexistentArticle")
    
    # Should return 404 with appropriate message
    assert response.status_code == 404
    assert "Article not found" in response.json()["detail"]

@patch("src.api_routes.get_parsed_article")
def test_disambiguation_page(mock_get_parsed_article):
    """Test handling of disambiguation pages."""
    # Setup mock with disambiguation page
    disambiguation_response = {
        "type": "disambiguation",
        "title": "Python",
        "options": ["Python (programming language)", "Monty Python", "Python (snake)"],
        "message": "Python may refer to multiple articles"
    }
    mock_get_parsed_article.return_value = disambiguation_response
    
    # Test the article endpoint
    response = client.get("/api/article?title=Python")
    
    # Should return 200 with disambiguation info
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "disambiguation"
    assert len(data["options"]) == 3
    
    # Test the summary endpoint with the same disambiguation
    response = client.get("/api/summary?title=Python&level=short")
    
    # Should also handle disambiguation
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "disambiguation" 