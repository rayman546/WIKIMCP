import pytest
from bs4 import BeautifulSoup
import logging
from unittest.mock import patch

from src.parser import WikipediaParser

# Test HTML content
TEST_HTML = """
<html>
<body>
<h1>Main Title</h1>
<p>Introduction paragraph.</p>
<h2>Section 1</h2>
<p>Content for section 1.</p>
<ul>
    <li>Item 1</li>
    <li>Item 2</li>
</ul>
<h2>Section 2</h2>
<p>Content for section 2.</p>
<table>
    <caption>Test Table</caption>
    <tr>
        <th>Header 1</th>
        <th>Header 2</th>
    </tr>
    <tr>
        <td>Cell 1</td>
        <td>Cell 2</td>
    </tr>
</table>
<h3>Subsection</h3>
<p>Content for subsection.</p>
<ol class="references">
    <li id="cite_1">Reference 1 <a href="http://example.com">Link</a></li>
    <li id="cite_2">Reference 2 <a href="http://example.org">Link</a></li>
</ol>
<img src="//example.com/image.jpg" alt="Example Image">
<table class="infobox">
    <tr>
        <th class="infobox-label">Property 1</th>
        <td class="infobox-data">Value 1</td>
    </tr>
    <tr>
        <th class="infobox-label">Property 2</th>
        <td class="infobox-data">Value 2</td>
    </tr>
</table>
</body>
</html>
"""

# Sample article data for testing
TEST_ARTICLE_DATA = {
    "title": "Test Article",
    "summary": "This is a test summary.",
    "content": "This is the article content.",
    "url": "https://example.com/wiki/Test_Article",
    "html": TEST_HTML,
    "images": ["https://example.com/image.jpg"],
    "links": ["Link 1", "Link 2"],
    "categories": ["Category 1", "Category 2"]
}

# Sample disambiguation data for testing
TEST_DISAMBIGUATION = {
    "error": "disambiguation",
    "message": "Test Article may refer to multiple articles.",
    "options": ["Test Article (Science)", "Test Article (Technology)", "Test Article (History)"]
}

class TestWikipediaParser:
    """Tests for the WikipediaParser class."""
    
    def test_extract_clean_text(self):
        """Test extracting clean text from HTML."""
        clean_text = WikipediaParser.extract_clean_text(TEST_HTML)
        
        assert "Main Title" in clean_text
        assert "Introduction paragraph." in clean_text
        assert "Content for section 1." in clean_text
        assert "Item 1" in clean_text
        assert "<p>" not in clean_text  # No HTML tags
        
        # Test empty input
        assert WikipediaParser.extract_clean_text("") == ""
        assert WikipediaParser.extract_clean_text(None) == ""
    
    def test_extract_sections(self):
        """Test extracting sections from HTML."""
        sections = WikipediaParser.extract_sections(TEST_HTML)
        
        assert len(sections) > 0
        
        # Check main title
        assert sections[0]["title"] == "Main Title"
        assert sections[0]["level"] == 1
        
        # Check section 1
        section1 = next((s for s in sections if s["title"] == "Section 1"), None)
        assert section1 is not None
        assert section1["level"] == 2
        assert "Content for section 1" in section1["text_content"]
        
        # Check subsection
        subsection = next((s for s in sections if s["title"] == "Subsection"), None)
        assert subsection is not None
        assert subsection["level"] == 3
        
        # Test empty input
        assert WikipediaParser.extract_sections("") == []
        assert WikipediaParser.extract_sections(None) == []
    
    def test_extract_citations(self):
        """Test extracting citations from HTML."""
        citations = WikipediaParser.extract_citations(TEST_HTML)
        
        assert len(citations) == 2
        
        assert citations[0]["id"] == "cite_1"
        assert "Reference 1" in citations[0]["text"]
        assert "http://example.com" in citations[0]["urls"]
        
        assert citations[1]["id"] == "cite_2"
        assert "Reference 2" in citations[1]["text"]
        assert "http://example.org" in citations[1]["urls"]
        
        # Test empty input
        assert WikipediaParser.extract_citations("") == []
        assert WikipediaParser.extract_citations(None) == []
    
    def test_extract_tables(self):
        """Test extracting tables from HTML."""
        tables = WikipediaParser.extract_tables(TEST_HTML)
        
        # There are two tables in the test HTML (regular table and infobox)
        assert len(tables) == 2
        
        # Regular table
        regular_table = next((t for t in tables if t["caption"] == "Test Table"), None)
        assert regular_table is not None
        assert regular_table["headers"] == ["Header 1", "Header 2"]
        assert regular_table["rows"] == [["Cell 1", "Cell 2"]]
        
        # The second table could be the infobox, depending on implementation
        assert len(tables) == 2
        
        # Test empty input
        assert WikipediaParser.extract_tables("") == []
        assert WikipediaParser.extract_tables(None) == []
    
    def test_extract_images(self):
        """Test extracting images from HTML."""
        images = WikipediaParser.extract_images(TEST_HTML)
        
        assert len(images) == 1
        
        assert images[0]["src"] == "https://example.com/image.jpg"
        assert images[0]["alt"] == "Example Image"
        
        # Test empty input
        assert WikipediaParser.extract_images("") == []
        assert WikipediaParser.extract_images(None) == []
    
    def test_extract_infobox(self):
        """Test extracting infobox from HTML."""
        infobox = WikipediaParser.extract_infobox(TEST_HTML)
        
        assert infobox is not None
        assert infobox["Property 1"] == "Value 1"
        assert infobox["Property 2"] == "Value 2"
        
        # Test empty input
        assert WikipediaParser.extract_infobox("") is None
        assert WikipediaParser.extract_infobox(None) is None
    
    def test_parse_article(self):
        """Test parsing a complete article."""
        parsed_article = WikipediaParser.parse_article(TEST_ARTICLE_DATA)
        
        assert parsed_article["type"] == "article"
        assert parsed_article["title"] == "Test Article"
        assert parsed_article["summary"] == "This is a test summary."
        assert parsed_article["url"] == "https://example.com/wiki/Test_Article"
        
        # Verify all components were extracted
        assert len(parsed_article["sections"]) > 0
        assert len(parsed_article["citations"]) == 2
        assert len(parsed_article["tables"]) == 2
        assert len(parsed_article["images"]) == 1
        assert parsed_article["infobox"] is not None
        assert parsed_article["categories"] == ["Category 1", "Category 2"]
        assert parsed_article["links"] == ["Link 1", "Link 2"]
    
    def test_parse_article_disambiguation(self):
        """Test parsing a disambiguation page."""
        parsed_article = WikipediaParser.parse_article(TEST_DISAMBIGUATION)
        
        assert parsed_article["type"] == "disambiguation"
        assert parsed_article["title"] == "Unknown"  # Default value when title is not provided
        assert parsed_article["options"] == TEST_DISAMBIGUATION["options"]
        assert parsed_article["message"] == TEST_DISAMBIGUATION["message"]
    
    @patch("src.parser.WikipediaParser.extract_sections")
    def test_parse_article_error_handling(self, mock_extract_sections):
        """Test error handling in parse_article."""
        # Mock extract_sections to raise an exception
        mock_extract_sections.side_effect = Exception("Parsing error")
        
        # Parse article should handle the exception and return a partial result
        parsed_article = WikipediaParser.parse_article(TEST_ARTICLE_DATA)
        
        assert parsed_article["type"] == "article"
        assert parsed_article["title"] == "Test Article"
        assert parsed_article["summary"] == "This is a test summary."
        assert parsed_article["url"] == "https://example.com/wiki/Test_Article"
        assert "parse_error" in parsed_article
        assert "Parsing error" in parsed_article["parse_error"]
    
    def test_format_for_llm(self):
        """Test formatting article data for LLM consumption."""
        # Test with raw article data
        formatted_data = WikipediaParser.format_for_llm(TEST_ARTICLE_DATA)
        
        assert formatted_data["type"] == "article"
        assert formatted_data["title"] == "Test Article"
        assert formatted_data["summary"] == "This is a test summary."
        assert formatted_data["url"] == "https://example.com/wiki/Test_Article"
        assert len(formatted_data["sections"]) > 0
        
        # Test with already parsed article data
        parsed_article = WikipediaParser.parse_article(TEST_ARTICLE_DATA)
        formatted_data2 = WikipediaParser.format_for_llm(parsed_article)
        
        # Should return the parsed article as is
        assert formatted_data2 == parsed_article
        
        # Test with disambiguation page
        formatted_disambiguation = WikipediaParser.format_for_llm(TEST_DISAMBIGUATION)
        assert formatted_disambiguation["type"] == "disambiguation"
    
    def test_generate_summary_short(self):
        """Test generating a short summary."""
        # Test with raw article data
        article_data = {
            "summary": "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence.",
            "content": "Full content for testing."
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="short")
        
        # Should include only first few sentences
        assert "First sentence. Second sentence." in summary
        assert "Third sentence" not in summary
        
        # Test with parsed article data
        parsed_article = {
            "type": "article",
            "title": "Test",
            "summary": "First sentence. Second sentence. Third sentence.",
            "sections": []
        }
        
        summary = WikipediaParser.generate_summary(parsed_article, level="short")
        assert "First sentence. Second sentence." in summary
    
    def test_generate_summary_medium(self):
        """Test generating a medium summary."""
        # Test with raw article data
        article_data = {
            "summary": "Complete medium summary.",
            "content": "Full content for testing."
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="medium")
        
        # Should use the full base summary
        assert summary == "Complete medium summary."
        
        # Test with parsed article data
        parsed_article = {
            "type": "article",
            "title": "Test",
            "summary": "Complete medium summary.",
            "sections": []
        }
        
        summary = WikipediaParser.generate_summary(parsed_article, level="medium")
        assert summary == "Complete medium summary."
    
    def test_generate_summary_long(self):
        """Test generating a long summary."""
        # Create parsed article with sections
        parsed_article = {
            "type": "article",
            "title": "Test",
            "summary": "Base summary.",
            "sections": [
                {"level": 1, "title": "Introduction", "text_content": "This is the introduction."},
                {"level": 2, "title": "History", "text_content": "This is the history section."},
                {"level": 3, "title": "Details", "text_content": "These are some details."}
            ]
        }
        
        summary = WikipediaParser.generate_summary(parsed_article, level="long")
        
        # Should include base summary plus section highlights
        assert "Base summary." in summary
        assert "Introduction: This is the introduction." in summary
        assert "History: This is the history section." in summary
        # Level 3 sections might be skipped depending on implementation
    
    def test_generate_summary_disambiguation(self):
        """Test generating a summary for a disambiguation page."""
        disambiguation = {
            "error": "disambiguation",
            "options": ["Option 1", "Option 2", "Option 3"],
            "message": "May refer to multiple articles."
        }
        
        summary = WikipediaParser.generate_summary(disambiguation, level="short")
        
        # Should return a message about disambiguation
        assert "Disambiguation" in summary
        assert "Option 1" in summary
        assert "Option 2" in summary
        assert "Option 3" in summary
    
    def test_generate_summary_fallback(self):
        """Test fallback behavior when no summary is available."""
        # Article with no summary
        article_data = {
            "title": "No Summary",
            "content": "",
            "html": "<html><body><p>Some content</p></body></html>"
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="medium")
        
        # Should fall back to a default message
        assert summary == "No summary available." 