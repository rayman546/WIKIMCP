import pytest
from bs4 import BeautifulSoup

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
    
    def test_extract_images(self):
        """Test extracting images from HTML."""
        images = WikipediaParser.extract_images(TEST_HTML)
        
        assert len(images) == 1
        
        assert images[0]["src"] == "https://example.com/image.jpg"
        assert images[0]["alt"] == "Example Image"
    
    def test_extract_infobox(self):
        """Test extracting infobox from HTML."""
        infobox = WikipediaParser.extract_infobox(TEST_HTML)
        
        assert infobox is not None
        assert infobox["Property 1"] == "Value 1"
        assert infobox["Property 2"] == "Value 2"
    
    def test_format_for_llm(self):
        """Test formatting article data for LLM consumption."""
        # Create sample article data
        article_data = {
            "title": "Test Article",
            "summary": "This is a test summary.",
            "content": "This is the article content.",
            "url": "https://example.com/wiki/Test_Article",
            "html": TEST_HTML,
            "images": ["https://example.com/image.jpg"],
            "links": ["Link 1", "Link 2"],
            "categories": ["Category 1", "Category 2"],
            "references": ["Reference 1", "Reference 2"]
        }
        
        formatted_data = WikipediaParser.format_for_llm(article_data)
        
        assert formatted_data["type"] == "article"
        assert formatted_data["title"] == "Test Article"
        assert formatted_data["summary"] == "This is a test summary."
        assert formatted_data["url"] == "https://example.com/wiki/Test_Article"
        assert len(formatted_data["sections"]) > 0
        assert len(formatted_data["citations"]) == 2
        # There are two tables in the test HTML (regular table and infobox)
        assert len(formatted_data["tables"]) == 2
        assert len(formatted_data["images"]) == 1
        assert formatted_data["infobox"] is not None
        assert "categories" in formatted_data
        assert "links" in formatted_data
    
    def test_generate_summary_short(self):
        """Test generating a short summary."""
        article_data = {
            "summary": "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence.",
            "content": "Full content for testing."
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="short")
        
        # Should include up to 3 sentences
        assert "First sentence. Second sentence. Third sentence" in summary
        assert "Fourth sentence" not in summary
    
    def test_generate_summary_medium(self):
        """Test generating a medium summary."""
        article_data = {
            "summary": "First paragraph.\nSecond paragraph.\nThird paragraph.",
            "content": "Full content for testing."
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="medium")
        
        # Should include up to 2 paragraphs
        assert "First paragraph" in summary
        assert "Second paragraph" in summary
        assert "Third paragraph" not in summary
    
    def test_generate_summary_long(self):
        """Test generating a long summary."""
        article_data = {
            "summary": "Complete summary for testing.",
            "content": "Full content for testing."
        }
        
        summary = WikipediaParser.generate_summary(article_data, level="long")
        
        # Should include the full summary
        assert summary == "Complete summary for testing."
    
    def test_generate_summary_fallback(self):
        """Test generating a summary when no summary is available."""
        article_data = {
            "content": "First paragraph.\nSecond paragraph.\nThird paragraph.\nFourth paragraph.\nFifth paragraph."
        }
        
        # Short summary should include first paragraph
        short = WikipediaParser.generate_summary(article_data, level="short")
        assert "First paragraph" in short
        assert "Second paragraph" not in short
        
        # Medium summary should include first three paragraphs
        medium = WikipediaParser.generate_summary(article_data, level="medium")
        assert "First paragraph" in medium
        assert "Second paragraph" in medium
        assert "Third paragraph" in medium
        assert "Fourth paragraph" not in medium
        
        # Long summary should include first five paragraphs
        long = WikipediaParser.generate_summary(article_data, level="long")
        assert "First paragraph" in long
        assert "Fifth paragraph" in long 