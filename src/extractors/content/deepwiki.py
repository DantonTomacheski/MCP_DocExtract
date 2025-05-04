"""
DeepWiki-specific content extraction implementation.

This module contains a content extractor specifically optimized for DeepWiki documentation sites.
DeepWiki sites typically have a specific DOM structure with consistent navigation and content panes.
"""

import re
from typing import Dict, List, Optional, Any, Union
from urllib.parse import ParseResult, urljoin
from bs4 import BeautifulSoup, Tag, NavigableString

from src.extractors.interfaces import IContentExtractor
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class DeepWikiContentExtractor(IContentExtractor):
    """
    DeepWiki-specific content extractor.
    
    This extractor is specialized for extracting content from DeepWiki-based documentation
    sites, which have a specific structure and content organization.
    """
    
    def __init__(self):
        """Initialize the DeepWiki content extractor."""
        # DeepWiki-specific selectors in priority order
        self._content_selectors = [
            # DeepWiki standard content containers
            "div.documentation-content",
            "div.wiki-content", 
            "div.deepwiki-content",
            "div.deepwiki-article",
            "main.content-wrapper",
            "div.content-wrapper",
            
            # Common DeepWiki layouts
            "div.deepwiki-container main",
            "div.deepwiki-container div.main",
            "div.deepwiki-body",
            
            # Fallbacks for DeepWiki variations
            "article.content", 
            "article.wiki-article",
            "div.article-content",
            "div.doc-content",
            
            # Last resort generic selectors
            "main",
            "article",
            "div[role='main']",
            "div.main"
        ]
        
        # Content blocks to exclude (navigation, sidebars, headers)
        self._exclude_selectors = [
            "div.deepwiki-sidebar",
            "div.sidebar",
            "nav",
            "header",
            "footer",
            "div.deepwiki-nav",
            "div.navigation",
            "div.table-of-contents",
            "div.toc",
            "div.deepwiki-header",
            "div.deepwiki-footer",
            "div.api-info",
            "div.version-info",
            "div.edit-options",
            "div.comments",
            "div.deepwiki-comments"
        ]
        
        # Title selectors in priority order
        self._title_selectors = [
            "h1.deepwiki-title",
            "h1.wiki-title",
            "h1.article-title",
            "div.deepwiki-header h1",
            "div.page-header h1",
            "h1.document-title",
            "h1:first-of-type",
            "h1",
            "h2.deepwiki-title",
            "h2:first-of-type",
            "title"
        ]
        
        # Patterns to identify API reference sections (often formatted differently)
        self._api_patterns = [
            r'API Reference',
            r'API Documentation',
            r'Method Reference',
            r'Function Reference',
            r'Class Reference'
        ]
    
    def get_priority_selectors(self) -> List[str]:
        """
        Return the predefined list of content selectors for DeepWiki.
        
        Returns:
            List of CSS selectors in priority order.
        """
        return self._content_selectors

    async def extract(self, html: str, url: ParseResult, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract content from DeepWiki-formatted HTML.
        
        Args:
            html: HTML content to extract from
            url: Parsed URL object for the page
            context: Optional extraction context for additional hints
            
        Returns:
            Dictionary with extracted title, content, and metadata
        """
        if not html:
            logger.warning(f"Empty HTML received for {url.geturl()}")
            return {
                "title": self._extract_title_from_url(url),
                "content": "",
                "metadata": {"extraction_successful": False}
            }
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract the title
        title = self._extract_title(soup, url)
        logger.debug(f"Extracted title: {title}")
        
        # Extract the content
        content_element, method = self._extract_content_element(soup)
        
        if not content_element:
            logger.warning(f"Could not find content element for {url.geturl()}")
            return {
                "title": title,
                "content": "",
                "metadata": {"extraction_successful": False, "extraction_method": "none"}
            }
        
        # Clean up content before returning
        cleaned_content = self._clean_content(content_element)
        
        # Extract code blocks and API references with special formatting
        code_blocks = self._extract_code_blocks(content_element)
        api_sections = self._identify_api_sections(content_element)
        
        # Return structured content
        return {
            "title": title,
            "content": str(cleaned_content),
            "metadata": {
                "extraction_successful": True,
                "extraction_method": method,
                "has_code_blocks": len(code_blocks) > 0,
                "code_block_count": len(code_blocks),
                "has_api_sections": len(api_sections) > 0,
                "api_section_count": len(api_sections),
                "url": url.geturl()
            }
        }
    
    def _extract_title(self, soup: BeautifulSoup, url: ParseResult) -> str:
        """
        Extract the title of the page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: ParseResult object of the URL
            
        Returns:
            Extracted title or fallback from URL
        """
        # Try DeepWiki-specific title selectors
        for selector in self._title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                return title_element.get_text(strip=True)
        
        # Fallback to <title> tag with cleanup
        if soup.title:
            title_text = soup.title.get_text(strip=True)
            
            # Remove common DeepWiki title suffixes
            title_text = re.sub(r'\s*[-|]\s*DeepWiki\s*$', '', title_text)
            title_text = re.sub(r'\s*[-|]\s*Documentation\s*$', '', title_text)
            
            return title_text
        
        # Last resort: extract from URL
        return self._extract_title_from_url(url)
    
    def _extract_title_from_url(self, url: ParseResult) -> str:
        """
        Extract a title from the URL as a last resort.
        
        Args:
            url: ParseResult object of the URL
            
        Returns:
            Title extracted from the URL path
        """
        path = url.path.rstrip('/')
        if not path:
            return url.netloc.split('.')[0].capitalize()
        
        # Get the last path component
        last_path = path.split('/')[-1]
        
        # Replace hyphens, underscores with spaces and capitalize
        title = last_path.replace('-', ' ').replace('_', ' ')
        
        # Capitalize words
        return ' '.join(word.capitalize() for word in title.split())
    
    def _extract_content_element(self, soup: BeautifulSoup) -> tuple[Optional[Tag], str]:
        """
        Extract the main content element using DeepWiki-specific selectors.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Tuple of (content element or None, extraction method used)
        """
        # Try each selector in priority order
        for selector in self._content_selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 100:
                # Remove excluded elements
                self._remove_excluded_elements(content)
                return content, f"selector:{selector}"
        
        # Heuristic approach for DeepWiki: look for the largest content div
        # that's not clearly a navigation element
        content_candidates = []
        
        for div in soup.find_all('div', class_=True):
            # Skip elements that match exclude selectors
            if any(div.select_one(sel) for sel in self._exclude_selectors):
                continue
                
            # Skip elements that have a small amount of text
            text_length = len(div.get_text(strip=True))
            if text_length < 200:
                continue
                
            # Skip elements that have many links (likely navigation)
            link_count = len(div.find_all('a'))
            if link_count > 15 and link_count > text_length / 100:
                continue
                
            # Compute content density score: text length / element count
            element_count = len(div.find_all())
            if element_count == 0:
                continue
                
            density_score = text_length / element_count
            
            # Add to candidates
            content_candidates.append((div, text_length, density_score))
        
        # Sort by text length and density score (weighted)
        if content_candidates:
            # Sort by combined score (80% text length, 20% density)
            content_candidates.sort(key=lambda x: (0.8 * x[1]) + (0.2 * x[2] * 10), reverse=True)
            best_candidate = content_candidates[0][0]
            self._remove_excluded_elements(best_candidate)
            return best_candidate, "heuristic:content_size"
            
        # Last resort: just use the body
        body = soup.find('body')
        if body:
            # Remove excluded elements
            self._remove_excluded_elements(body)
            return body, "fallback:body"
            
        return None, "none"
    
    def _remove_excluded_elements(self, content: Tag) -> None:
        """
        Remove navigation and other non-content elements from the extracted content.
        
        Args:
            content: BeautifulSoup Tag to clean up
        """
        for selector in self._exclude_selectors:
            for element in content.select(selector):
                element.decompose()
        
        # Remove DeepWiki comments markers
        for comment in content.find_all(string=lambda text: isinstance(text, NavigableString) and '<!--' in text):
            comment.extract()
        
        # Remove DeepWiki specific edit links
        for edit_link in content.select('a.deepwiki-edit, a.wiki-edit, a.edit-page, a.edit-link'):
            edit_link.decompose()
    
    def _clean_content(self, content: Tag) -> Tag:
        """
        Clean up the content for better extraction results.
        
        Args:
            content: BeautifulSoup Tag containing the content
            
        Returns:
            Cleaned content Tag
        """
        # Remove script and style elements
        for element in content.find_all(['script', 'style', 'iframe']):
            element.decompose()
        
        # Remove DeepWiki-specific navigation controls
        for nav_class in ['deepwiki-pages', 'deepwiki-nav', 'page-operations', 'toc-wrapper']:
            for element in content.find_all(class_=nav_class):
                element.decompose()
        
        # Remove "Edit on GitHub" links and similar
        for link in content.find_all('a', href=True):
            href = link.get('href', '')
            if any(x in href for x in ['edit', 'github.com', 'gitlab.com']):
                if len(link.get_text(strip=True)) < 30:  # Don't remove long text links
                    link.decompose()
        
        # Process DeepWiki div containers with special formatting
        for div in content.find_all('div', class_=True):
            classes = div.get('class', [])
            class_str = ' '.join(classes)
            
            # Handle note/warning/info boxes common in DeepWiki
            if any(x in class_str for x in ['note', 'warning', 'info', 'alert', 'admonition']):
                # Add a prefix to make these sections stand out
                if not div.find('strong') and not div.find('b'):
                    prefix_type = next((x for x in ['note', 'warning', 'info', 'alert'] if x in class_str), 'Note')
                    prefix = soup.new_tag('strong')
                    prefix.string = f"{prefix_type.capitalize()}: "
                    div.insert(0, prefix)
        
        return content
    
    def _extract_code_blocks(self, content: Tag) -> List[Dict[str, Any]]:
        """
        Extract and process code blocks.
        
        Args:
            content: BeautifulSoup Tag containing the content
            
        Returns:
            List of dictionaries with code block info
        """
        code_blocks = []
        
        # Extract <pre><code> blocks
        for pre in content.find_all('pre'):
            code = pre.find('code')
            if code:
                language = None
                
                # Try to identify language from class
                if code.get('class'):
                    for cls in code.get('class'):
                        if cls.startswith(('language-', 'lang-')):
                            language = cls.split('-', 1)[1]
                            break
                
                code_text = code.get_text()
                code_blocks.append({
                    'language': language,
                    'code': code_text,
                    'type': 'pre_code'
                })
        
        # Handle DeepWiki-specific code blocks
        for div in content.find_all('div', class_=True):
            classes = div.get('class', [])
            if any(cls in classes for cls in ['code-block', 'highlight', 'deepwiki-code', 'source-code']):
                # Try to find language hint
                language = None
                
                # Check for language in data attribute
                if div.get('data-language'):
                    language = div.get('data-language')
                elif div.get('data-lang'):
                    language = div.get('data-lang')
                    
                # Check for language in class
                if not language:
                    for cls in classes:
                        if cls.startswith(('language-', 'lang-', 'highlight-')):
                            language = cls.split('-', 1)[1]
                            break
                
                code_text = div.get_text()
                code_blocks.append({
                    'language': language,
                    'code': code_text,
                    'type': 'div_code'
                })
        
        return code_blocks
    
    def _identify_api_sections(self, content: Tag) -> List[Dict[str, Any]]:
        """
        Identify API reference sections for special processing.
        
        Args:
            content: BeautifulSoup Tag containing the content
            
        Returns:
            List of dictionaries with API section info
        """
        api_sections = []
        
        # Look for API reference headings
        api_pattern = re.compile('|'.join(self._api_patterns), re.IGNORECASE)
        
        for heading in content.find_all(['h1', 'h2', 'h3']):
            heading_text = heading.get_text(strip=True)
            
            if api_pattern.search(heading_text):
                # Found an API reference section
                # Get all content until the next heading of same or higher level
                api_content = []
                current = heading.next_sibling
                
                while current:
                    if current.name and current.name[0] == 'h' and int(current.name[1]) <= int(heading.name[1]):
                        break
                    api_content.append(current)
                    current = current.next_sibling
                
                # Create a container tag for the API section
                api_section = BeautifulSoup().new_tag('div')
                for element in api_content:
                    if element.name:
                        api_section.append(element.extract())
                
                # Add to the list
                api_sections.append({
                    'heading': heading_text,
                    'content': str(api_section),
                    'level': int(heading.name[1])
                })
        
        return api_sections
