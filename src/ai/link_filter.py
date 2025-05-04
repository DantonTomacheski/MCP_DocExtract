"""
AI-powered link relevance filter for documentation scraping.

This module implements AI-based filtering of links to determine which
are most relevant to the documentation context and should be followed
during scraping.
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
import json
from datetime import datetime
import time
import re
from urllib.parse import urlparse, urljoin

# Optional import for OpenAI API
try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.utils.logging import get_logger

# Get logger
logger = get_logger(__name__)


class AILinkFilter:
    """
    AI-powered link filter for determining documentation relevance.
    
    This class uses AI models to analyze links in the context of a page
    and determine which links are relevant to documentation and should
    be followed during scraping.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-nano",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        batch_size: int = 20,
        cache_dir: Optional[str] = None,
        relevance_threshold: float = 0.7
    ):
        """
        Initialize the AI link filter.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: AI model to use
            temperature: Creativity level (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            batch_size: Maximum links to process in one batch
            cache_dir: Directory to store cache (defaults to ./.cache/ai)
            relevance_threshold: Minimum score to consider a link relevant (0.0-1.0)
        """
        # Store configuration
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._batch_size = batch_size
        self._relevance_threshold = relevance_threshold
        
        # Initialize API client
        self._setup_client(api_key)
        
        # Configure caching
        if cache_dir:
            self._cache_dir = cache_dir
        else:
            # Default to hidden directory in project root
            self._cache_dir = os.path.join(os.getcwd(), ".cache", "ai")
            
        # Create cache directory if it doesn't exist
        os.makedirs(self._cache_dir, exist_ok=True)
        
        # Initialize cache
        self._cache = self._load_cache()
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Initialize known patterns
        self._initialize_patterns()
    
    def _setup_client(self, api_key: Optional[str]) -> None:
        """
        Set up the OpenAI client.
        
        Args:
            api_key: API key, or None to use environment variable
        """
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not available. Install with: pip install openai")
            self._client = None
            return
            
        # Get API key from parameter or environment
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self._api_key:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
            self._client = None
            return
            
        # Initialize client - use standard client for newer API
        self._client = OpenAI(api_key=self._api_key)
        logger.info(f"Initialized AI link filter with model {self._model}")
    
    def _initialize_patterns(self) -> None:
        """Initialize regex patterns for common documentation links."""
        # Common documentation link patterns
        self._doc_patterns = [
            # Common documentation paths
            r'/(docs|documentation|manual|guide|tutorial|reference|api|learn|help|faq)/.*',
            # Common documentation file extensions
            r'.*\.(md|markdown|html|htm|rst|txt|pdf)$',
            # Common versioned doc paths
            r'/v\d+/.*',
            # Common section dividers in URLs
            r'/.*#.*',
            # Common documentation keywords in paths
            r'/(get[-_]?started|quick[-_]?start|introduction|overview|examples|concepts|how[-_]?to)(/|$)',
        ]
        
        # Non-documentation patterns to exclude
        self._exclude_patterns = [
            # Media files
            r'.*\.(jpg|jpeg|png|gif|svg|webp|mp4|webm|mp3|wav|zip|tar\.gz|exe|dmg)$',
            # Common non-documentation paths
            r'/(login|signin|signup|register|account|profile|contact|about|pricing|blog|news|forum|community|download)(/|$)',
            # Social media links
            r'/(twitter|facebook|linkedin|instagram|github|youtube)(/|$)',
            # Common tracking parameters
            r'.*\?(utm_|fbclid|gclid).*',
        ]
        
        # Compile patterns for efficiency
        self._doc_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self._doc_patterns]
        self._exclude_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self._exclude_patterns]
    
    def _load_cache(self) -> Dict[str, Any]:
        """
        Load the cache from disk.
        
        Returns:
            Dictionary with cached results
        """
        cache_file = os.path.join(self._cache_dir, "link_filter_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"Loaded link filter cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load link filter cache: {str(e)}")
                
        return {}
    
    def _save_cache(self) -> None:
        """Save the cache to disk."""
        cache_file = os.path.join(self._cache_dir, "link_filter_cache.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved link filter cache with {len(self._cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save link filter cache: {str(e)}")
    
    def _get_cache_key(self, url: str, page_url: str) -> str:
        """
        Generate a cache key for a URL and context.
        
        Args:
            url: The URL to filter
            page_url: The URL of the page containing the link
            
        Returns:
            Cache key string
        """
        # Use URL + page_url as key
        return f"{url}|{page_url}"
    
    def is_likely_documentation(self, url: str) -> bool:
        """
        Check if a URL matches common documentation patterns (without AI).
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL is likely documentation
        """
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path
        
        # Check if URL matches any documentation patterns
        for pattern in self._doc_regex:
            if pattern.search(path):
                return True
                
        # Check if URL matches any exclusion patterns
        for pattern in self._exclude_regex:
            if pattern.search(path):
                return False
                
        # Default to true for paths with depth > 1 that aren't explicitly excluded
        path_parts = [p for p in path.split('/') if p]
        return len(path_parts) > 1
    
    async def analyze_link(
        self,
        url: str,
        page_url: str,
        page_title: str,
        page_content: str,
        link_text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single link for documentation relevance.
        
        Args:
            url: The URL to analyze
            page_url: URL of the page containing the link
            page_title: Title of the page containing the link
            page_content: Content of the page (can be truncated)
            link_text: Text of the link
            context: Additional context around the link (optional)
            
        Returns:
            Dictionary with relevance score and metadata
        """
        # Check if client is available
        if not self._client:
            logger.warning("AI client not available. Using pattern matching only.")
            is_relevant = self.is_likely_documentation(url)
            return {
                "url": url,
                "is_relevant": is_relevant,
                "relevance_score": 1.0 if is_relevant else 0.0,
                "method": "pattern_matching",
                "analyzed_at": datetime.now().isoformat()
            }
        
        # Generate cache key
        cache_key = self._get_cache_key(url, page_url)
        
        # Check cache
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.debug(f"Link filter cache hit ({self._cache_hits}/{self._cache_hits + self._cache_misses})")
            return self._cache[cache_key]
            
        self._cache_misses += 1
        logger.debug(f"Link filter cache miss ({self._cache_misses}/{self._cache_hits + self._cache_misses})")
        
        # First do pattern matching to avoid unnecessary API calls
        pattern_match_relevant = self.is_likely_documentation(url)
        
        # If it's clearly not documentation by pattern, skip AI analysis
        if not pattern_match_relevant and not context:
            # Only skip AI if we don't have link context, as context might reveal relevance
            result = {
                "url": url,
                "is_relevant": False,
                "relevance_score": 0.0,
                "method": "pattern_matching",
                "reason": "Excluded by documentation patterns",
                "analyzed_at": datetime.now().isoformat()
            }
            self._cache[cache_key] = result
            return result
        
        # Process with AI
        try:
            # Prepare content sample (truncate to reduce tokens)
            content_sample = page_content[:1000] + ("..." if len(page_content) > 1000 else "")
            
            # Get link context if not provided (text around the link)
            if not context and link_text and link_text in page_content:
                # Try to get ~100 chars before and after the link text
                link_pos = page_content.find(link_text)
                start = max(0, link_pos - 100)
                end = min(len(page_content), link_pos + len(link_text) + 100)
                context = page_content[start:end]
            
            # Call AI to analyze the link
            start_time = time.time()
            result = await self._analyze_with_ai(url, page_url, page_title, content_sample, link_text, context)
            elapsed_time = time.time() - start_time
            
            # Format the result
            analysis_result = {
                "url": url,
                "is_relevant": result["is_relevant"],
                "relevance_score": result["relevance_score"],
                "reason": result.get("reason", ""),
                "method": "ai_analysis",
                "processing_time": elapsed_time,
                "analyzed_at": datetime.now().isoformat(),
                "model": self._model
            }
            
            # Store in cache
            self._cache[cache_key] = analysis_result
            
            # Save cache periodically (every 20 new entries)
            if self._cache_misses % 20 == 0:
                self._save_cache()
                
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing link: {str(e)}")
            
            # Fallback to pattern matching on error
            is_relevant = self.is_likely_documentation(url)
            result = {
                "url": url,
                "is_relevant": is_relevant,
                "relevance_score": 1.0 if is_relevant else 0.0,
                "method": "pattern_matching_fallback",
                "reason": f"AI analysis error: {str(e)}",
                "analyzed_at": datetime.now().isoformat()
            }
            
            # Store in cache to avoid repeated errors
            self._cache[cache_key] = result
            return result
    
    async def analyze_links_batch(
        self,
        links: List[Dict[str, Any]],
        base_url: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple links in batches for efficiency.
        
        Args:
            links: List of link dictionaries with url, page_url, etc.
            base_url: Base URL of the documentation site
            
        Returns:
            List of link analysis results
        """
        # Check if client is available
        if not self._client:
            logger.warning("AI client not available. Using pattern matching only.")
            return [{
                "url": link["url"],
                "is_relevant": self.is_likely_documentation(link["url"]),
                "relevance_score": 1.0 if self.is_likely_documentation(link["url"]) else 0.0,
                "method": "pattern_matching",
                "analyzed_at": datetime.now().isoformat()
            } for link in links]
        
        # Normalize URLs
        normalized_links = []
        for link in links:
            # Make sure URL is absolute
            url = urljoin(base_url, link["url"]) if "url" in link else ""
            if not url:
                continue
                
            normalized_links.append({
                **link,
                "url": url
            })
        
        # Prepare tasks list
        tasks = []
        batch_size = self._batch_size
        
        # Create batches with optimal size
        for i in range(0, len(normalized_links), batch_size):
            batch = normalized_links[i:i+batch_size]
            
            # Use gather to process batch concurrently
            batch_tasks = []
            for item in batch:
                task = self.analyze_link(
                    url=item["url"],
                    page_url=item.get("page_url", base_url),
                    page_title=item.get("page_title", ""),
                    page_content=item.get("page_content", ""),
                    link_text=item.get("link_text", ""),
                    context=item.get("context", "")
                )
                batch_tasks.append(task)
            
            # Schedule batch
            tasks.append(asyncio.gather(*batch_tasks))
        
        # Process all batches
        results = []
        for i, batch_future in enumerate(tasks):
            try:
                batch_result = await batch_future
                results.extend(batch_result)
                logger.info(f"Analyzed link batch {i+1}/{len(tasks)}")
            except Exception as e:
                logger.error(f"Error processing link batch {i+1}: {str(e)}")
                # Handle failed batch with pattern matching
                batch_start = i * batch_size
                batch_end = min(batch_start + batch_size, len(normalized_links))
                for j in range(batch_start, batch_end):
                    link = normalized_links[j]
                    url = link["url"]
                    is_relevant = self.is_likely_documentation(url)
                    results.append({
                        "url": url,
                        "is_relevant": is_relevant,
                        "relevance_score": 1.0 if is_relevant else 0.0,
                        "method": "pattern_matching_fallback",
                        "reason": f"Batch error: {str(e)}",
                        "analyzed_at": datetime.now().isoformat()
                    })
        
        # Save cache after processing is done
        self._save_cache()
        
        return results
    
    async def filter_links(
        self,
        links: List[str],
        base_url: str,
        page_url: str,
        page_title: str = "",
        page_content: str = ""
    ) -> List[str]:
        """
        Filter a list of links to only include relevant documentation links.
        
        Args:
            links: List of URLs to filter
            base_url: Base URL of the documentation site
            page_url: URL of the page containing the links
            page_title: Title of the page
            page_content: Content of the page
            
        Returns:
            Filtered list of relevant documentation URLs
        """
        # Prepare link items for batch processing
        link_items = []
        for url in links:
            # Normalize URL
            full_url = urljoin(base_url, url)
            
            # Only include links that are part of the same domain/subdomain
            if not self._is_same_site(full_url, base_url):
                continue
                
            # Find link text if possible
            link_text = self._extract_link_text(url, page_content)
            
            link_items.append({
                "url": full_url,
                "page_url": page_url,
                "page_title": page_title,
                "page_content": page_content,
                "link_text": link_text
            })
        
        # Analyze links in batch
        analysis_results = await self.analyze_links_batch(link_items, base_url)
        
        # Filter to only include relevant links
        relevant_links = []
        for result in analysis_results:
            if result["is_relevant"] and result["relevance_score"] >= self._relevance_threshold:
                relevant_links.append(result["url"])
        
        return relevant_links
    
    def _is_same_site(self, url: str, base_url: str) -> bool:
        """
        Check if URL is part of the same site as base_url.
        
        Args:
            url: URL to check
            base_url: Base URL of the site
            
        Returns:
            True if URLs are from the same site
        """
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        
        # Compare domains, allowing subdomains of the same domain
        url_domain = parsed_url.netloc
        base_domain = parsed_base.netloc
        
        # Exact domain match
        if url_domain == base_domain:
            return True
            
        # Check if one is a subdomain of the other
        url_parts = url_domain.split('.')
        base_parts = base_domain.split('.')
        
        # Compare the main domain parts (last two parts)
        if len(url_parts) >= 2 and len(base_parts) >= 2:
            url_main = '.'.join(url_parts[-2:])
            base_main = '.'.join(base_parts[-2:])
            return url_main == base_main
            
        return False
    
    def _extract_link_text(self, url: str, page_content: str) -> str:
        """
        Extract link text for a URL from page content.
        
        Args:
            url: URL to find in page content
            page_content: HTML content of the page
            
        Returns:
            Link text if found, empty string otherwise
        """
        # Simple regex to find link text for this URL
        # This is a basic implementation and might not work for all cases
        url_escaped = re.escape(url)
        pattern = f'<a[^>]*href=["\'](?:{url_escaped}|[^"\']*?{url_escaped})["\'][^>]*>(.*?)</a>'
        
        matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
        if matches:
            # Remove HTML tags from link text
            link_text = re.sub(r'<[^>]*>', '', matches[0])
            return link_text.strip()
            
        return ""
    
    async def _analyze_with_ai(
        self,
        url: str,
        page_url: str,
        page_title: str,
        page_content: str,
        link_text: str,
        context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use AI to analyze link relevance.
        
        Args:
            url: URL to analyze
            page_url: URL of the page containing the link
            page_title: Title of the page
            page_content: Sample of page content
            link_text: Text of the link
            context: Text surrounding the link
            
        Returns:
            Analysis result with relevance score
        """
        # Create system message
        system_message = {
            "role": "system",
            "content": """
You are an expert documentation analyzer.
Your task is to determine if a URL is relevant to technical documentation and should be included in a documentation scrape.

Score from 0.0 to 1.0 (higher = more relevant) and provide true/false for is_relevant based on:
1. If the URL appears to be documentation, API reference, guides, tutorials, or technical information
2. If the URL is likely to contain technical content based on the link text and context
3. If the URL is part of a logical documentation structure
4. If the URL seems to be part of the same documentation as the source page

Technical documentation typically contains:
- API references
- Function/method specifications
- Code examples
- Technical guides/tutorials
- Concept explanations
- Architecture diagrams/explanations

Do NOT include:
- Marketing pages
- Blog posts (unless technical tutorials)
- News articles
- Community forums/discussions
- Download pages

Format your response as valid JSON with these fields:
{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0,
  "reason": "brief explanation"
}
"""
        }
        
        # Create user message with content and metadata
        user_message = {
            "role": "user",
            "content": f"""
Analyze this link:

URL: {url}
Link Text: {link_text or "N/A"}
Page URL: {page_url}
Page Title: {page_title or "N/A"}

{"Context around the link:" if context else ""}
{context or ""}

{"Sample page content:" if page_content else ""}
{page_content or ""}

Is this URL relevant to documentation and should be included in scraping?
"""
        }
        
        # Make API call using new responses.create API
        try:
            response = self._client.responses.create(
                model=self._model,
                input=[
                    {"type": "system", "content": system_message["content"]},
                    {"type": "user", "content": user_message["content"]}
                ],
                text={"format": {"type": "json_object"}},
                reasoning={},
                tools=[],
                temperature=self._temperature,
                max_output_tokens=self._max_tokens,
                top_p=1,
                store=True
            )
            
            # Extract and return the analysis result
            if response.text:
                result_text = response.text.strip()
                try:
                    result = json.loads(result_text)
                    
                    # Ensure all required fields are present
                    required_fields = ["is_relevant", "relevance_score", "reason"]
                    for field in required_fields:
                        if field not in result:
                            logger.warning(f"Missing field {field} in AI response: {result_text}")
                            result[field] = field == "is_relevant" and False or (field == "relevance_score" and 0.0 or "")
                    
                    return result
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from AI: {result_text}")
                    
                    # Fallback result
                    return {
                        "is_relevant": self.is_likely_documentation(url),
                        "relevance_score": 0.5,
                        "reason": "Failed to parse AI response"
                    }
            else:
                raise ValueError("Empty response from AI API")
                
        except Exception as e:
            logger.error(f"Error calling AI API for link analysis: {str(e)}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(1, total_requests) * 100
        
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": hit_rate,
            "cache_dir": self._cache_dir
        }
    
    def clear_cache(self) -> None:
        """Clear the link filter cache."""
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._save_cache()
        logger.info("Link filter cache cleared")
