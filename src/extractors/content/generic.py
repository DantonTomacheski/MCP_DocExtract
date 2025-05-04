"""
Generic content extractor implementation.

This module implements a generic content extraction strategy that works with most
documentation websites by using a multi-stage approach with selectors in priority order.
"""

import re
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import ParseResult
import logging
from bs4 import BeautifulSoup, Tag, NavigableString

from src.extractors.interfaces import IContentExtractor
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class GenericContentExtractor(IContentExtractor):
    """
    Generic content extractor implementation.
    
    This class implements the IContentExtractor interface for general documentation sites.
    It uses a multi-stage extraction process with fallbacks:
    
    1. Try content-specific selectors (article, main, etc.)
    2. Fall back to more general selectors if needed
    3. Apply content cleaning and normalization
    """
    
    def __init__(self):
        """Initialize the generic content extractor."""
        # Define priority selectors for content extraction
        self._priority_selectors = [
            "article.documentation",  # Common in modern doc sites
            "main.content",           # Common content container
            "article",                # HTML5 semantic element for content
            "main",                   # HTML5 semantic element for main content
            "div[role='main']",       # ARIA role for main content
            "div.content",            # Common class for content
            "div.documentation",      # Common class for documentation
            "div.main-content",       # Common class pattern
            "div.doc-content",        # Common class pattern
            ".markdown-body",         # GitHub-style docs
            "#content",               # Common ID for content
            "#main-content",          # Common ID pattern
            ".content-container"      # Fallback general container
        ]
        
        # Define elements that should be removed
        self._noise_selectors = [
            "header",                # Site header
            "footer",                # Site footer
            "nav",                   # Navigation elements
            ".sidebar",              # Sidebar elements
            ".navigation",           # Navigation elements
            ".menu",                 # Menu elements
            ".toc",                  # Table of contents that may duplicate
            ".breadcrumbs",          # Breadcrumb navigation
            ".admonition",           # Special notice boxes to handle separately
            ".search",               # Search elements
            ".cookie-banner",        # Cookie consent banners
            "script",                # Any inline scripts 
            "style",                 # Any inline styles
            "iframe",                # Iframes 
            "noscript",              # Noscript tags
            "[aria-hidden='true']",  # Hidden elements
            ".ads",                  # Advertisement elements
            ".announcement",         # Announcement banners
            ".modal",                # Modal dialogs
            ".popup"                 # Popup elements
        ]
    
    async def extract(self, html: str, url: ParseResult, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract the main content from the provided HTML.
        
        Args:
            html: Raw HTML content to extract from
            url: Parsed URL object for the page being processed
            context: Optional contextual information to assist extraction
            
        Returns:
            Dictionary containing:
                - 'title': Page title
                - 'content': Extracted main content
                - 'metadata': Additional metadata
                - 'elements': Key structural elements
                - 'success': Whether extraction was successful
                - 'extraction_method': The method that succeeded
                
        Raises:
            ExtractionError: If content extraction fails completely
        """
        if not html:
            logger.error("Empty HTML provided for extraction")
            return self._create_error_result("Empty HTML provided")
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = self._extract_title(soup)
        logger.debug(f"Extracted title: {title}")
        
        # Extract metadata
        metadata = self._extract_metadata(soup)
        
        # Try to extract content using priority selectors
        content_element, extraction_method = self._extract_content_element(soup)
        
        if not content_element:
            logger.warning(f"Could not find content container for {url.geturl()}")
            return self._create_error_result("Could not find content container")
        
        # Clean up the content
        self._clean_content(content_element)
        
        # Extract structured content elements (headings, lists, code blocks)
        elements = self._extract_structural_elements(content_element)
        
        # Convert cleaned content to string (HTML)
        content_html = str(content_element)
        
        # Return extraction results
        return {
            "title": title,
            "content": content_html,
            "metadata": metadata,
            "elements": elements,
            "success": True,
            "extraction_method": extraction_method
        }
    
    def get_priority_selectors(self) -> List[str]:
        """
        Get the ordered list of CSS selectors to try for content extraction.
        
        Returns:
            List of CSS selectors in priority order
        """
        return self._priority_selectors
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract the page title from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Page title as string
        """
        # Try different methods for title extraction
        
        # Method 1: Look for h1 in main content
        if main_content := soup.select_one(",".join(self._priority_selectors)):
            if h1 := main_content.select_one("h1"):
                return h1.get_text(strip=True)
        
        # Method 2: Main h1 on page
        if h1 := soup.select_one("h1"):
            return h1.get_text(strip=True)
            
        # Method 3: HTML title tag
        if title_tag := soup.title:
            # Clean up typical title format: "Page Name | Site Name"
            title_text = title_tag.get_text(strip=True)
            # Remove site name if it exists after pipe or dash
            if " | " in title_text:
                title_text = title_text.split(" | ")[0]
            elif " - " in title_text:
                title_text = title_text.split(" - ")[0]
            return title_text
            
        # Fallback
        return "Untitled Document"
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract page metadata from HTML meta tags.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of metadata values
        """
        metadata = {}
        
        # Extract OpenGraph metadata
        for meta in soup.select("meta[property^='og:']"):
            key = meta.get("property")[3:]  # Remove 'og:' prefix
            value = meta.get("content")
            if value:
                metadata[key] = value
                
        # Extract standard meta tags
        for meta in soup.select("meta[name]"):
            name = meta.get("name")
            value = meta.get("content")
            if name and value:
                metadata[name] = value
                
        # Extract canonical URL
        if link := soup.select_one("link[rel='canonical']"):
            metadata["canonical_url"] = link.get("href")
            
        # Extract last modified date if available
        if modified := soup.select_one("meta[name='last-modified']"):
            metadata["last_modified"] = modified.get("content")
            
        return metadata
    
    def _extract_content_element(self, soup: BeautifulSoup) -> Tuple[Optional[Tag], str]:
        """
        Extract the main content element using priority selectors.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Tuple of (content element or None, extraction method)
        """
        # Try each priority selector
        for selector in self._priority_selectors:
            if element := soup.select_one(selector):
                logger.debug(f"Found content using selector: {selector}")
                return element, f"priority_selector:{selector}"
        
        # Fallback method: Look for the div with most meaningful content
        candidate_elements = []
        for div in soup.find_all("div"):
            # Skip elements that are clearly navigation, header, footer, etc.
            skip_classes = ["nav", "menu", "header", "footer", "sidebar"]
            if any(cls in (div.get("class") or []) for cls in skip_classes):
                continue
                
            # Calculate content score based on presence of paragraphs, headings, and text length
            paragraphs = div.find_all("p")
            headings = div.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            code_blocks = div.find_all(["pre", "code"])
            
            # Only consider elements with some meaningful content
            if len(paragraphs) + len(headings) + len(code_blocks) > 0:
                # Simple score: weight paragraphs, headings and code blocks
                score = (len(paragraphs) * 2) + (len(headings) * 3) + (len(code_blocks) * 2)
                
                # Additional points for longer text content
                text_content = div.get_text(strip=True)
                score += min(len(text_content) / 100, 10)  # Cap text length contribution
                
                candidate_elements.append((div, score))
        
        # Sort candidates by score (descending)
        candidate_elements.sort(key=lambda x: x[1], reverse=True)
        
        # Return the highest scoring element if we have any candidates
        if candidate_elements:
            logger.debug(f"Used content scoring fallback, found {len(candidate_elements)} candidates")
            return candidate_elements[0][0], "content_scoring"
        
        # Last resort: return the body element
        if body := soup.body:
            logger.warning("Could not identify main content, using full body")
            return body, "full_body_fallback"
            
        # If we can't find body either, return None
        return None, "extraction_failed"
    
    def _clean_content(self, element: Tag) -> None:
        """
        Clean the content element by removing noise elements.
        
        Args:
            element: BeautifulSoup Tag to clean
            
        Returns:
            None (modifies element in place)
        """
        # Remove noise elements
        for selector in self._noise_selectors:
            for noise in element.select(selector):
                noise.decompose()
        
        # Remove empty paragraphs and divs
        for tag in element.find_all(["p", "div"]):
            if not tag.get_text(strip=True) and not tag.find_all(["img", "svg"]):
                tag.decompose()
                
        # Remove inline event handlers (onclick, etc.)
        for tag in element.find_all(True):  # Find all elements
            for attr in list(tag.attrs):
                if attr.startswith("on"):
                    del tag[attr]
                # Remove data attributes except those related to syntax highlighting
                elif attr.startswith("data-") and not attr in ["data-lang", "data-language"]:
                    del tag[attr]
                    
        # Handle code blocks: ensure they're properly formatted
        for pre in element.find_all("pre"):
            # Make sure code inside pre has proper tags
            if not pre.find("code") and pre.string:
                code_tag = soup.new_tag("code")
                code_tag.string = pre.string
                pre.string = ""
                pre.append(code_tag)
    
    def _extract_structural_elements(self, element: Tag) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract structured content elements for better processing.
        
        Args:
            element: BeautifulSoup Tag containing content
            
        Returns:
            Dictionary of structured elements
        """
        elements = {
            "headings": [],
            "lists": [],
            "code_blocks": [],
            "tables": [],
            "images": []
        }
        
        # Extract headings
        for heading_level in range(1, 7):
            for heading in element.find_all(f"h{heading_level}"):
                elements["headings"].append({
                    "level": heading_level,
                    "text": heading.get_text(strip=True),
                    "id": heading.get("id", "")
                })
        
        # Extract lists
        for list_tag in element.find_all(["ul", "ol"]):
            list_items = [li.get_text(strip=True) for li in list_tag.find_all("li")]
            elements["lists"].append({
                "type": list_tag.name,  # "ul" or "ol"
                "items": list_items
            })
            
        # Extract code blocks
        for pre in element.find_all("pre"):
            code = pre.find("code")
            language = ""
            
            # Try to determine the language
            if code and code.get("class"):
                for cls in code.get("class"):
                    if cls.startswith("language-") or cls.startswith("lang-"):
                        language = cls.split("-")[1]
                        break
            
            code_text = (code or pre).get_text()
            elements["code_blocks"].append({
                "language": language,
                "code": code_text
            })
            
        # Extract tables
        for table in element.find_all("table"):
            headers = []
            rows = []
            
            # Extract headers
            for th in table.select("thead th"):
                headers.append(th.get_text(strip=True))
                
            # Extract rows
            for tr in table.select("tbody tr"):
                row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if row:  # Only append non-empty rows
                    rows.append(row)
                    
            elements["tables"].append({
                "headers": headers,
                "rows": rows
            })
            
        # Extract images
        for img in element.find_all("img"):
            elements["images"].append({
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "title": img.get("title", "")
            })
            
        return elements
    
    def _create_error_result(self, message: str) -> Dict[str, Any]:
        """
        Create an error result dictionary.
        
        Args:
            message: Error message
            
        Returns:
            Error result dictionary
        """
        return {
            "title": "",
            "content": "",
            "metadata": {},
            "elements": {},
            "success": False,
            "extraction_method": "failed",
            "error": message
        }
