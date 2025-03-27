Can you use braimport asyncio # Import asyncio
import logging
import time
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# Setup logging
logger = logging.getLogger(__name__)

class ArticleNotFoundError(Exception):
    """Raised when an article is not found."""
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
                logger.error("Missing dependency: bs4 (BeautifulSoup)")
                raise ImportError("Missing dependency: bs4 (BeautifulSoup)")
        except ImportError:
            logger.error("Missing dependency: wikipedia")
            raise ImportError("Missing dependency: wikipedia")

    async def _respect_rate_limit(self):
        """Ensure rate limiting by adding delay if needed (async version)."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_duration = self.rate_limit_delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_duration:.2f} seconds")
            await asyncio.sleep(sleep_duration) # Use asyncio.sleep

        self.last_request_time = time.time() # Update last request time after potential sleep

    async def search(self, query: str, results: int = 10) -> List[str]:
        """
        Search for Wikipedia articles (async version).

        Args:
            query: Search term
            results: Maximum number of results to return
            
        Returns:
            List of article titles
        """
        await self._respect_rate_limit()
        loop = asyncio.get_running_loop()
        try:
            # Run blocking call in executor
            search_results = await loop.run_in_executor(
                None, self.wikipedia.search, query, results
            )
            return search_results
        except Exception as e:
            logger.error(f"Wikipedia search error for '{query}': {str(e)}", exc_info=True)
            # Raise a more specific error later (e.g., WikipediaError)
            raise WikipediaError(f"Wikipedia search failed: {str(e)}")

    async def get_article(self, title: str, auto_suggest: bool = True) -> Dict[str, Any]:
        """
        Get a Wikipedia article by title (async version).

        Args:
            title: Article title
            auto_suggest: Whether to auto-suggest similar titles
            
        Returns:
            Dictionary containing essential article data (title, url, html, summary, etc.)
        """
        await self._respect_rate_limit()
        loop = asyncio.get_running_loop()
        try:
            # Run blocking wikipedia.page call in executor
            page = await loop.run_in_executor(
                None, self.wikipedia.page, title, auto_suggest
            )

            # Run blocking page.html() call in executor
            html_content = await loop.run_in_executor(None, page.html)

            # Other attributes like summary, content, images, links, categories are usually cached
            # by the library after the initial page load, so accessing them might not block significantly.
            # However, if they trigger further network calls, they should also be run in executor.
            # For now, assume they are relatively quick.
            return {
                "title": page.title,
                "url": page.url,
                "html": html_content,
                "summary": page.summary,
                "content": page.content,
                "images": page.images,
                "links": page.links,
                "categories": page.categories
            }
        except self.wikipedia.exceptions.DisambiguationError as e:
            # TODO: Refactor to raise DisambiguationAPIError (Phase 2)
            logger.info(f"Disambiguation page found for '{title}': {str(e)}")
            # Returning dict for now, will change to raise error later
            return {
                "error": "disambiguation",
                "message": str(e),
                "options": e.options
            }
        except self.wikipedia.exceptions.PageError as e:
            logger.warning(f"Page not found for article: {title} - {str(e)}")
            raise NotFoundError(f"Page not found: {title}") # Use specific APIError
        except Exception as e:
            logger.error(f"Error retrieving article '{title}': {str(e)}", exc_info=True)
            raise WikipediaError(f"Error retrieving article: {str(e)}")

    async def get_summary(self, title: str, sentences: int = 5) -> str:
        """
        Get a summary of a Wikipedia article (async version).

        Args:
            title: Article title
            sentences: Number of sentences to include in summary
            
        Returns:
            Summary text
        """
        await self._respect_rate_limit()
        loop = asyncio.get_running_loop()
        try:
            # Run blocking call in executor
            summary_text = await loop.run_in_executor(
                None, self.wikipedia.summary, title, sentences
            )
            return summary_text
        except self.wikipedia.exceptions.DisambiguationError as e:
            # TODO: Refactor to raise DisambiguationAPIError (Phase 2)
            options_str = ", ".join(e.options[:10])
            if len(e.options) > 10:
                options_str += f", and {len(e.options) - 10} more"
            logger.info(f"Disambiguation page found for summary '{title}': {str(e)}")
            # Returning string for now, will change to raise error later
            return f"Disambiguation: '{title}' may refer to multiple articles: {options_str}"
        except self.wikipedia.exceptions.PageError as e:
            logger.warning(f"Page not found for summary: {title} - {str(e)}")
            raise NotFoundError(f"Page not found: {title}") # Use specific APIError
        except Exception as e:
            logger.error(f"Error retrieving summary for '{title}': {str(e)}", exc_info=True)
            raise WikipediaError(f"Error retrieving summary: {str(e)}")

    # Removed redundant _extract_sections method. Parsing is handled by WikipediaParser.
