"""
Generic link extractor implementation.

This module implements a generic link extraction strategy that works with most
documentation websites by using navigation element detection and prioritization.
"""

import re
from typing import Dict, List, Optional, Any, Set
from urllib.parse import ParseResult, urljoin, urlparse
from bs4 import BeautifulSoup

from src.extractors.interfaces import ILinkExtractor
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class GenericLinkExtractor(ILinkExtractor):
    """
    Generic link extractor implementation.
    
    This class implements the ILinkExtractor interface for general documentation sites.
    It focuses on identifying and extracting navigation links, with a priority system
    to ensure the most relevant links are crawled first.
    """
    
    def __init__(self):
        """Initialize the generic link extractor."""
        # Define navigation element selectors in priority order
        self._navigation_selectors = [
            "nav",                     # HTML5 semantic element for navigation
            ".sidebar",                # Common class for documentation sidebar
            ".navigation",             # Common class for navigation
            ".toc",                    # Table of contents
            "aside",                   # HTML5 semantic element for sidebar
            "#sidebar",                # Common ID for sidebar
            "#menu",                   # Common ID for menu
            "#toc",                    # Common ID for table of contents
            ".doc-menu",               # Common class for documentation menu
            ".doc-nav",                # Common class for documentation navigation
            ".menu",                   # Common class for menu
            "header nav",              # Navigation in header
            "footer nav",              # Navigation in footer
            "[role='navigation']"      # ARIA role for navigation
        ]
        
        # Define additional link containers that might contain relevant documentation links
        self._content_link_selectors = [
            "article a",               # Links within main content
            "main a",                  # Links within main content
            ".content a",              # Links within content area
            ".documentation a",        # Links within documentation area
            ".main-content a"          # Links within main content area
        ]
        
        # Define patterns for recognizing pagination links
        self._pagination_patterns = {
            "next": [
                "next", "next page", "continue", "→", ">>",
                "próximo", "siguiente", "weiter"  # Multi-language support
            ],
            "previous": [
                "previous", "prev", "back", "←", "<<",
                "anterior", "vorherige"  # Multi-language support
            ]
        }
        
        # Define patterns for likely documentation paths
        self._doc_path_patterns = [
            r"/docs?/",
            r"/documentation/",
            r"/guide/",
            r"/tutorial/",
            r"/reference/",
            r"/manual/",
            r"/learn/",
            r"/api/",
            r"/wiki/"
        ]
        
        # Terms that indicate a link is likely not documentation
        self._negative_terms = [
            "login", "sign in", "register", "download", "buy",
            "forum", "blog", "contact", "privacy", "terms", "careers"
        ]
    
    async def extract(self, html: str, base_url: ParseResult, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract documentation links from the provided HTML.
        
        Args:
            html: Raw HTML content to extract links from
            base_url: Parsed URL object for the current page
            context: Optional contextual information that may assist in extraction
            
        Returns:
            List of dictionaries, each containing:
                - 'url': Full URL of the link
                - 'text': Link text
                - 'type': Type of link (navigation, content, pagination)
                - 'priority': Suggested crawl priority (lower is higher priority)
                - 'depth': Estimated depth in the documentation hierarchy
        """
        if not html:
            logger.error("Empty HTML provided for link extraction")
            return []
            
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create a set to avoid duplicate links
        unique_links: Set[str] = set()
        
        # Results will contain all extracted links
        results = []
        
        # Extract navigation links (highest priority)
        nav_links = self._extract_navigation_links(soup, base_url, unique_links)
        results.extend(nav_links)
        
        # Extract content links (medium priority)
        content_links = self._extract_content_links(soup, base_url, unique_links)
        results.extend(content_links)
        
        # Extract pagination links (high priority for sequential docs)
        pagination_links = self._extract_pagination_links(soup, base_url, unique_links)
        results.extend(pagination_links)
        
        # Log extraction results
        logger.debug(f"Extracted {len(results)} unique links from {base_url.geturl()}: "
                    f"{len(nav_links)} navigation links, "
                    f"{len(content_links)} content links, "
                    f"{len(pagination_links)} pagination links")
        
        return results
    
    def get_navigation_selectors(self) -> List[str]:
        """
        Get the ordered list of CSS selectors to try for navigation extraction.
        
        Returns:
            List of CSS selectors in priority order
        """
        return self._navigation_selectors
    
    def should_follow_link(self, link_url: ParseResult, current_url: ParseResult, link_text: str) -> bool:
        """
        Determine if a link should be followed during crawling.
        
        Args:
            link_url: Parsed URL of the link
            current_url: Parsed URL of the current page
            link_text: Visible text of the link
            
        Returns:
            Boolean indicating if the link should be followed
        """
        # Don't follow links to different domains (stay on the same site)
        if link_url.netloc != current_url.netloc:
            return False
        
        # Skip common non-documentation file types
        if re.search(r"\.(zip|pdf|png|jpg|jpeg|gif|svg|webp|mp4|webm|mp3|ogg|wav|css|js)$", link_url.path, re.IGNORECASE):
            return False
            
        # Skip links with negative terms (login, download, etc.)
        link_text_lower = link_text.lower()
        if any(term in link_text_lower for term in self._negative_terms):
            return False
            
        # Skip anchor links that point to the same page
        if not link_url.path and link_url.fragment:
            return False
            
        # Skip links with query parameters to avoid potential loops
        # except for common doc versioning parameters
        if link_url.query and not re.search(r"(version|v|doc_version|release)=", link_url.query):
            return False
        
        # Prefer to follow links that look like documentation paths
        if any(re.search(pattern, link_url.path, re.IGNORECASE) for pattern in self._doc_path_patterns):
            return True
            
        # By default, follow links on the same domain
        return True
    
    def _extract_navigation_links(self, soup: BeautifulSoup, base_url: ParseResult, unique_links: Set[str]) -> List[Dict[str, Any]]:
        """
        Extract links from navigation elements.
        
        Args:
            soup: BeautifulSoup object
            base_url: Parsed URL object for the current page
            unique_links: Set of already processed URLs to avoid duplicates
            
        Returns:
            List of extracted navigation links
        """
        results = []
        base_url_string = base_url.geturl()
        
        # Extract links from navigation elements in priority order
        for selector in self._navigation_selectors:
            nav_elements = soup.select(selector)
            
            # Process links from each navigation element
            for i, nav in enumerate(nav_elements):
                # Get all links in this navigation element
                links = nav.find_all("a", href=True)
                
                # Calculate a base priority value based on the selector priority
                # Lower values = higher priority, earlier in navigation_selectors = higher priority
                base_priority = self._navigation_selectors.index(selector) + 1
                
                # Adjust priority slightly for multiple navigation elements of the same type
                if len(nav_elements) > 1:
                    base_priority += 0.1 * i
                
                # Process each link in this navigation element
                for link in links:
                    href = link.get("href", "").strip()
                    
                    # Skip empty or javascript links
                    if not href or href.startswith("javascript:") or href == "#":
                        continue
                    
                    # Create absolute URL
                    full_url = urljoin(base_url_string, href)
                    
                    # Skip if we've already seen this URL
                    if full_url in unique_links:
                        continue
                    
                    # Add to unique links set
                    unique_links.add(full_url)
                    
                    # Parse the URL
                    parsed_url = urlparse(full_url)
                    
                    # Only include if it should be followed
                    if self.should_follow_link(parsed_url, base_url, link.get_text(strip=True)):
                        # Calculate depth based on path segments
                        path = parsed_url.path.strip("/")
                        depth = len(path.split("/")) if path else 0
                        
                        # Extract link text
                        link_text = link.get_text(strip=True)
                        
                        # Create link entry
                        results.append({
                            "url": full_url,
                            "text": link_text,
                            "type": "navigation",
                            "priority": base_priority,
                            "depth": depth
                        })
        
        return results
    
    def _extract_content_links(self, soup: BeautifulSoup, base_url: ParseResult, unique_links: Set[str]) -> List[Dict[str, Any]]:
        """
        Extract links from main content areas.
        
        Args:
            soup: BeautifulSoup object
            base_url: Parsed URL object for the current page
            unique_links: Set of already processed URLs to avoid duplicates
            
        Returns:
            List of extracted content links
        """
        results = []
        base_url_string = base_url.geturl()
        
        # Extract links from content areas
        for selector in self._content_link_selectors:
            links = soup.select(selector)
            
            # Set a base priority for content links (higher than navigation)
            base_priority = 10 + self._content_link_selectors.index(selector)
            
            # Process each link
            for link in links:
                href = link.get("href", "").strip()
                
                # Skip empty or javascript links
                if not href or href.startswith("javascript:") or href == "#":
                    continue
                
                # Create absolute URL
                full_url = urljoin(base_url_string, href)
                
                # Skip if we've already seen this URL
                if full_url in unique_links:
                    continue
                
                # Add to unique links set
                unique_links.add(full_url)
                
                # Parse the URL
                parsed_url = urlparse(full_url)
                
                # Only include if it should be followed
                if self.should_follow_link(parsed_url, base_url, link.get_text(strip=True)):
                    # Calculate depth based on path segments
                    path = parsed_url.path.strip("/")
                    depth = len(path.split("/")) if path else 0
                    
                    # Extract link text
                    link_text = link.get_text(strip=True)
                    
                    # Create link entry
                    results.append({
                        "url": full_url,
                        "text": link_text,
                        "type": "content",
                        "priority": base_priority,
                        "depth": depth
                    })
        
        return results
    
    def _extract_pagination_links(self, soup: BeautifulSoup, base_url: ParseResult, unique_links: Set[str]) -> List[Dict[str, Any]]:
        """
        Extract pagination links (Next/Previous).
        
        Args:
            soup: BeautifulSoup object
            base_url: Parsed URL object for the current page
            unique_links: Set of already processed URLs to avoid duplicates
            
        Returns:
            List of extracted pagination links
        """
        results = []
        base_url_string = base_url.geturl()
        
        # Find all links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            
            # Skip empty or javascript links
            if not href or href.startswith("javascript:") or href == "#":
                continue
            
            # Create absolute URL
            full_url = urljoin(base_url_string, href)
            
            # Skip if we've already seen this URL
            if full_url in unique_links:
                continue
            
            # Get link text and any title attribute
            link_text = link.get_text(strip=True).lower()
            link_title = link.get("title", "").lower()
            link_class = " ".join(link.get("class", [])).lower()
            link_rel = link.get("rel", [])
            if isinstance(link_rel, str):
                link_rel = [link_rel]
            link_rel = [r.lower() for r in link_rel]
            
            # Check if it's a pagination link
            pagination_type = None
            
            # Check for "next" link
            if (
                any(pattern in link_text for pattern in self._pagination_patterns["next"]) or
                any(pattern in link_title for pattern in self._pagination_patterns["next"]) or
                "next" in link_class or
                "next" in link_rel
            ):
                pagination_type = "next"
                
            # Check for "previous" link
            elif (
                any(pattern in link_text for pattern in self._pagination_patterns["previous"]) or
                any(pattern in link_title for pattern in self._pagination_patterns["previous"]) or
                "prev" in link_class or "previous" in link_class or
                "prev" in link_rel or "previous" in link_rel
            ):
                pagination_type = "previous"
            
            # If it's a pagination link
            if pagination_type:
                # Add to unique links set
                unique_links.add(full_url)
                
                # Parse the URL
                parsed_url = urlparse(full_url)
                
                # Only include if it should be followed
                if self.should_follow_link(parsed_url, base_url, link_text):
                    # Set priority (next links are higher priority than previous)
                    priority = 5 if pagination_type == "next" else 8
                    
                    # Calculate depth based on path segments
                    path = parsed_url.path.strip("/")
                    depth = len(path.split("/")) if path else 0
                    
                    # Create link entry
                    results.append({
                        "url": full_url,
                        "text": link.get_text(strip=True),
                        "type": f"pagination_{pagination_type}",
                        "priority": priority,
                        "depth": depth
                    })
        
        return results
