"""
Interfaces for content and link extraction strategies.

This module defines the abstract base classes that all extraction strategies must implement,
following the Strategy pattern to allow for flexible and extensible extraction mechanisms.
"""

import abc
from typing import Dict, List, Optional, Any, Union
from urllib.parse import ParseResult


class IContentExtractor(abc.ABC):
    """
    Interface for content extraction strategies.
    
    Implementations of this interface are responsible for extracting the main content
    from a webpage, separating the actual documentation from navigation, headers, footers, etc.
    
    All content extractors must follow a multi-stage extraction process with fallbacks:
    1. Attempt precise extraction using content-specific selectors
    2. Fall back to more general selectors if specific extraction fails
    3. Apply content cleaning and normalization
    """
    
    @abc.abstractmethod
    async def extract(self, html: str, url: ParseResult, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract the main content from the provided HTML.
        
        Args:
            html: Raw HTML content to extract from
            url: Parsed URL object for the page being processed
            context: Optional contextual information that may assist in extraction
                    (e.g., framework detected, page hierarchy info)
        
        Returns:
            Dictionary containing:
                - 'title': Page title
                - 'content': Extracted main content
                - 'metadata': Additional metadata extracted
                - 'elements': Key structural elements identified
                - 'success': Boolean indicating if extraction was successful
                - 'extraction_method': String describing which method succeeded
        
        Raises:
            ExtractionError: If content extraction fails completely
        """
        pass
    
    @abc.abstractmethod
    def get_priority_selectors(self) -> List[str]:
        """
        Get the ordered list of CSS selectors to try for content extraction.
        
        Returns:
            List of CSS selectors in priority order
        """
        pass


class ILinkExtractor(abc.ABC):
    """
    Interface for link extraction strategies.
    
    Implementations of this interface are responsible for extracting navigation links
    from documentation pages, focusing on links that lead to other pages in the documentation.
    
    Link extractors should prioritize:
    1. Documentation navigation elements
    2. Table of contents links
    3. "Next/Previous" navigation
    4. Related topic links
    """
    
    @abc.abstractmethod
    async def extract(self, html: str, base_url: ParseResult, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract documentation links from the provided HTML.
        
        Args:
            html: Raw HTML content to extract links from
            base_url: Parsed URL object for the current page
            context: Optional contextual information that may assist in extraction
                    (e.g., framework detected, page hierarchy info)
        
        Returns:
            List of dictionaries, each containing:
                - 'url': Full URL of the link
                - 'text': Link text
                - 'type': Type of link (navigation, content, etc.)
                - 'priority': Suggested crawl priority
                - 'depth': Estimated depth in the documentation hierarchy
        
        Raises:
            ExtractionError: If link extraction fails completely
        """
        pass
    
    @abc.abstractmethod
    def get_navigation_selectors(self) -> List[str]:
        """
        Get the ordered list of CSS selectors to try for navigation extraction.
        
        Returns:
            List of CSS selectors in priority order
        """
        pass
    
    @abc.abstractmethod
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
        pass
