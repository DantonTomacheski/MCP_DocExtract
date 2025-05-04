"""
Sequential scraper service implementation.

This module implements a sequential (single-threaded) scraper service that
uses a breadth-first search (BFS) algorithm to crawl documentation websites.
"""

import os
import time
import asyncio
from collections import deque
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse, ParseResult
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup

from src.extractors.interfaces import IContentExtractor, ILinkExtractor
from src.utils.logging import get_logger

# Optional import for AI components
try:
    from src.ai.content_processor import AIContentProcessor
    from src.ai.link_filter import AILinkFilter
    AI_COMPONENTS_AVAILABLE = True
except ImportError:
    AI_COMPONENTS_AVAILABLE = False

# Get logger
logger = get_logger(__name__)


class SequentialScraperService:
    """
    Sequential scraper service for documentation websites.
    
    This class implements a single-threaded BFS algorithm to crawl documentation
    websites, extract content, and organize it for export.
    """
    """
    Sequential scraper service for documentation websites.
    
    This class implements a single-threaded BFS algorithm to crawl documentation
    websites, extract content, and organize it for export.
    """
    
    def __init__(
        self,
        content_extractor: IContentExtractor,
        link_extractor: ILinkExtractor,
        max_depth: int = 5,
        max_pages: int = 500,
        rate_limit: float = 0.5,  # seconds between requests
        ai_processor: Optional[Any] = None,  # AIContentProcessor
        ai_link_filter: Optional[Any] = None,  # AILinkFilter
        batch_size: int = 5  # Number of items to process in a batch
    ):
        """
        Initialize the sequential scraper service.
        
        Args:
            content_extractor: Strategy for extracting content
            link_extractor: Strategy for extracting links
            max_depth: Maximum depth of links to follow
            max_pages: Maximum number of pages to process
            rate_limit: Minimum time between requests in seconds
        """
        self.content_extractor = content_extractor
        self.link_extractor = link_extractor
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        self.ai_processor = ai_processor
        self.ai_link_filter = ai_link_filter
        self.batch_size = batch_size
        
        # Flag indicating whether AI capabilities are available and initialized
        self.use_ai = bool(ai_processor) and bool(ai_link_filter)
        
        # Initialize state tracking
        self.visited_urls: Set[str] = set()
        self.content_map: Dict[str, Dict[str, Any]] = {}
        self.url_queue: deque = deque()
        self.url_to_depth: Dict[str, int] = {}
        
        # Initialize statistics
        self.stats = {
            "urls_discovered": 0,
            "urls_processed": 0,
            "start_time": None,
            "end_time": None,
            "success": True,
            "error": None,
            "status": "initialized",
            "ai_processed": 0,
            "batches_processed": 0,
            "cache_hits": 0
        }
        
        # Initialize browser resources
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def scrape(self, start_url: str, operation_id: str = None) -> Dict[str, Any]:
        """
        Scrape a documentation website starting from the given URL.
        
        This method implements a breadth-first search algorithm to crawl the website,
        with optional AI-powered content processing and link filtering for improved quality.
        
        Args:
            start_url: The URL to start scraping from
            operation_id: Optional operation ID for tracking
            
        Returns:
            Dictionary containing scraped content and metadata
        """
        # Record start time
        self.stats["start_time"] = datetime.now()
        
        # Parse start URL
        parsed_url = urlparse(start_url)
        
        # Initialize queue with start URL at depth 0
        self.url_queue.append(start_url)
        self.url_to_depth[start_url] = 0
        
        try:
            # Initialize Playwright browser
            await self._initialize_browser()
            
            # Process URLs in BFS order until queue is empty or limits are reached
            while self.url_queue and len(self.visited_urls) < self.max_pages:
                # Get next URL from queue
                url = self.url_queue.popleft()
                depth = self.url_to_depth[url]
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                    
                # Mark as visited
                self.visited_urls.add(url)
                
                # Process page
                try:
                    await self._process_page(url, depth)
                    self.stats["urls_processed"] += 1
                except Exception as e:
                    logger.error(f"Error processing page {url}: {str(e)}")
                    # Continue with next URL to make the scraper more robust
                    # Add error info to stats for debugging
                    if "errors" not in self.stats:
                        self.stats["errors"] = []
                    self.stats["errors"].append({"url": url, "error": str(e)})
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit)
                
                # Process content in batches periodically if AI is enabled
                # This helps optimize API usage while still providing incremental processing
                if self.use_ai and self.batch_size > 1 and len(self.content_map) % self.batch_size == 0:
                    logger.info(f"Performing incremental batch processing after {len(self.content_map)} pages")
                    await self._batch_process_content()
            
            # Record completion statistics
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            # Prepare result
            result = {
                "content_map": self.content_map,
                "stats": {
                    **self.stats,
                    "duration_seconds": duration,
                    "pages_per_second": self.stats["urls_processed"] / max(1, duration)
                },
                "base_url": start_url,
                "domain": parsed_url.netloc
            }
            
            # Batch process content with AI if enabled
            if self.use_ai:
                await self._batch_process_content()
            
            return result
            
        finally:
            # Clean up browser resources
            await self._cleanup_browser()
    
    async def _initialize_browser(self) -> None:
        """
        Initialize Playwright browser for scraping.
        
        Returns:
            None
        """
        logger.info("Initializing browser")
        
        try:
            # Launch browser
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            
            # Create context with viewport and user agent
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 DocExtractAI Documentation Scraper (+https://github.com/your-org/doc-extract-ai)"
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_navigation_timeout(30000)
            self.page.set_default_timeout(10000)
            
            # Configure response caching and resource handling
            await self.context.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
            await self.context.route("**/*.{css,woff,woff2,ttf,otf}", lambda route: route.abort())
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            # Clean up any partially initialized resources
            await self._cleanup_browser()
            raise
    
    async def _cleanup_browser(self) -> None:
        """
        Clean up Playwright browser resources.
        
        Returns:
            None
        """
        logger.info("Cleaning up browser resources")
        
        try:
            if self.page:
                await self.page.close()
                self.page = None
                
            if self.context:
                await self.context.close()
                self.context = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}")
    
    async def _process_page(self, url: str, depth: int) -> None:
        """
        Process a single page: navigate, extract content and links.
        
        Args:
            url: URL to process
            depth: Current depth level
            
        Returns:
            None
        """
        logger.info(f"Processing page: {url} (depth: {depth})")
        
        try:
            # Navigate to the page
            response = await self.page.goto(url, wait_until="networkidle")
            
            # Check if navigation was successful
            if not response or response.status >= 400:
                logger.warning(f"Failed to load {url}: status {response.status if response else 'unknown'}")
                return
                
            # Wait for content to load
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Get HTML content
            html = await self.page.content()
            
            # Extract content
            parsed_url = urlparse(url)
            content_result = await self.content_extractor.extract(html, parsed_url)
            
            # Store content
            self.content_map[url] = {
                "title": content_result["title"],
                "content": content_result["content"],
                "metadata": {
                    "depth": depth,
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                    "ai_processed": False  # Will be updated during batch processing
                }
            }
            
            # Process with AI immediately if enabled and not batching
            if self.use_ai and self.ai_processor and self.batch_size <= 1:
                try:
                    # Process content with AI
                    logger.debug(f"Processing content with AI for {url}")
                    result = await self.ai_processor.process_content(
                        content=content_result["content"],
                        mode="clean",
                        content_type="documentation",
                        metadata={
                            "title": content_result["title"],
                            "url": url,
                            "depth": depth
                        }
                    )
                    
                    # Update content if processing was successful
                    if result["success"]:
                        self.content_map[url]["content"] = result["content"]
                        # Track enhanced pages in metadata
                        if "metadata" not in self.content_map[url]:
                            self.content_map[url]["metadata"] = {}
                        self.content_map[url]["metadata"]["ai_enhanced"] = True
                        self.content_map[url]["metadata"]["ai_processing_time"] = result.get("processing_time", 0)
                        self.stats["ai_processed"] += 1
                except Exception as e:
                    logger.error(f"AI content processing error for {url}: {str(e)}")
                    # Continue with original content as fallback
            
            # Update statistics
            self.stats["urls_processed"] += 1
            
            # Extract and queue links
            await self._extract_and_queue_links(self.page, url, parsed_url)
            
        except Exception as e:
            logger.error(f"Error processing page {url}: {str(e)}")
            # Continue with next URL to make the scraper more robust
            # Add error info to stats for debugging
            if "errors" not in self.stats:
                self.stats["errors"] = []
            self.stats["errors"].append({"url": url, "error": str(e)})
            
    async def _extract_and_queue_links(self, page, current_url, base_url):
        """Extrai e enfileira links da página atual."""
        try:
            extracted_links = await self.link_extractor.extract_links(page, current_url)
            self.logger.debug(f"Extraídos {len(extracted_links)} links de {current_url}")
            
            # Filtra links por URL e normaliza
            valid_links = self._filter_and_normalize_links(extracted_links, base_url)
            self.logger.debug(f"{len(valid_links)} links válidos após filtragem básica")
            
            # Aplica filtragem de IA se disponível
            if self.ai_link_filter and self.use_ai:
                page_title = await page.title()
                context = {
                    "title": page_title,
                    "url": current_url,
                    "content_snippet": await self._get_content_snippet(page) # Assuming _get_content_snippet exists
                }
                
                # Filtra links usando IA para determinar relevância contextual
                filtered_links = await self.ai_link_filter.filter_links(
                    links=valid_links,
                    context=context,
                    base_url=base_url
                )
                
                self.logger.info(f"IA filtrou links: {len(valid_links)} → {len(filtered_links)}")
                valid_links = filtered_links
            
            # Adiciona links válidos e não visitados à fila
            new_links_added = 0
            for link in valid_links:
                # Depth check should happen here based on link.depth compared to self.max_depth
                # Assuming Link object has a depth attribute or we derive it
                # Example check (needs refinement based on actual Link structure):
                # current_depth = self.depth_map.get(current_url, 0) # Need depth tracking
                # link_depth = current_depth + 1 
                # if link_depth > self.max_depth:
                #    continue 

                if link.href not in self.visited_urls and link.href not in self.queued_urls:
                    # Check domain constraints if necessary
                    # parsed_link = urlparse(link.href)
                    # if parsed_link.netloc != base_url.netloc:
                    #    continue
                        
                    self.url_queue.append(link) # Should append tuple (link.href, link_depth)
                    self.queued_urls.add(link.href)
                    # self.depth_map[link.href] = link_depth # Update depth map
                    self.logger.debug(f"Adicionado à fila: {link.href}")
                    new_links_added += 1
            
            return new_links_added
        except Exception as e:
            self.logger.error(f"Erro ao extrair links de {current_url}: {str(e)}")
            return 0
    
    async def _batch_process_content(self) -> None:
        """Process content in batches for efficiency and AI enhancement."""
        if not self.use_ai or not self.ai_processor:
            logger.debug("Skipping batch processing: AI processor not available")
            return
            
        # Only process if we have content to process
        if not self.content_map:
            return
            
        try:
            logger.info(f"Starting batch processing of {len(self.content_map)} pages with AI")
            
            # Prepare batch items
            batch_items = []
            for url, page_data in self.content_map.items():
                batch_items.append({
                    "content": page_data.get("content", ""),
                    "url": url,
                    "title": page_data.get("title", ""),
                    "depth": page_data.get("metadata", {}).get("depth", 0)
                })
            
            # Process in optimized batches
            batch_count = (len(batch_items) + self.batch_size - 1) // self.batch_size
            logger.info(f"Processing content in {batch_count} batches of size {self.batch_size}")
            
            # Process each batch
            for i in range(0, len(batch_items), self.batch_size):
                batch = batch_items[i:i+self.batch_size]
                batch_num = i // self.batch_size + 1
                
                try:
                    logger.info(f"Processing batch {batch_num}/{batch_count}")
                    results = await self.ai_processor.process_batch(
                        content_items=batch,
                        mode="clean",  # Use clean mode for documentation
                        content_type="documentation"
                    )
                    
                    # Update content map with processed content
                    for j, result in enumerate(results):
                        url = batch[j]["url"]
                        if result["success"]:
                            self.content_map[url]["content"] = result["content"]
                            # Track enhanced pages in metadata
                            if "metadata" not in self.content_map[url]:
                                self.content_map[url]["metadata"] = {}
                            self.content_map[url]["metadata"]["ai_enhanced"] = True
                            self.content_map[url]["metadata"]["ai_processing_time"] = result.get("processing_time", 0)
                    
                    # Update statistics
                    self.stats["batches_processed"] += 1
                    
                    # Throttle to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {str(e)}")
                    # Continue with next batch - we still want to process what we can
            
            # Get cache stats if available
            try:
                if hasattr(self.ai_processor, "get_cache_stats"):
                    cache_stats = self.ai_processor.get_cache_stats()
                    self.stats["cache_hits"] = cache_stats.get("cache_hits", 0)
                    # Add cache stats to overall stats
                    self.stats["ai_cache_stats"] = cache_stats
            except Exception as e:
                logger.warning(f"Could not get cache stats: {str(e)}")
            
            logger.info("AI content processing complete")
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            # Don't re-raise to allow scraping to continue with original content
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scraping operation.
        
        Returns:
            Dictionary with current status and statistics
        """
        # Calculate progress
        total_urls = len(self.visited_urls) + len(self.url_queue)
        progress = (len(self.visited_urls) / max(1, total_urls)) * 100 if total_urls > 0 else 0
        
        # Calculate elapsed time
        start_time = self.stats["start_time"] or datetime.now()
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        
        # Calculate rate
        pages_per_second = self.stats["urls_processed"] / max(1, elapsed_seconds)
        
        # Calculate estimated time remaining
        remaining_urls = len(self.url_queue)
        estimated_seconds_remaining = remaining_urls / max(0.1, pages_per_second) if pages_per_second > 0 else 0
        
        # Return status dictionary
        return {
            "urls_discovered": self.stats["urls_discovered"],
            "urls_processed": self.stats["urls_processed"],
            "urls_remaining": remaining_urls,
            "progress_percent": progress,
            "elapsed_seconds": elapsed_seconds,
            "pages_per_second": pages_per_second,
            "estimated_seconds_remaining": estimated_seconds_remaining,
            "is_complete": len(self.url_queue) == 0 or len(self.visited_urls) >= self.max_pages,
            "ai_integration": {
                "enabled": self.use_ai,
                "processed_items": self.stats.get("ai_processed", 0),
                "batches_processed": self.stats.get("batches_processed", 0),
                "cache_hits": self.stats.get("cache_hits", 0)
            }
        }
