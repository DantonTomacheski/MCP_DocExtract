"""
DeepWiki-specific link extraction implementation.

This module contains a link extractor specifically optimized for DeepWiki documentation sites,
focusing on their navigation patterns and structures.
"""

import re
from typing import Dict, List, Optional, Any, Union, Set
from urllib.parse import ParseResult, urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from src.extractors.interfaces import ILinkExtractor
from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class DeepWikiLinkExtractor(ILinkExtractor):
    """
    DeepWiki-specific link extractor.
    
    This extractor is specialized for extracting navigation links from DeepWiki-based documentation
    sites, which have specific navigation structures and link patterns.
    """
    
    def __init__(self):
        """Initialize the DeepWiki link extractor."""
        # DeepWiki navigation selectors in priority order
        self._nav_selectors = [
            # DeepWiki standard navigation containers
            "nav.deepwiki-nav",
            "div.deepwiki-navigation",
            "div.deepwiki-sidebar",
            "div.wiki-sidebar",
            "div.documentation-sidebar",
            "aside.sidebar",
            "nav.sidebar",
            "div.toc-sidebar",
            
            # Left/right sidebar patterns
            "div.left-sidebar",
            "div.right-sidebar",
            "div.sidebar-wrapper",
            
            # Table of contents containers
            "div.table-of-contents",
            "div.toc",
            "nav.toc",
            "div.deepwiki-toc",
            
            # Menu containers common in DeepWiki
            "ul.deepwiki-menu",
            "ul.wiki-menu",
            "ul.doc-menu",
            "div.menu-container",
            
            # Generic navigation fallbacks
            "nav",
            "div[role='navigation']",
            "ul.navigation"
        ]
        
        # DeepWiki in-content link section selectors
        self._in_content_link_selectors = [
            "div.see-also",
            "div.related-pages",
            "div.related-topics",
            "div.deepwiki-related",
            "section.related-links",
            "div.next-prev-links",
            "div.page-navigation",
            "div.article-footer"
        ]
        
        # Patterns to identify navigation links vs. external links
        self._doc_link_patterns = [
            r'\/docs\/',
            r'\/documentation\/',
            r'\/guide\/',
            r'\/tutorial\/',
            r'\/manual\/',
            r'\/reference\/',
            r'\/wiki\/',
            r'\.md$',
            r'\.html$'
        ]
        
        # Patterns for links to exclude
        self._exclude_link_patterns = [
            r'\/edit\/',
            r'\/raw\/',
            r'\/history\/',
            r'\/blame\/',
            r'\/commits\/',
            r'\/issues\/',
            r'\/pull\/',
            r'\/compare\/',
            r'\/settings\/',
            r'\/export\/',
            r'\/search\?',
            r'\/login',
            r'\/logout',
            r'\/register'
        ]
    
    def get_navigation_selectors(self) -> List[str]:
        """
        Return the predefined list of navigation selectors for DeepWiki.
        
        Returns:
            List of CSS selectors for navigation elements in priority order.
        """
        return self._nav_selectors

    def should_follow_link(self, link_url: ParseResult, current_url: ParseResult, link_text: str) -> bool:
        """
        Determine if a link should be followed based on DeepWiki patterns.

        Args:
            link_url: Parsed URL of the link.
            current_url: Parsed URL of the current page.
            link_text: Visible text of the link.

        Returns:
            Boolean indicating if the link should be followed.
        """
        # Don't follow excluded links (edit, history, etc.)
        if self._is_excluded_link(link_url.geturl()):
            logger.debug(f"Excluding link based on exclude pattern: {link_url.geturl()}")
            return False

        # Only follow links within the same domain (or subdomain)
        if link_url.netloc and link_url.netloc != current_url.netloc:
            # Allow specific known documentation subdomains if needed in future
            logger.debug(f"Excluding link to different domain: {link_url.netloc} (from {current_url.netloc})")
            return False

        # Don't follow fragment identifiers on the same page
        if not link_url.path and link_url.fragment:
             # Allow if the path is different *and* there's a fragment
             if link_url.path == current_url.path:
                 logger.debug(f"Excluding fragment-only link on same page: #{link_url.fragment}")
                 return False

        # Check if it looks like a documentation link based on path/text
        # This uses the existing helper which checks for common doc patterns
        # but might need refinement based on actual DeepWiki structure.
        looks_like_doc = self._looks_like_doc_link(link_url.geturl(), link_text, current_url)
        if not looks_like_doc:
            logger.debug(f"Excluding link that doesn't look like doc: {link_url.geturl()} (text: '{link_text}')")
            return False
            
        # If it passes all checks, follow it
        logger.debug(f"Following link: {link_url.geturl()}")
        return True

    async def extract(self, html: str, base_url: ParseResult, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract links from DeepWiki-formatted HTML.
        
        Args:
            html: HTML content to extract links from
            base_url: Parsed URL object for resolving relative links
            context: Optional extraction context for additional hints
            
        Returns:
            List of dictionaries with link information
        """
        if not html:
            logger.warning(f"Empty HTML received for {base_url.geturl()}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract navigation links (primary approach for DeepWiki)
        nav_links = self._extract_navigation_links(soup, base_url)
        logger.debug(f"Extracted {len(nav_links)} navigation links from {base_url.geturl()}")
        
        # Extract in-content links (secondary, but important for DeepWiki)
        content_links = self._extract_content_links(soup, base_url)
        logger.debug(f"Extracted {len(content_links)} content links from {base_url.geturl()}")
        
        # Extract related links sections (tertiary, but valuable in DeepWiki)
        related_links = self._extract_related_links(soup, base_url)
        logger.debug(f"Extracted {len(related_links)} related links from {base_url.geturl()}")
        
        # Combine all links and remove duplicates while preserving metadata
        all_links = self._merge_and_deduplicate_links(nav_links, content_links, related_links)
        
        # Filter out non-documentation links
        doc_links = self._filter_documentation_links(all_links, base_url)
        
        # Sort links by priority (navigation links first, then in-content)
        doc_links.sort(key=lambda x: (
            -x.get('priority', 0),  # Higher priority first
            x.get('source_type', '') != 'navigation',  # Navigation links first
            x.get('depth', 0)  # Then by depth (lower depth first)
        ))
        
        return doc_links
    
    def _extract_navigation_links(self, soup: BeautifulSoup, base_url: ParseResult) -> List[Dict[str, Any]]:
        """
        Extract links from navigation elements using DeepWiki-specific selectors.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: ParseResult object for resolving relative links
            
        Returns:
            List of dictionaries with navigation link information
        """
        nav_links = []
        
        # Track which links we've seen to avoid duplicates
        seen_urls = set()
        
        # Try each navigation selector in priority order
        for selector in self._nav_selectors:
            nav_elements = soup.select(selector)
            
            for nav in nav_elements:
                # DeepWiki often uses hierarchical navigation with nested lists
                # Extract all links and determine their depth in the navigation
                for link in nav.find_all('a', href=True):
                    href = link.get('href')
                    
                    # Skip empty and excluded links
                    if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                        continue
                    
                    # Skip links that match exclude patterns
                    if self._is_excluded_link(href):
                        continue
                    
                    # Resolve relative URLs
                    abs_url = urljoin(base_url.geturl(), href)
                    
                    # Skip if we've seen this URL
                    if abs_url in seen_urls:
                        continue
                    
                    seen_urls.add(abs_url)
                    
                    # Get the link text
                    link_text = link.get_text(strip=True)
                    
                    # Determine depth in the navigation structure
                    depth = self._determine_link_depth(link)
                    
                    # Determine if this is a current/active link
                    is_active = self._is_active_link(link)
                    
                    # Special handling for headings in DeepWiki navigation
                    is_heading = False
                    parent = link.parent
                    if parent and parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong']:
                        is_heading = True
                    
                    # Add to our list
                    nav_links.append({
                        'url': abs_url,
                        'text': link_text,
                        'source_type': 'navigation',
                        'source_selector': selector,
                        'depth': depth,
                        'is_active': is_active,
                        'is_heading': is_heading,
                        'priority': self._calculate_link_priority(link, depth, is_active, is_heading)
                    })
        
        return nav_links
    
    def _extract_content_links(self, soup: BeautifulSoup, base_url: ParseResult) -> List[Dict[str, Any]]:
        """
        Extract links from main content area.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: ParseResult object for resolving relative links
            
        Returns:
            List of dictionaries with content link information
        """
        content_links = []
        seen_urls = set()
        
        # First try to locate main content area (using DeepWiki content selectors)
        content_selectors = [
            "div.documentation-content",
            "div.wiki-content", 
            "div.deepwiki-content",
            "div.deepwiki-article",
            "main.content-wrapper",
            "article",
            "main",
            "div.content"
        ]
        
        content_area = None
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Pick the one with the most text
                content_area = max(elements, key=lambda el: len(el.get_text(strip=True)))
                break
        
        # If no content area found, use body as fallback
        if not content_area:
            content_area = soup.find('body')
            if not content_area:
                return []
        
        # Find all content links
        for link in content_area.find_all('a', href=True):
            href = link.get('href')
            
            # Skip empty and excluded links
            if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            
            # Skip links that match exclude patterns
            if self._is_excluded_link(href):
                continue
            
            # Resolve relative URLs
            abs_url = urljoin(base_url.geturl(), href)
            
            # Skip if we've seen this URL
            if abs_url in seen_urls:
                continue
            
            seen_urls.add(abs_url)
            
            # Get the link text
            link_text = link.get_text(strip=True)
            
            # Determine if this link is in a paragraph, heading, or list
            container_type = self._determine_link_container(link)
            
            # Skip links that are likely not documentation links
            if not self._looks_like_doc_link(href, link_text, base_url):
                continue
            
            # Add to our list
            content_links.append({
                'url': abs_url,
                'text': link_text,
                'source_type': 'content',
                'container_type': container_type,
                'depth': 0,  # Content links don't have a depth
                'priority': 5 if container_type == 'heading' else 3,  # Prioritize heading links
                'is_heading': container_type == 'heading'
            })
        
        return content_links
    
    def _extract_related_links(self, soup: BeautifulSoup, base_url: ParseResult) -> List[Dict[str, Any]]:
        """
        Extract links from related content sections (see also, related topics, etc.).
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: ParseResult object for resolving relative links
            
        Returns:
            List of dictionaries with related link information
        """
        related_links = []
        seen_urls = set()
        
        # Check each related section selector
        for selector in self._in_content_link_selectors:
            related_sections = soup.select(selector)
            
            for section in related_sections:
                section_title = ""
                
                # Try to find the section title
                heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading:
                    section_title = heading.get_text(strip=True)
                elif section.has_attr('aria-label'):
                    section_title = section['aria-label']
                elif section.has_attr('title'):
                    section_title = section['title']
                
                # Find all links in this section
                for link in section.find_all('a', href=True):
                    href = link.get('href')
                    
                    # Skip empty and excluded links
                    if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                        continue
                    
                    # Skip links that match exclude patterns
                    if self._is_excluded_link(href):
                        continue
                    
                    # Resolve relative URLs
                    abs_url = urljoin(base_url.geturl(), href)
                    
                    # Skip if we've seen this URL
                    if abs_url in seen_urls:
                        continue
                    
                    seen_urls.add(abs_url)
                    
                    # Get the link text
                    link_text = link.get_text(strip=True)
                    
                    # Add to our list with high priority for related links
                    related_links.append({
                        'url': abs_url,
                        'text': link_text,
                        'source_type': 'related',
                        'section_title': section_title,
                        'source_selector': selector,
                        'priority': 7  # Related links are typically very relevant
                    })
        
        return related_links
    
    def _merge_and_deduplicate_links(self, *link_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge multiple link lists and remove duplicates while preserving metadata.
        
        Args:
            *link_groups: Variable number of link lists to merge
            
        Returns:
            Deduplicated list of links
        """
        url_to_link_map = {}
        
        # Process all link groups
        for links in link_groups:
            for link in links:
                url = link['url']
                
                if url in url_to_link_map:
                    # If we've seen this URL before, merge and keep the higher priority
                    existing = url_to_link_map[url]
                    
                    # Keep the entry with higher priority
                    if link.get('priority', 0) > existing.get('priority', 0):
                        # Keep most metadata from the new link, but merge source_types
                        link['source_type'] = f"{link['source_type']},{existing['source_type']}"
                        url_to_link_map[url] = link
                else:
                    # First time seeing this URL
                    url_to_link_map[url] = link
        
        return list(url_to_link_map.values())
    
    def _filter_documentation_links(self, links: List[Dict[str, Any]], base_url: ParseResult) -> List[Dict[str, Any]]:
        """
        Filter links to only include those that are likely documentation pages.
        
        Args:
            links: List of link dictionaries
            base_url: ParseResult object of the current page
            
        Returns:
            Filtered list of documentation links
        """
        doc_links = []
        base_domain = base_url.netloc
        
        for link in links:
            url = link['url']
            parsed_url = urlparse(url)
            
            # Always include links to the same domain
            if parsed_url.netloc == base_domain:
                # But exclude non-documentation paths
                if not self._is_excluded_link(parsed_url.path):
                    doc_links.append(link)
                    continue
            
            # For external links, only include those that look like documentation
            if self._looks_like_doc_link(url, link['text'], base_url):
                # Mark as external
                link['is_external'] = True
                doc_links.append(link)
        
        return doc_links
    
    def _determine_link_depth(self, link: Tag) -> int:
        """
        Determine the depth of a link in the navigation hierarchy.
        
        Args:
            link: BeautifulSoup Tag for the link
            
        Returns:
            Depth level (0-based)
        """
        depth = 0
        parent = link.parent
        
        # Navigate up through nested lists to determine depth
        while parent:
            if parent.name == 'ul' or parent.name == 'ol':
                depth += 1
                
                # Check if this list is nested inside a list item
                if parent.parent and parent.parent.name == 'li':
                    parent = parent.parent.parent
                else:
                    parent = parent.parent
            else:
                parent = parent.parent
                
        return depth - 1 if depth > 0 else 0
    
    def _is_active_link(self, link: Tag) -> bool:
        """
        Determine if this link is marked as the current/active page.
        
        Args:
            link: BeautifulSoup Tag for the link
            
        Returns:
            Boolean indicating if this is an active link
        """
        # Check for common active/current class markers
        classes = link.get('class', [])
        if any(c in classes for c in ['active', 'current', 'selected', 'deepwiki-active']):
            return True
        
        # Check parent list item for active marker
        parent_li = link.find_parent('li')
        if parent_li and parent_li.get('class'):
            parent_classes = parent_li.get('class', [])
            if any(c in parent_classes for c in ['active', 'current', 'selected', 'deepwiki-active']):
                return True
        
        # Check aria-current attribute
        if link.get('aria-current'):
            return True
            
        return False
    
    def _determine_link_container(self, link: Tag) -> str:
        """
        Determine what kind of element contains this link.
        
        Args:
            link: BeautifulSoup Tag for the link
            
        Returns:
            Container type: 'heading', 'paragraph', 'list', or 'other'
        """
        # Check if link is in a heading
        if link.find_parent(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            return 'heading'
        
        # Check if link is in a paragraph
        if link.find_parent('p'):
            return 'paragraph'
        
        # Check if link is in a list
        if link.find_parent(['ul', 'ol']):
            return 'list'
            
        return 'other'
    
    def _is_excluded_link(self, href: str) -> bool:
        """
        Determine if a link should be excluded based on patterns.
        
        Args:
            href: Link URL to check
            
        Returns:
            Boolean indicating if the link should be excluded
        """
        # Check against exclude patterns
        for pattern in self._exclude_link_patterns:
            if re.search(pattern, href):
                return True
                
        return False
    
    def _looks_like_doc_link(self, href: str, text: str, base_url: ParseResult) -> bool:
        """
        Determine if a link looks like it leads to documentation.
        
        Args:
            href: Link URL
            text: Link text
            base_url: Base URL for context
            
        Returns:
            Boolean indicating if this looks like a documentation link
        """
        # Internal links on the same domain are likely documentation
        if not urlparse(href).netloc or urlparse(href).netloc == base_url.netloc:
            # But exclude anchors and non-documentation paths
            if href.startswith('#') or self._is_excluded_link(href):
                return False
            return True
        
        # External links need more checks
        # Check if the URL matches documentation patterns
        for pattern in self._doc_link_patterns:
            if re.search(pattern, href):
                return True
        
        # Check if the link text suggests it's documentation
        doc_text_patterns = [
            r'doc(s|umentation)?',
            r'guide',
            r'tutorial',
            r'manual',
            r'reference',
            r'api',
            r'how\s+to',
            r'learn',
            r'example'
        ]
        
        for pattern in doc_text_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Default to not a documentation link for external URLs
        return False
    
    def _calculate_link_priority(self, link: Tag, depth: int, is_active: bool, is_heading: bool) -> int:
        """
        Calculate a priority score for a link based on various factors.
        
        Args:
            link: BeautifulSoup Tag for the link
            depth: Depth in the navigation hierarchy
            is_active: Whether this is the active link
            is_heading: Whether this link is in/is a heading
            
        Returns:
            Priority score (higher is more important)
        """
        priority = 5  # Base priority
        
        # Navigation hierarchy factors
        if depth == 0:
            priority += 3  # Top-level navigation links are important
        elif depth == 1:
            priority += 2  # Second level is also quite important
        else:
            priority -= depth  # Deeper levels are less important
        
        # Active link gets a boost
        if is_active:
            priority += 3
            
        # Heading links get a boost
        if is_heading:
            priority += 2
            
        # Boost links with 'index' or 'overview' in them
        link_text = link.get_text(strip=True).lower()
        href = link.get('href', '').lower()
        
        if any(term in link_text or term in href for term in ['index', 'overview', 'introduction', 'getting started']):
            priority += 2
            
        # Penalize links that might be less relevant
        if any(term in link_text.lower() for term in ['deprecated', 'legacy', 'archive']):
            priority -= 3
            
        return priority
