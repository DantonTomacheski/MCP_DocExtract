"""
AI-powered content processor for documentation cleaning and structuring.

This module implements AI-based cleaning and formatting of documentation content
extracted from websites, including structure enhancement, code block detection,
and other improvements to raw HTML content.
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime
import time

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


class AIContentProcessor:
    """
    AI-powered content processor for enhancing documentation.
    
    This class uses AI models to clean, structure, and enhance documentation
    content, including formatting improvements, code detection, and more.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-nano",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        batch_size: int = 5,
        token_limit: int = 4000,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the AI content processor.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: AI model to use
            temperature: Creativity level (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            batch_size: Maximum items to process in one batch
            token_limit: Maximum tokens per API call
            cache_dir: Directory to store cache (defaults to ./.cache/ai)
        """
        # Store configuration
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._batch_size = batch_size
        self._token_limit = token_limit
        
        # Initialize API client
        self._setup_client(api_key)
        
        # Initialize batch processing state
        self._current_batch = []
        self._batch_context = {}
        
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
        logger.info(f"Initialized AI content processor with model {self._model}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """
        Load the cache from disk.
        
        Returns:
            Dictionary with cached results
        """
        cache_file = os.path.join(self._cache_dir, "content_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"Loaded cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load cache: {str(e)}")
                
        return {}
    
    def _save_cache(self) -> None:
        """Save the cache to disk."""
        cache_file = os.path.join(self._cache_dir, "content_cache.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved cache with {len(self._cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save cache: {str(e)}")
    
    def _get_cache_key(self, content: str, mode: str) -> str:
        """
        Generate a cache key for content and mode.
        
        Args:
            content: The content to process
            mode: The processing mode
            
        Returns:
            Cache key string
        """
        # Use first 100 chars + last 100 chars + mode + content length as key
        content_hash = f"{content[:100]}{content[-100:]}{mode}{len(content)}"
        return content_hash
    
    async def process_content(
        self,
        content: str,
        mode: str = "clean",
        content_type: str = "documentation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a single piece of content.
        
        Args:
            content: HTML or text content to process
            mode: Processing mode (clean, summarize, restructure)
            content_type: Type of content (documentation, tutorial, etc.)
            metadata: Additional metadata for context
            
        Returns:
            Dictionary with processed content and metadata
        """
        # Check if client is available
        if not self._client:
            logger.warning("AI client not available. Returning original content.")
            return {
                "content": content,
                "success": False,
                "message": "AI client not available",
                "processed_at": datetime.now().isoformat()
            }
        
        # Generate cache key
        cache_key = self._get_cache_key(content, mode)
        
        # Check cache
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.debug(f"Cache hit ({self._cache_hits}/{self._cache_hits + self._cache_misses})")
            return self._cache[cache_key]
            
        self._cache_misses += 1
        logger.debug(f"Cache miss ({self._cache_misses}/{self._cache_hits + self._cache_misses})")
        
        # Process the content
        try:
            # Get appropriate prompt for the mode
            prompt = self._get_prompt(mode, content_type)
            
            # Call AI to process the content
            start_time = time.time()
            result = await self._call_ai(prompt, content, metadata or {})
            elapsed_time = time.time() - start_time
            
            # Format the result
            processed_result = {
                "content": result,
                "success": True,
                "processing_time": elapsed_time,
                "mode": mode,
                "content_type": content_type,
                "processed_at": datetime.now().isoformat(),
                "model": self._model
            }
            
            # Store in cache
            self._cache[cache_key] = processed_result
            
            # Save cache periodically (every 10 new entries)
            if self._cache_misses % 10 == 0:
                self._save_cache()
                
            return processed_result
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            return {
                "content": content,
                "success": False,
                "message": f"Error: {str(e)}",
                "processed_at": datetime.now().isoformat()
            }
    
    async def process_batch(
        self,
        content_items: List[Dict[str, Any]],
        mode: str = "clean",
        content_type: str = "documentation"
    ) -> List[Dict[str, Any]]:
        """
        Process multiple content items in batches for efficiency.
        
        Args:
            content_items: List of items with content and metadata
            mode: Processing mode
            content_type: Type of content
            
        Returns:
            List of processed content items
        """
        # Check if client is available
        if not self._client:
            logger.warning("AI client not available. Returning original content.")
            return [{
                "content": item.get("content", ""),
                "success": False,
                "message": "AI client not available",
                "processed_at": datetime.now().isoformat(),
                **{k: v for k, v in item.items() if k != "content"}
            } for item in content_items]
        
        # Prepare tasks list
        tasks = []
        batch_size = self._batch_size
        
        # Create batches with optimal size
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i:i+batch_size]
            
            # Use gather to process batch concurrently
            batch_tasks = [
                self.process_content(
                    item.get("content", ""),
                    mode,
                    content_type,
                    {k: v for k, v in item.items() if k != "content"}
                )
                for item in batch
            ]
            
            # Schedule batch
            tasks.append(asyncio.gather(*batch_tasks))
        
        # Process all batches and collect results
        results = []
        for i, batch_future in enumerate(tasks):
            try:
                batch_result = await batch_future
                results.extend(batch_result)
                logger.info(f"Processed batch {i+1}/{len(tasks)}")
            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {str(e)}")
                # Handle failed batch by returning original content
                batch_start = i * batch_size
                batch_end = min(batch_start + batch_size, len(content_items))
                for j in range(batch_start, batch_end):
                    item = content_items[j]
                    results.append({
                        "content": item.get("content", ""),
                        "success": False,
                        "message": f"Batch error: {str(e)}",
                        "processed_at": datetime.now().isoformat(),
                        **{k: v for k, v in item.items() if k != "content"}
                    })
        
        # Save cache after all processing is done
        self._save_cache()
        
        return results
    
    async def _call_ai(
        self,
        prompt: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Call the AI API to process content.
        
        Args:
            prompt: Instruction prompt for the AI
            content: Content to process
            metadata: Additional metadata for context
            
        Returns:
            Processed content string
        """
        # Create system message
        system_message = {
            "role": "system",
            "content": prompt
        }
        
        # Create user message with content and metadata
        user_message = {
            "role": "user",
            "content": f"""
Content to process:
```html
{content}
```

Metadata context:
{json.dumps(metadata, indent=2)}

Process the content according to the instructions.
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
                text={"format": {"type": "text"}},
                reasoning={},
                tools=[],
                temperature=self._temperature,
                max_output_tokens=self._max_tokens,
                top_p=1,
                store=True
            )
            
            # Extract and return the processed content
            if response.text:
                return response.text.strip()
            else:
                raise ValueError("Empty response from AI API")
                
        except Exception as e:
            logger.error(f"Error calling AI API: {str(e)}")
            raise
    
    def _get_prompt(self, mode: str, content_type: str) -> str:
        """
        Get the appropriate prompt for the processing mode.
        
        Args:
            mode: Processing mode
            content_type: Type of content
            
        Returns:
            Prompt string for AI
        """
        prompts = {
            "clean": f"""
You are an expert documentation cleaner and formatter specialized in {content_type} content.
Your task is to clean and format the provided HTML content while:

1. Preserving all important information and context
2. Identifying and properly formatting code blocks with correct syntax highlighting
3. Removing unnecessary HTML elements like navigation bars, footers, etc.
4. Fixing formatting issues and improving readability
5. Ensuring consistent heading structure
6. Preserving links but improving their display text when needed
7. Fixing any broken or incomplete code examples
8. Removing duplicate content

The content should be returned as clean, well-formatted HTML with proper semantic structure.
DO NOT summarize or change the meaning of the content.
""",
            "summarize": f"""
You are an expert documentation summarizer specialized in {content_type} content.
Your task is to create a concise, accurate summary of the provided HTML content while:

1. Identifying the key concepts, functions, and features described
2. Preserving important technical details and parameters
3. Structuring the summary with clear headings and sections
4. Including any critical warnings, notes, or caveats from the original
5. Keeping code examples that are essential to understanding, but simplifying where possible
6. Maintaining accurate links but with improved descriptive text

The summary should be returned as clean, well-formatted HTML that captures the essence of the original content
while being significantly shorter and more focused.
""",
            "restructure": f"""
You are an expert documentation restructurer specialized in {content_type} content.
Your task is to reorganize and improve the structure of the provided HTML content while:

1. Creating a more logical flow of information from basic to advanced concepts
2. Improving heading hierarchy to reflect content importance and relationships
3. Grouping related topics and concepts together
4. Adding clear section markers and improving navigation
5. Preserving all original information and code examples
6. Ensuring consistent formatting and style throughout
7. Improving code block formatting and syntax highlighting
8. Enhancing readability with better paragraph structure

The restructured content should be returned as clean, well-formatted HTML with improved organization
that makes the content easier to navigate and understand.
""",
            "extract_code": f"""
You are an expert code extractor specialized in {content_type} content.
Your task is to identify and extract all code examples from the provided HTML content while:

1. Preserving exact code syntax and formatting
2. Identifying the programming language for each code block
3. Adding appropriate context or comments from surrounding text
4. Organizing code snippets in a logical order
5. Removing any non-code elements
6. Including brief descriptions of what each code block demonstrates
7. Fixing obvious syntax errors or typos in the code
8. Properly formatting the code for readability

The extracted code should be returned as clean, well-formatted HTML with properly tagged code blocks
that could be used as standalone examples.
""",
            "format": f"""
You are an expert content formatter specialized in {content_type} documentation.
Your task is to improve the formatting of the provided HTML content while:

1. Applying consistent styling throughout the document
2. Ensuring proper heading hierarchy (h1, h2, h3, etc.)
3. Formatting code blocks with appropriate syntax highlighting
4. Creating proper lists (ordered and unordered) where appropriate
5. Improving table formatting for readability
6. Enhancing link text for better context
7. Adding appropriate whitespace for readability
8. Preserving all original content and meaning

The formatted content should be returned as clean, well-structured HTML with consistent styling
that improves readability while maintaining all original information.
"""
        }
        
        # Return the appropriate prompt or fallback to "clean" mode
        return prompts.get(mode, prompts["clean"])
    
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
        """Clear the content cache."""
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._save_cache()
        logger.info("Cache cleared")
        
    async def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in text (rough approximation).
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            Estimated token count
        """
        # Simple approximation: ~4 chars per token for English
        return len(text) // 4
