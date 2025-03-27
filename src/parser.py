"""
Parser for Wikipedia content extraction and formatting.
"""
import asyncio # Import asyncio
import re
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor # For running sync code

# Setup logging
logger = logging.getLogger(__name__)

# Create a reusable executor
# Consider making the number of workers configurable
executor = ThreadPoolExecutor(max_workers=os.cpu_count())

# Helper function to run sync code in executor
async def run_sync_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

# --- Sync BeautifulSoup processing functions ---
# These will be called via run_sync_in_executor

def _sync_extract_clean_text(html_content: str) -> str:
    """Synchronous version of clean text extraction."""
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        logger.error(f"Sync Error extracting clean text: {str(e)}", exc_info=True)
        return "" # Or raise?

def _sync_extract_citations(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Synchronous citation extraction."""
    try:
        citations = []
        cite_notes = soup.select(".reference-text")
        for i, cite in enumerate(cite_notes):
            citation_text = cite.get_text().strip()
            citations.append({"id": i + 1, "text": citation_text})
        return citations
    except Exception as e:
        logger.error(f"Sync Error extracting citations: {str(e)}", exc_info=True)
        return []

def _sync_extract_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Synchronous section extraction."""
    try:
        sections = []
        current_section = None
        content_div = soup.find("div", {"id": "mw-content-text"})
        if not content_div: return []

        for element in content_div.children:
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if current_section: sections.append(current_section)
                level = int(element.name[1])
                title = element.get_text().strip()
                current_section = {"level": level, "title": title, "text_content": "", "subsections": []}
            elif current_section and element.name == "p":
                text = element.get_text().strip()
                if text: current_section["text_content"] += text + "\n\n"
        if current_section: sections.append(current_section)
        return sections
    except Exception as e:
        logger.error(f"Sync Error extracting sections: {str(e)}", exc_info=True)
        return []

def _sync_extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Synchronous table extraction."""
    try:
        tables = []
        table_elements = soup.find_all("table", {"class": "wikitable"})
        for i, table in enumerate(table_elements):
            caption = table.find("caption")
            title = caption.get_text().strip() if caption else f"Table {i + 1}"
            headers = []
            header_row = table.find("tr")
            if header_row: headers = [th.get_text().strip() for th in header_row.find_all(["th", "td"])]
            rows = []
            for row in table.find_all("tr")[1:]:
                cells = [td.get_text().strip() for td in row.find_all(["td", "th"])]
                if cells: rows.append(cells)
            tables.append({"title": title, "headers": headers, "rows": rows})
        return tables
    except Exception as e:
        logger.error(f"Sync Error extracting tables: {str(e)}", exc_info=True)
        return []

def _sync_extract_images(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Synchronous image extraction."""
    try:
        images = []
        image_elements = soup.find_all("img")
        for img in image_elements:
            src = img.get("src", "")
            # Basic filtering, might need refinement
            if not src or src.startswith('data:'): continue
            # Ensure protocol is present for external images
            if src.startswith('//'): src = 'https:' + src

            figure = img.find_parent("figure")
            caption = ""
            if figure:
                caption_elem = figure.find("figcaption")
                if caption_elem: caption = caption_elem.get_text().strip()
            images.append({"src": src, "alt": img.get("alt", ""), "caption": caption})
        return images
    except Exception as e:
        logger.error(f"Sync Error extracting images: {str(e)}", exc_info=True)
        return []

def _sync_extract_infobox(soup: BeautifulSoup) -> Dict[str, str]:
    """Synchronous infobox extraction."""
    try:
        infobox = {}
        infobox_table = soup.select_one(".infobox")
        if infobox_table:
            rows = infobox_table.select("tr")
            for row in rows:
                if not row.find("th"): continue
                key_elem = row.find("th")
                val_elem = row.find("td")
                if key_elem and val_elem: # Ensure both key and value elements exist
                    key = key_elem.get_text().strip()
                    value = val_elem.get_text().strip()
                    value = re.sub(r'\[\d+\]', '', value).strip() # Clean value
                    if key and value: infobox[key] = value
        return infobox
    except Exception as e:
        logger.error(f"Sync Error extracting infobox: {str(e)}", exc_info=True)
        return {}

def _sync_parse_article_from_html(html_content: str) -> Dict[str, Any]:
    """Synchronous parsing of components from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Run individual sync extractors
    citations = _sync_extract_citations(soup)
    sections = _sync_extract_sections(soup)
    tables = _sync_extract_tables(soup)
    images = _sync_extract_images(soup)
    infobox = _sync_extract_infobox(soup)
    return {
        "citations": citations,
        "sections": sections,
        "tables": tables,
        "images": images,
        "infobox": infobox,
    }

# --- End Sync Functions ---

# Setup logging
logger = logging.getLogger(__name__)

class WikipediaParser:
    """Parser for Wikipedia content extraction and formatting."""
    
    @staticmethod
    async def extract_clean_text(html_content: str) -> str:
        """
        Extract clean text from HTML content (async).
        Runs BeautifulSoup parsing in an executor.
        """
        return await run_sync_in_executor(_sync_extract_clean_text, html_content)

    @staticmethod
    async def parse_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified method to parse all components of a Wikipedia article (async).
        Runs BeautifulSoup parsing in an executor.
        """
        # Handle disambiguation pages (no parsing needed)
        if "error" in article_data and article_data["error"] == "disambiguation":
            logger.debug(f"Processing disambiguation page: {article_data.get('title', 'Unknown')}")
            return {
                "type": "disambiguation",
                "title": article_data.get("title", "Unknown"),
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }

        try:
            title = article_data.get("title", "Unknown")
            url = article_data.get("url", "")
            html_content = article_data.get("html", "")
            summary = article_data.get("summary", "")
            logger.debug(f"Parsing article: {title}")

            # Run the synchronous parsing function in the executor
            parsed_components = await run_sync_in_executor(_sync_parse_article_from_html, html_content)

            # Combine with non-parsed data
            return {
                "type": "article",
                "title": title,
                "summary": summary,
                "url": url,
                **parsed_components, # Add results from sync parsing
                "categories": article_data.get("categories", []),
                "links": article_data.get("links", [])
            }
        except Exception as e:
            # TODO: Raise specific ParsingError (Phase 3)
            logger.error(f"Error parsing article '{title}': {str(e)}", exc_info=True)
            # Return minimal error structure for now
            return {
                "type": "error", # Indicate error type
                "title": article_data.get("title", "Unknown"),
                "error": f"Failed to parse article: {str(e)}",
            }

    # Note: The individual _extract_* methods are now synchronous helpers (_sync_extract_*)
    # called by _sync_parse_article_from_html, which runs in the executor.
    # We keep the static methods on the class for organization but they are not directly async.

    @staticmethod
    async def format_for_llm(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format article data for optimal LLM consumption (async).
        """
        # If already parsed, return directly
        if "type" in article_data and article_data["type"] in ["article", "disambiguation", "error"]:
            return article_data

        # Otherwise, parse it asynchronously
        return await WikipediaParser.parse_article(article_data)

    @staticmethod
    async def generate_summary(article_data: Dict[str, Any], level: str = "medium") -> str:
        """
        Generate a summary of the article (async).
        """
        # Handle disambiguation or error types directly
        if "type" in article_data:
            if article_data["type"] == "disambiguation":
                options_str = ", ".join(article_data.get("options", [])[:10])
                # Add ellipsis if more options exist
                if len(article_data.get("options", [])) > 10:
                    options_str += f", and {len(article_data.get('options', [])) - 10} more"
                return f"Disambiguation: '{article_data.get('title', 'Unknown')}' may refer to: {options_str}"
            elif article_data["type"] == "error":
                return f"Error: {article_data.get('error', 'Could not process article.')}"

        # If not already parsed, parse it first
        if "type" not in article_data or article_data["type"] != "article":
             logger.debug("generate_summary received unparsed data, parsing first...")
             parsed_data = await WikipediaParser.parse_article(article_data)
             # Check if parsing failed
             if parsed_data.get("type") == "error":
                 return f"Error: {parsed_data.get('error', 'Could not parse article for summary.')}"
             article_data = parsed_data # Use parsed data

        # Now we assume article_data is a parsed article
        title = article_data.get("title", "")
        base_summary = article_data.get("summary", "")
        sections = article_data.get("sections", [])

        # Generate summary based on level (sync logic is fine here)
        if level == "short":
            if base_summary:
                sentences = base_summary.split('.')
                # Take first 2 non-empty sentences
                short_summary = '.'.join(filter(None, [s.strip() for s in sentences[:3]]))
                return short_summary + '.' if short_summary else "No summary available."
            return "No summary available."

        elif level == "medium":
            return base_summary if base_summary else "No summary available."

        elif level == "long":
            long_summary = base_summary + "\n\n" if base_summary else ""
            for section in sections[:5]:
                if section.get("level", 99) <= 2: # Check level safely
                    section_text = section.get("text_content", "")
                    if section_text:
                        # Take first few sentences of the section text
                        sentences = section_text.split('.')
                        section_summary = '.'.join(filter(None, [s.strip() for s in sentences[:4]]))
                        if section_summary:
                             long_summary += f"\n-- {section.get('title', 'Section')} --\n{section_summary}.\n"

            return long_summary.strip() if long_summary.strip() else "No detailed summary available."

        # Fallback
        return base_summary if base_summary else "No summary available."
