import time
import sys
import logging
from typing import Dict, List, Optional, Union, Any

# Debug log function for console output
def debug_log(message):
    """Log to stderr so it doesn't interfere with JSON-RPC communication"""
    print(message, file=sys.stderr)

# Setup logging
logger = logging.getLogger(__name__)

class ArticleNotFoundError(Exception):
    """Custom exception for article not found errors."""
    pass

class WikipediaClient:
    """Client for interacting with the Wikipedia API."""
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize the Wikipedia client.
        
        Args:
            rate_limit_delay: Delay in seconds between consecutive API calls
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        
        # Try to import wikipedia here to handle import errors gracefully
        try:
            import wikipedia
            self.wikipedia = wikipedia
            try:
                from bs4 import BeautifulSoup
                self.BeautifulSoup = BeautifulSoup
            except ImportError:
                debug_log("Error: No module named 'bs4' (BeautifulSoup)")
                debug_log("Make sure you have installed all dependencies: pip install -r requirements.txt")
                raise ImportError("Missing dependency: bs4 (BeautifulSoup)")
        except ImportError:
            debug_log("Error: No module named 'wikipedia'")
            debug_log("Make sure you have installed all dependencies: pip install -r requirements.txt")
            raise ImportError("Missing dependency: wikipedia")
        
    def _respect_rate_limit(self):
        """Ensure rate limiting by adding delay if needed."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def search(self, query: str, results: int = 10) -> List[str]:
        """
        Search for Wikipedia articles.
        
        Args:
            query: Search term
            results: Maximum number of results to return
            
        Returns:
            List of article titles
        """
        self._respect_rate_limit()
        try:
            return self.wikipedia.search(query, results=results)
        except Exception as e:
            logger.error(f"Wikipedia search error: {str(e)}")
            debug_log(f"Wikipedia search error: {str(e)}")
            raise Exception(f"Wikipedia search error: {str(e)}")
    
    def get_article(self, title: str, auto_suggest: bool = True) -> Dict[str, Any]:
        """
        Get a Wikipedia article by title.
        
        Args:
            title: Article title
            auto_suggest: Whether to auto-suggest similar titles
            
        Returns:
            Dictionary containing essential article data (title, url, html, summary)
        """
        self._respect_rate_limit()
        try:
            page = self.wikipedia.page(title, auto_suggest=auto_suggest)
            return {
                "title": page.title,
                "url": page.url,
                "html": page.html(),
                "summary": page.summary,
                "content": page.content,  # Keep raw content for full-text processing if needed
                "images": page.images,    # Keep basic metadata for convenience
                "links": page.links,      # Keep basic metadata for convenience
                "categories": page.categories  # Keep basic metadata for convenience
            }
        except self.wikipedia.exceptions.DisambiguationError as e:
            # Handle disambiguation pages
            logger.info(f"Disambiguation page found for '{title}': {str(e)}")
            debug_log(f"Disambiguation page found for '{title}': {str(e)}")
            return {
                "error": "disambiguation",
                "message": str(e),
                "options": e.options
            }
        except self.wikipedia.exceptions.PageError as e:
            logger.error(f"Page not found: {title} - {str(e)}")
            debug_log(f"Page not found: {title} - {str(e)}")
            raise ArticleNotFoundError(f"Page not found: {title}")
        except Exception as e:
            logger.error(f"Error retrieving article '{title}': {str(e)}")
            debug_log(f"Error retrieving article '{title}': {str(e)}")
            raise Exception(f"Error retrieving article: {str(e)}")
    
    def get_summary(self, title: str, sentences: int = 5) -> str:
        """
        Get a summary of a Wikipedia article.
        
        Args:
            title: Article title
            sentences: Number of sentences to include in summary
            
        Returns:
            Summary text
        """
        self._respect_rate_limit()
        try:
            return self.wikipedia.summary(title, sentences=sentences)
        except self.wikipedia.exceptions.DisambiguationError as e:
            # Handle disambiguation pages
            options_str = ", ".join(e.options[:10])
            if len(e.options) > 10:
                options_str += f", and {len(e.options) - 10} more"
            debug_log(f"Disambiguation page found for '{title}': {str(e)}")
            return f"Disambiguation: '{title}' may refer to multiple articles: {options_str}"
        except self.wikipedia.exceptions.PageError as e:
            logger.error(f"Page not found for summary: {title} - {str(e)}")
            debug_log(f"Page not found for summary: {title} - {str(e)}")
            raise ArticleNotFoundError(f"Page not found: {title}")
        except Exception as e:
            logger.error(f"Error retrieving summary for '{title}': {str(e)}")
            debug_log(f"Error retrieving summary for '{title}': {str(e)}")
            raise Exception(f"Error retrieving summary: {str(e)}")
    
    def _extract_sections(self, page) -> List[Dict[str, Any]]:
        """
        Extract sections from a Wikipedia page.
        
        Args:
            page: Wikipedia page object
            
        Returns:
            List of section dictionaries
        """
        sections = []
        
        # Parse HTML to extract sections
        soup = self.BeautifulSoup(page.html(), 'html.parser')
        
        # Find all headings (h1-h6)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for i, heading in enumerate(headings):
            section = {
                "level": int(heading.name[1]),  # h1 -> 1, h2 -> 2, etc.
                "title": heading.get_text().strip(),
                "content": ""
            }
            
            # Get content until next heading
            content_elements = []
            next_sibling = heading.next_sibling
            
            while next_sibling and next_sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if next_sibling.name in ['p', 'ul', 'ol', 'table']:
                    content_elements.append(str(next_sibling))
                next_sibling = next_sibling.next_sibling
                
                # Safety check for complex pages
                if len(content_elements) > 100:
                    break
            
            section["content"] = "".join(content_elements)
            sections.append(section)
        
        return sections 