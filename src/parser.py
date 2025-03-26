from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import re

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
    
    @staticmethod
    def extract_sections(html_content: str) -> List[Dict[str, Any]]:
        """
        Extract sections from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of section dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = []
        
        # Find all headings (h1-h6)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for i, heading in enumerate(headings):
            # Get heading level (h1 -> 1, h2 -> 2, etc.)
            level = int(heading.name[1])
            title = heading.get_text().strip()
            
            # Get content until next heading
            content_elements = []
            curr_elem = heading.next_sibling
            
            while curr_elem and not (
                isinstance(curr_elem, BeautifulSoup) and 
                curr_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            ):
                if curr_elem.name in ['p', 'ul', 'ol', 'table', 'div', 'blockquote']:
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
    
    @staticmethod
    def extract_citations(html_content: str) -> List[Dict[str, str]]:
        """
        Extract citations from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of citation dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        citations = []
        
        # Find all citation elements (typically in a references section)
        reference_list = soup.find('ol', class_='references')
        if reference_list:
            for i, li in enumerate(reference_list.find_all('li')):
                citation_id = li.get('id', f'citation-{i}')
                citation_text = li.get_text().strip()
                
                # Extract URLs if available
                urls = []
                for a in li.find_all('a', href=True):
                    href = a.get('href')
                    if href and href.startswith('http'):
                        urls.append(href)
                
                citations.append({
                    "id": citation_id,
                    "text": citation_text,
                    "urls": urls
                })
        
        return citations
    
    @staticmethod
    def extract_tables(html_content: str) -> List[Dict[str, Any]]:
        """
        Extract tables from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of table dictionaries
        """
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
    
    @staticmethod
    def extract_images(html_content: str) -> List[Dict[str, str]]:
        """
        Extract images from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            List of image dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []
        
        for img in soup.find_all('img'):
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
    
    @staticmethod
    def extract_infobox(html_content: str) -> Optional[Dict[str, str]]:
        """
        Extract infobox data from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            Dictionary of infobox key-value pairs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find infobox (different Wikipedia versions might use different classes)
        infobox = soup.find('table', class_=re.compile(r'infobox|vcard'))
        if not infobox:
            return None
        
        infobox_data = {}
        
        # Extract rows
        for row in infobox.find_all('tr'):
            # Find header/label and value
            header = row.find(['th', 'td', 'div'], class_='infobox-label')
            value = row.find(['td', 'div'], class_='infobox-data')
            
            # If both exist, add to data
            if header and value:
                key = header.get_text().strip()
                val = value.get_text().strip()
                infobox_data[key] = val
        
        return infobox_data
    
    @staticmethod
    def format_for_llm(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format article data for optimal LLM consumption.
        
        Args:
            article_data: Raw article data
            
        Returns:
            Formatted data optimized for LLM processing
        """
        # Check if this is a disambiguation page
        if "error" in article_data and article_data["error"] == "disambiguation":
            return {
                "type": "disambiguation",
                "title": article_data.get("title", "Unknown"),
                "options": article_data.get("options", []),
                "message": article_data.get("message", "")
            }
        
        # Parse HTML content
        html_content = article_data.get("html", "")
        
        # Extract various components
        sections = WikipediaParser.extract_sections(html_content)
        citations = WikipediaParser.extract_citations(html_content)
        tables = WikipediaParser.extract_tables(html_content)
        images = WikipediaParser.extract_images(html_content)
        infobox = WikipediaParser.extract_infobox(html_content)
        
        # Construct formatted output
        formatted_data = {
            "type": "article",
            "title": article_data.get("title", "Unknown"),
            "summary": article_data.get("summary", ""),
            "url": article_data.get("url", ""),
            "sections": sections,
            "citations": citations,
            "tables": tables,
            "images": images[:10],  # Limit to first 10 images
            "infobox": infobox,
            "categories": article_data.get("categories", []),
            "links": article_data.get("links", [])[:100]  # Limit to first 100 links
        }
        
        return formatted_data
    
    @staticmethod
    def generate_summary(article_data: Dict[str, Any], level: str = "medium") -> str:
        """
        Generate a summary of an article.
        
        Args:
            article_data: Article data
            level: Summary detail level ('short', 'medium', 'long')
            
        Returns:
            Summary text
        """
        # Check if article already has a summary
        if "summary" in article_data and article_data["summary"]:
            summary = article_data["summary"]
            
            # Adjust length based on level
            if level == "short":
                # Return first paragraph or first 3 sentences
                paragraphs = summary.split('\n')
                if paragraphs:
                    first_para = paragraphs[0]
                    sentences = first_para.split('. ')
                    return '. '.join(sentences[:3]) + ('.' if not sentences[0].endswith('.') else '')
            elif level == "medium":
                # Return first 2-3 paragraphs or first 5-7 sentences
                paragraphs = summary.split('\n')
                if len(paragraphs) >= 2:
                    return '\n'.join(paragraphs[:2])
                else:
                    sentences = summary.split('. ')
                    return '. '.join(sentences[:5]) + ('.' if not sentences[0].endswith('.') else '')
            else:  # long
                return summary
        
        # If no summary is available, create one from the content
        content = article_data.get("content", "")
        if not content:
            return "No summary available."
        
        # Simple extractive summarization
        paragraphs = content.split('\n')
        paragraphs = [p for p in paragraphs if p.strip()]
        
        if level == "short":
            return paragraphs[0] if paragraphs else "No summary available."
        elif level == "medium":
            return '\n'.join(paragraphs[:3]) if paragraphs else "No summary available."
        else:  # long
            return '\n'.join(paragraphs[:5]) if paragraphs else "No summary available." 