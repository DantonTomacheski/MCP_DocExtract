"""
Parallel scraper service implementation.

This module provides a parallel implementation of the scraper service
using asyncio for concurrent processing of multiple pages.
"""

import os
import time
import asyncio
import aiohttp
import random
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urljoin, urlparse, ParseResult
import logging
import traceback
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

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


class ParallelScraperService:
    """
    Parallel scraper service for extracting content from documentation sites.
    
    This service uses asyncio and a worker pool pattern to parallelize the scraping
    process, improving performance for sites with many pages.
    """
    
    def __init__(
        self, 
        content_extractor: IContentExtractor,
        link_extractor: ILinkExtractor,
        max_depth: int = 5,
        max_pages: Optional[int] = None,
        concurrency: int = 3,
        user_agent: str = None,
        respect_robots_txt: bool = True,
        delay_between_requests: float = 0.5,
        use_playwright: bool = False,
        ai_processor: Optional[Any] = None,  # AIContentProcessor
        ai_link_filter: Optional[Any] = None,  # AILinkFilter
        batch_size: int = 5  # Number of items to process in a batch
    ):
        """
        Initialize the parallel scraper service.
        
        Args:
            content_extractor: Strategy for extracting content
            link_extractor: Strategy for extracting links
            max_depth: Maximum depth to crawl
            max_pages: Maximum number of pages to extract (None for unlimited)
            concurrency: Number of concurrent workers
            user_agent: User agent to use for requests
            respect_robots_txt: Whether to respect robots.txt
            delay_between_requests: Delay between requests to the same domain (seconds)
            use_playwright: Whether to use Playwright for rendering JavaScript
        """
        self.content_extractor = content_extractor
        self.link_extractor = link_extractor
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.user_agent = user_agent or f"DocExtractor/1.0 Python Documentation Crawler"
        self.respect_robots_txt = respect_robots_txt
        self.delay_between_requests = delay_between_requests
        self.use_playwright = use_playwright
        self.ai_processor = ai_processor
        self.ai_link_filter = ai_link_filter
        self.batch_size = batch_size
        
        # Flag indicating whether AI capabilities are available and initialized
        self.use_ai = bool(ai_processor) and bool(ai_link_filter)
        
        # Internal state tracking
        self._content_map = {}  # URL -> content
        self._robots_txts = {}  # domain -> robots.txt content
        self._last_request_time = {}  # domain -> last request time
        self._status = {
            "urls_discovered": 0,
            "urls_processed": 0,
            "urls_failed": 0,
            "urls_queued": 0,
            "progress_percent": 0.0,
            "is_running": False,
            "is_complete": False,
            "start_time": None,
            "end_time": None,
            "ai_processed": 0,
            "batches_processed": 0,
            "cache_hits": 0
        }
        
        # Queue and sets for tracking URLs
        self._url_queue = None
        self._visited_urls = None
        self._failed_urls = None
        
        # Lock for status updates
        self._status_lock = asyncio.Lock()
        
        # For Playwright
        self._playwright = None
        self._browser = None
    
    async def scrape(self, start_url: str, operation_id: str = None) -> Dict[str, Any]:
        """
        Scrape a documentation site starting from the given URL.
        
        Args:
            start_url: URL to start scraping from
            operation_id: Optional ID for tracking the operation
            
        Returns:
            Dictionary with content map and statistics
        """
        # Parse and normalize the start URL
        parsed_url = urlparse(start_url)
        if not parsed_url.scheme:
            start_url = f"https://{start_url}"
            parsed_url = urlparse(start_url)
        
        # Reset state
        self._content_map = {}
        self._robots_txts = {}
        self._url_queue = asyncio.Queue()
        self._visited_urls = set()
        self._failed_urls = set()
        
        # Initialize status
        async with self._status_lock:
            self._status = {
                "urls_discovered": 1,  # Starting URL
                "urls_processed": 0,
                "urls_failed": 0,
                "urls_queued": 1,  # Starting URL
                "progress_percent": 0.0,
                "is_running": True,
                "is_complete": False,
                "start_time": datetime.now(),
                "end_time": None,
                "operation_id": operation_id
            }
        
        # Add the start URL to the queue
        domain = parsed_url.netloc
        await self._url_queue.put((start_url, 0, domain))  # (url, depth, domain)
        
        try:
            # Initialize browser if using Playwright
            if self.use_playwright:
                logger.info(f"Initializing Playwright browser")
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
            
            # Create worker tasks
            logger.info(f"Starting {self.concurrency} worker tasks")
            workers = [
                asyncio.create_task(self._worker(i)) for i in range(self.concurrency)
            ]
            
            # Wait for all workers to complete
            logger.info(f"Waiting for workers to complete")
            await asyncio.gather(*workers)
            
            # Update status
            async with self._status_lock:
                self._status["is_running"] = False
                self._status["is_complete"] = True
                self._status["end_time"] = datetime.now()
                self._status["progress_percent"] = 100.0
            
            # Calculate statistics
            duration = (self._status["end_time"] - self._status["start_time"]).total_seconds()
            pages_per_second = self._status["urls_processed"] / duration if duration > 0 else 0
            
            # Process content in batches with AI if enabled
            if self.use_ai and self.ai_processor:
                logger.info("Starting batch processing of content with AI")
                await self._batch_process_content()
            
            # Return results
            logger.info(f"Scraping completed. Processed {self._status['urls_processed']} pages in {duration:.2f} seconds ({pages_per_second:.2f} pages/sec)")
            return {
                "content_map": self._content_map,
                "stats": {
                    "urls_discovered": self._status["urls_discovered"],
                    "urls_processed": self._status["urls_processed"],
                    "urls_failed": self._status["urls_failed"],
                    "duration_seconds": duration,
                    "pages_per_second": pages_per_second,
                    "ai_processed": self._status.get("ai_processed", 0),
                    "batches_processed": self._status.get("batches_processed", 0),
                    "cache_hits": self._status.get("cache_hits", 0)
                },
                "base_url": start_url,
                "domain": domain,
                "ai_enabled": self.use_ai
            }
        except Exception as e:
            logger.error(f"Error in scraping process: {str(e)}", exc_info=True)
            # Update status
            async with self._status_lock:
                self._status["is_running"] = False
                self._status["is_complete"] = True
                self._status["end_time"] = datetime.now()
                self._status["error"] = str(e)
            raise
        finally:
            # Cleanup resources
            if self.use_playwright and self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scraping process.
        
        Returns:
            Dictionary with status information
        """
        async with self._status_lock:
            return self._status.copy()
    
    async def _worker(self, worker_id: int) -> None:
        """
        Worker task for processing URLs from the queue.
        
        Args:
            worker_id: ID of the worker
        """
        logger.debug(f"Worker {worker_id} started")
        
        try:
            while True:
                # Check if we've reached the maximum number of pages
                if self.max_pages is not None:
                    async with self._status_lock:
                        if self._status["urls_processed"] >= self.max_pages:
                            logger.info(f"Worker {worker_id} stopping: reached max pages ({self.max_pages})")
                            break
                
                # Try to get a URL from the queue with a timeout
                try:
                    url, depth, domain = await asyncio.wait_for(self._url_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Check if the queue is empty or if we're still processing
                    if self._url_queue.qsize() == 0:
                        async with self._status_lock:
                            if self._status["urls_queued"] <= (self._status["urls_processed"] + self._status["urls_failed"]):
                                logger.info(f"Worker {worker_id} stopping: queue is empty")
                                break
                    # Continue trying
                    continue
                
                try:
                    # Skip if already visited
                    if url in self._visited_urls:
                        self._url_queue.task_done()
                        continue
                    
                    # Add to visited set
                    self._visited_urls.add(url)
                    
                    # Process the URL
                    logger.debug(f"Worker {worker_id} processing URL: {url} (depth {depth})")
                    
                    # Wait for rate limiting if needed
                    await self._respect_rate_limit(domain)
                    
                    # Fetch and process the page
                    await self._process_url(url, depth, domain)
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
                    self._failed_urls.add(url)
                    async with self._status_lock:
                        self._status["urls_failed"] += 1
                finally:
                    # Mark task as done
                    self._url_queue.task_done()
                    
                    # Update progress
                    await self._update_progress()
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {str(e)}", exc_info=True)
        finally:
            logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_url(self, url: str, depth: int, domain: str) -> None:
        """
        Process a URL to extract content and discover links.
        
        Args:
            url: URL to process
            depth: Current depth level
            domain: Domain of the URL
        """
        # Step 1: Fetch the page content
        try:
            html, status_code = await self._fetch_url(url, domain)
            if not html or status_code >= 400:
                logger.warning(f"Failed to fetch {url}: status code {status_code}")
                self._failed_urls.add(url)
                async with self._status_lock:
                    self._status["urls_failed"] += 1
                return
            
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Step 2: Extract content
            content_data = await self.content_extractor.extract(html, parsed_url)
            
            # Add metadata to content data
            if "metadata" not in content_data:
                content_data["metadata"] = {}
                
            content_data["metadata"].update({
                "depth": depth,
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "ai_processed": False  # Will be updated during batch processing
            })
            
            # Store in content map
            self._content_map[url] = content_data
            
            # Process with AI immediately if enabled and not batching
            if self.use_ai and self.ai_processor and self.batch_size <= 1:
                try:
                    # Process content with AI
                    logger.debug(f"Processing content with AI for {url}")
                    result = await self.ai_processor.process_content(
                        content=content_data["content"],
                        mode="clean",
                        content_type="documentation",
                        metadata={
                            "title": content_data.get("title", ""),
                            "url": url,
                            "depth": depth
                        }
                    )
                    
                    # Update content if processing was successful
                    if result["success"]:
                        self._content_map[url]["content"] = result["content"]
                        # Track enhanced pages in metadata
                        if "metadata" not in self._content_map[url]:
                            self._content_map[url]["metadata"] = {}
                        self._content_map[url]["metadata"]["ai_enhanced"] = True
                        self._content_map[url]["metadata"]["ai_processing_time"] = result.get("processing_time", 0)
                    
                    # Update statistics
                    async with self._status_lock:
                        self._status["ai_processed"] += 1
                except Exception as e:
                    logger.error(f"AI content processing error for {url}: {str(e)}")
                    # Continue with original content as fallback
            
            # Update processed count
            async with self._status_lock:
                self._status["urls_processed"] += 1
            
            # If we've reached max depth, don't extract links
            if depth >= self.max_depth:
                return
            
            # Step 3: Extract links
            links = await self.link_extractor.extract(html, parsed_url)
            
            # Filter and queue discovered links
            await self._process_discovered_links(links, url, parsed_url, None)
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}", exc_info=True)
            raise
    
    async def _fetch_url(self, url: str, domain: str) -> Tuple[str, int]:
        """
        Fetch a URL and return its content.
        
        Args:
            url: URL to fetch
            domain: Domain of the URL
            
        Returns:
            Tuple of (html_content, status_code)
        """
        if self.use_playwright:
            return await self._fetch_url_with_playwright(url)
        else:
            return await self._fetch_url_with_requests(url)
    
    async def _fetch_url_with_requests(self, url: str) -> Tuple[str, int]:
        """
        Fetch a URL using the requests library.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (html_content, status_code)
        """
        # Use requests in a non-blocking way with run_in_executor
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    timeout=30
                )
            )
            return response.text, response.status_code
        except Exception as e:
            logger.error(f"Error fetching {url} with requests: {str(e)}")
            return "", 500
    
    async def _fetch_url_with_playwright(self, url: str) -> Tuple[str, int]:
        """
        Fetch a URL using Playwright for JavaScript rendering.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (html_content, status_code)
        """
        try:
            # Create a new page
            page = await self._browser.new_page()
            try:
                # Set user agent
                await page.set_extra_http_headers({"User-Agent": self.user_agent})
                
                # Navigate to URL
                response = await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Get the HTML content
                html = await page.content()
                
                # Get status code
                status_code = response.status if response else 500
                
                return html, status_code
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"Error fetching {url} with Playwright: {str(e)}")
            return "", 500
    
    async def _process_discovered_links(self, links: List[Any], current_url: str, base_url: ParseResult, context: Optional[Dict] = None):
        """Processa links descobertos, filtrando e adicionando à fila."""
        try:
            # Filtra links por URL e normaliza
            # Assuming _filter_and_normalize_links exists and returns a list of Link objects/tuples
            valid_links = self._filter_and_normalize_links(links, base_url)
            self.logger.debug(f"{len(valid_links)} links válidos após filtragem básica para {current_url}")

            # Aplica filtragem de IA se disponível
            if self.ai_link_filter and self.use_ai:
                if context is None:
                    # If context isn't passed, we might need to fetch basic info 
                    # or define a default. Fetching here might be inefficient.
                    # Consider passing necessary context from the calling worker.
                    context = {
                        "title": "Unknown", # Placeholder
                        "url": current_url,
                        # Potentially add content snippet if available from worker
                    }
                
                # Filtra links usando IA para determinar relevância contextual
                self.logger.debug(f"Aplicando filtro de IA para links de {current_url}")
                filtered_links = await self.ai_link_filter.filter_links(
                    links=valid_links,
                    context=context,
                    base_url=base_url
                )
                
                self.logger.info(f"IA filtrou links para {current_url}: {len(valid_links)} → {len(filtered_links)}")
                valid_links = filtered_links # Update valid_links with the AI-filtered list
                
                # Atualiza métricas de IA
                async with self._status_lock:
                    # This metric might be confusing - it counts links *after* AI filtering.
                    # Maybe rename to ai_approved_links or similar?
                    self._status["ai_filtered_links"] = self._status.get("ai_filtered_links", 0) + len(filtered_links)
        
            # Adiciona links válidos e não visitados à fila
            new_links_queued = 0
            async with self._status_lock: # Ensure lock protects both queue and sets
                # Need depth tracking similar to sequential service
                # current_depth = self.depth_map.get(current_url, 0)

                for link in valid_links:
                    # Check depth
                    # link_depth = current_depth + 1
                    # if link_depth > self.max_depth:
                    #     continue

                    # Check domain constraints if necessary
                    # parsed_link = urlparse(link.href)
                    # if parsed_link.netloc != base_url.netloc:
                    #    continue

                    if link.href not in self._visited_urls and link.href not in self._failed_urls:
                        await self._url_queue.put((link.href, 0)) # Should put tuple (link.href, link_depth)
                        self._visited_urls.add(link.href)
                        # self.depth_map[link.href] = link_depth
                        new_links_queued += 1
                        self.logger.debug(f"Adicionado à fila: {link.href}")
            
            return new_links_queued
        except Exception as e:
            self.logger.error(f"Erro ao processar links de {current_url}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0
    
    async def _respect_rate_limit(self, domain: str) -> None:
        """
        Respect rate limiting for a domain.
        
        Args:
            domain: Domain to check rate limits for
        """
        if not domain or self.delay_between_requests <= 0:
            return
            
        last_time = self._last_request_time.get(domain)
        if last_time:
            elapsed = time.time() - last_time
            if elapsed < self.delay_between_requests:
                wait_time = self.delay_between_requests - elapsed
                # Add a small random variation
                wait_time += random.uniform(0, 0.5)
                await asyncio.sleep(wait_time)
        
        # Update last request time
        self._last_request_time[domain] = time.time()
    
    def _is_allowed_by_robots_txt(self, url: str, domain: str) -> bool:
        """
        Check if a URL is allowed by robots.txt.
        
        Args:
            url: URL to check
            domain: Domain to check robots.txt for
            
        Returns:
            Boolean indicating if the URL is allowed
        """
        # For now, just allow everything
        # In a real implementation, we would parse and respect robots.txt
        return True
    
    async def _update_progress(self) -> None:
        """Update the progress percentage of the scraping process."""
        async with self._status_lock:
            total = self._status["urls_discovered"]
            processed = self._status["urls_processed"] + self._status["urls_failed"]
            
            # Avoid division by zero
            if total > 0:
                progress = (processed / total) * 100
                self._status["progress_percent"] = min(99.9, progress)  # Cap at 99.9% until complete
            
            logger.debug(f"Progress: {self._status['progress_percent']:.1f}% ({processed}/{total})")
    
    async def cancel(self) -> bool:
        """
        Cancel the scraping operation.
        
        Returns:
            Boolean indicating if cancellation was successful
        """
        async with self._status_lock:
            if not self._status["is_running"]:
                return False
                
            self._status["is_running"] = False
            self._status["is_complete"] = True
            self._status["end_time"] = datetime.now()
            self._status["cancelled"] = True
            
            logger.info(f"Scraping operation cancelled")
            
            # Cleanup resources
            if self.use_playwright and self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
                
            return True
            
    async def _batch_process_content(self) -> None:
        """Process content in batches for efficiency and AI enhancement."""
        if not self.use_ai or not self.ai_processor:
            logger.debug("Skipping batch processing: AI processor not available")
            return
            
        # Only process if we have content to process
        if not self._content_map:
            return
            
        try:
            logger.info(f"Starting batch processing of {len(self._content_map)} pages with AI")
            
            # Prepare batch items
            batch_items = []
            for url, page_data in self._content_map.items():
                # Skip already processed items
                if page_data.get("metadata", {}).get("ai_processed", False):
                    continue
                    
                batch_items.append({
                    "content": page_data.get("content", ""),
                    "url": url,
                    "title": page_data.get("title", ""),
                    "depth": page_data.get("metadata", {}).get("depth", 0)
                })
            
            # Skip if no items to process
            if not batch_items:
                logger.info("No content items to process")
                return
            
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
                            self._content_map[url]["content"] = result["content"]
                            # Track enhanced pages in metadata
                            if "metadata" not in self._content_map[url]:
                                self._content_map[url]["metadata"] = {}
                            self._content_map[url]["metadata"]["ai_enhanced"] = True
                            self._content_map[url]["metadata"]["ai_processing_time"] = result.get("processing_time", 0)
                    
                    # Update statistics
                    async with self._status_lock:
                        self._status["batches_processed"] = self._status.get("batches_processed", 0) + 1
                        self._status["ai_processed"] = self._status.get("ai_processed", 0) + len(results)
                    
                    # Throttle to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {str(e)}")
                    # Continue with next batch - we still want to process what we can
            
            # Get cache stats if available
            try:
                if hasattr(self.ai_processor, "get_cache_stats"):
                    cache_stats = self.ai_processor.get_cache_stats()
                    async with self._status_lock:
                        self._status["cache_hits"] = cache_stats.get("cache_hits", 0)
                        # Add cache stats to overall stats
                        self._status["ai_cache_stats"] = cache_stats
            except Exception as e:
                logger.warning(f"Could not get cache stats: {str(e)}")
            
            logger.info("AI content processing complete")
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            # Don't re-raise to allow scraping to continue with original content
