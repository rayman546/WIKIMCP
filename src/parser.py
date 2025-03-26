from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import re
import logging
import sys

# Debug log function for console output
def debug_log(message):
    """Log to stderr so it doesn't interfere with JSON-RPC communication"""
    print(message, file=sys.stderr)

# Setup logging
logger = logging.getLogger(__name__)

class WikipediaParser:
    """Parser for Wikipedia content extraction and formatting."""
    
    @staticmethod
    def extract_clean_text(html_content: str) -> str:
        """
        Extract clean text from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            Clean text without HTML tags
        """
        if not html_content:
            return ""
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script_or_style in soup(['script', 'style']):
                script_or_style.decompose()
            
            # Get text and clean it
            text = soup.get_text()
            
            # Remove extra whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting clean text: {str(e)}")
            return ""
    
    @staticmethod
    def extract_sections(html_content: str) -> List[Dict[str, Any]]:
        """
        Extract sections from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of section dictionaries
        """
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            sections = []
            
            # Find all headings (h1-h6)
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for i, heading in enumerate(headings):
                # Get heading level (h1 -> 1, h2 -> 2, etc.)
                level = int(heading.name[1]) if heading.name and heading.name[0] == 'h' and len(heading.name) > 1 else 0
                title = heading.get_text().strip() if heading else ""
                
                # Get content until next heading
                content_elements = []
                curr_elem = heading.next_sibling if heading else None
                
                while curr_elem and not (
                    hasattr(curr_elem, 'name') and 
                    curr_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
                ):
                    if hasattr(curr_elem, 'name') and curr_elem.name in ['p', 'ul', 'ol', 'table', 'div', 'blockquote']:
                        content_elements.append(str(curr_elem))
                    curr_elem = curr_elem.next_sibling
                    
                    # Safety check for complex pages
                    if len(content_elements) > 100:
                        break
                
                # Create section object
                section = {
                    "level": level,
                    "title": title,
                    "html_content": "".join(content_elements),
                    "text_content": WikipediaParser.extract_clean_text("".join(content_elements))
                }
                
                sections.append(section)
            
            return sections
        except Exception as e:
            logger.error(f"Error extracting sections: {str(e)}")
            return []
    
    @staticmethod
    def extract_citations(html_content: str) -> List[Dict[str, str]]:
        """
        Extract citations from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of citation dictionaries
        """
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            citations = []
            
            # Find all citation elements (typically in a references section)
            reference_list = soup.find('ol', class_='references')
            if reference_list:
                for i, li in enumerate(reference_list.find_all('li')):
                    citation_id = li.get('id', f'citation-{i}')
                    citation_text = li.get_text().strip() if li else ""
                    
                    # Extract URLs if available
                    urls = []
                    for a in li.find_all('a', href=True) if li else []:
                        href = a.get('href')
                        if href and href.startswith('http'):
                            urls.append(href)
                    
                    citations.append({
                        "id": citation_id,
                        "text": citation_text,
                        "urls": urls
                    })
            
            return citations
        except Exception as e:
            logger.error(f"Error extracting citations: {str(e)}")
            return []
    
    @staticmethod
    def extract_tables(html_content: str) -> List[Dict[str, Any]]:
        """
        Extract tables from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of table dictionaries
        """
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = []
            
            for i, table in enumerate(soup.find_all('table')):
                # Try to find caption/title
                caption_elem = table.find('caption')
                caption = caption_elem.get_text().strip() if caption_elem else f"Table {i+1}"
                
                # Extract headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                
                # Extract rows
                rows = []
                for tr in table.find_all('tr')[1:]:  # Skip header row
                    if tr:
                        row = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
                        if row:  # Skip empty rows
                            rows.append(row)
                
                tables.append({
                    "caption": caption,
                    "headers": headers,
                    "rows": rows,
                    "html": str(table)
                })
            
            return tables
        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}")
            return []
    
    @staticmethod
    def extract_images(html_content: str) -> List[Dict[str, str]]:
        """
        Extract images from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of image dictionaries
        """
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            images = []
            
            for img in soup.find_all('img'):
                if img:
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    
                    # Fix protocol-relative URLs
                    if src.startswith('//'):
                        src = 'https:' + src
                    
                    # Only include non-empty images
                    if src:
                        images.append({
                            "src": src,
                            "alt": alt
                        })
            
            return images
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            return []
    
    @staticmethod
    def extract_infobox(html_content: str) -> Optional[Dict[str, str]]:
        """
        Extract infobox data from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            Dictionary of infobox key-value pairs
        """
        if not html_content:
            return None
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find infobox (different Wikipedia versions might use different classes)
            infobox = soup.find('table', class_=re.compile(r'infobox|vcard'))
            if not infobox:
                return None
            
            infobox_data = {}
            
            # Extract rows
            for row in infobox.find_all('tr'):
                if row:
                    # Find header/label and value
                    header = row.find(['th', 'td', 'div'], class_='infobox-label')
                    value = row.find(['td', 'div'], class_='infobox-data')
                    
                    # If both exist, add to data
                    if header and value:
                        key = header.get_text().strip()
                        val = value.get_text().strip()
                        infobox_data[key] = val
            
            return infobox_data
        except Exception as e:
            logger.error(f"Error extracting infobox: {str(e)}")
            return None
    
    @staticmethod
    def parse_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified method to parse all components of a Wikipedia article in one pass.
        
        Args:
            article_data: Raw article data from WikipediaClient
            
        Returns:
            Comprehensive parsed article data
        """
        # Check if this is a disambiguation page
        if "error" in article_data and article_data["error"] == "disambiguation":
            debug_log(f"Processing disambiguation page: {article_data.get('title', 'Unknown')}")
            return {
                "type": "disambiguation",
                "title": article_data.get("title", "Unknown"),
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }
        
        try:
            # Get basic data
            title = article_data.get("title", "Unknown")
            url = article_data.get("url", "")
            html_content = article_data.get("html", "")
            summary = article_data.get("summary", "")
            
            debug_log(f"Parsing article: {title}")
            
            # Parse HTML content with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract data using specialized methods
            citations = WikipediaParser._extract_citations(soup)
            sections = WikipediaParser._extract_sections(soup)
            tables = WikipediaParser._extract_tables(soup)
            images = WikipediaParser._extract_images(soup)
            infobox = WikipediaParser._extract_infobox(soup)
            
            # Return comprehensive article data
            return {
                "type": "article",
                "title": title,
                "summary": summary,
                "url": url,
                "sections": sections,
                "citations": citations,
                "tables": tables,
                "images": images,
                "infobox": infobox,
                "categories": article_data.get("categories", []),
                "links": article_data.get("links", [])
            }
        except Exception as e:
            logger.error(f"Error parsing article: {str(e)}")
            debug_log(f"Error parsing article: {str(e)}")
            # Return a minimal valid response with error information
            return {
                "type": "article",
                "title": article_data.get("title", "Unknown"),
                "summary": article_data.get("summary", ""),
                "url": article_data.get("url", ""),
                "error": str(e),
                "sections": [],
                "citations": [],
                "tables": [],
                "images": [],
                "infobox": {},
                "categories": article_data.get("categories", []),
                "links": article_data.get("links", [])
            }
    
    @staticmethod
    def _extract_citations(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract citations from the article."""
        try:
            citations = []
            cite_notes = soup.select(".reference-text")
            
            for i, cite in enumerate(cite_notes):
                citation_text = cite.get_text().strip()
                citations.append({
                    "id": i + 1,
                    "text": citation_text
                })
            
            return citations
        except Exception as e:
            logger.error(f"Error extracting citations: {str(e)}")
            debug_log(f"Error extracting citations: {str(e)}")
            return []
    
    @staticmethod
    def _extract_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract sections with hierarchical structure."""
        try:
            sections = []
            current_section = None
            
            # Find all headings
            headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            
            for heading in headings:
                # Skip table of contents and reference sections
                if heading.get("id") == "toc" or "References" in heading.get_text():
                    continue
                
                # Get heading level
                level = int(heading.name[1])
                title = heading.get_text().strip()
                
                # Get section content
                content = ""
                next_tag = heading.find_next_sibling()
                while next_tag and next_tag.name not in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    if next_tag.name in ["p", "ul", "ol"]:
                        content += next_tag.get_text().strip() + "\n\n"
                    next_tag = next_tag.find_next_sibling()
                
                # Create section object
                section = {
                    "level": level,
                    "title": title,
                    "content": content.strip(),
                    "subsections": []
                }
                
                # Add to section hierarchy
                if level == 2:  # Top-level section
                    sections.append(section)
                    current_section = section
                elif level > 2 and current_section:  # Subsection
                    current_section["subsections"].append(section)
            
            return sections
        except Exception as e:
            logger.error(f"Error extracting sections: {str(e)}")
            debug_log(f"Error extracting sections: {str(e)}")
            return []
    
    @staticmethod
    def _extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables from the article."""
        try:
            tables = []
            table_elements = soup.select("table.wikitable")
            
            for i, table in enumerate(table_elements):
                # Get table caption/title
                caption = table.find("caption")
                title = caption.get_text().strip() if caption else f"Table {i+1}"
                
                # Get table headers
                headers = []
                header_row = table.select_one("tr th") and table.select("tr th")
                if header_row:
                    headers = [th.get_text().strip() for th in header_row]
                
                # Get table rows
                rows = []
                data_rows = table.select("tr")
                for row in data_rows:
                    # Skip header row
                    if row.find("th") and row.find("th").parent == row:
                        continue
                    
                    cells = [td.get_text().strip() for td in row.find_all(["td"])]
                    if cells:
                        rows.append(cells)
                
                tables.append({
                    "title": title,
                    "headers": headers,
                    "rows": rows
                })
            
            return tables
        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}")
            debug_log(f"Error extracting tables: {str(e)}")
            return []
    
    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract images from the article."""
        try:
            images = []
            image_elements = soup.select(".image img")
            
            for img in image_elements:
                src = img.get("src", "")
                if src and not src.startswith("data:"):
                    # Ensure src is a full URL
                    if src.startswith("//"):
                        src = "https:" + src
                    
                    # Get caption if available
                    caption = ""
                    caption_element = img.parent.parent.find("div", class_="thumbcaption")
                    if caption_element:
                        caption = caption_element.get_text().strip()
                    
                    images.append({
                        "src": src,
                        "caption": caption,
                        "alt": img.get("alt", "")
                    })
            
            return images
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            debug_log(f"Error extracting images: {str(e)}")
            return []
    
    @staticmethod
    def _extract_infobox(soup: BeautifulSoup) -> Dict[str, str]:
        """Extract infobox data from the article."""
        try:
            infobox = {}
            infobox_table = soup.select_one(".infobox")
            
            if infobox_table:
                # Process each row in the infobox
                rows = infobox_table.select("tr")
                for row in rows:
                    # Skip rows without th elements
                    if not row.find("th"):
                        continue
                    
                    key = row.find("th").get_text().strip()
                    value = row.find("td").get_text().strip() if row.find("td") else ""
                    
                    # Clean up the value (remove citation numbers, etc.)
                    value = re.sub(r'\[\d+\]', '', value)
                    
                    if key and value:
                        infobox[key] = value
            
            return infobox
        except Exception as e:
            logger.error(f"Error extracting infobox: {str(e)}")
            debug_log(f"Error extracting infobox: {str(e)}")
            return {}
    
    @staticmethod
    def format_for_llm(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format article data for optimal LLM consumption.
        
        Args:
            article_data: Raw article data
            
        Returns:
            Formatted data optimized for LLM processing
        """
        # For pre-parsed data (using parse_article), just return it
        if "type" in article_data and article_data["type"] in ["article", "disambiguation"]:
            return article_data
            
        # Otherwise, parse it
        return WikipediaParser.parse_article(article_data)
    
    @staticmethod
    def generate_summary(article_data: Dict[str, Any], level: str = "medium") -> str:
        """
        Generate a summary of the article at the specified detail level.
        
        Args:
            article_data: Either raw article data or parsed article data
            level: Detail level (short, medium, long)
            
        Returns:
            Formatted summary
        """
        # Handle disambiguation pages
        if "error" in article_data and article_data["error"] == "disambiguation":
            options_str = ", ".join(article_data.get("options", [])[:10])
            if len(article_data.get("options", [])) > 10:
                options_str += f", and {len(article_data.get('options', [])) - 10} more"
            return f"Disambiguation: Multiple articles found for this title: {options_str}"
        
        # For pre-parsed data using parse_article
        if "type" in article_data and article_data["type"] == "article":
            title = article_data.get("title", "")
            base_summary = article_data.get("summary", "")
            sections = article_data.get("sections", [])
        else:
            # Handle raw article data
            title = article_data.get("title", "")
            base_summary = article_data.get("summary", "")
            html_content = article_data.get("html", "")
            sections = WikipediaParser.extract_sections(html_content)
        
        # Generate summary based on level
        if level == "short":
            # Short: Just use the first few sentences from base summary
            if base_summary:
                sentences = base_summary.split('.')
                short_summary = '.'.join(sentences[:2]).strip() + '.'
                return short_summary
            return "No summary available."
            
        elif level == "medium":
            # Medium: Use the full base summary
            return base_summary if base_summary else "No summary available."
            
        elif level == "long":
            # Long: Combine base summary with section highlights
            long_summary = base_summary + "\n\n" if base_summary else ""
            
            # Add section highlights
            for section in sections[:5]:  # Limit to first 5 sections
                if section["level"] <= 2:  # Only main sections
                    section_text = section.get("text_content", "")
                    if section_text:
                        sentences = section_text.split('.')
                        if len(sentences) > 3:
                            section_summary = '.'.join(sentences[:3]).strip() + '.'
                        else:
                            section_summary = section_text
                        
                        long_summary += f"{section.get('title', 'Section')}: {section_summary}\n\n"
            
            return long_summary.strip()
        
        # Fallback
        return base_summary if base_summary else "No summary available." 