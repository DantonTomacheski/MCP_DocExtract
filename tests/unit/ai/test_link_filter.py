"""
Unit tests for the AILinkFilter class.
"""

import os
import pytest
import json
import asyncio
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile

from src.ai.link_filter import AILinkFilter


class TestAILinkFilter:
    """Tests for the AILinkFilter class."""
    
    @pytest.fixture
    def link_filter(self):
        """Return an AILinkFilter instance with mocked API."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filter_instance = AILinkFilter(
                api_key="test_api_key",
                model="gpt-4.1-nano",
                cache_dir=temp_dir,
                relevance_threshold=0.7
            )
            yield filter_instance
    
    @pytest.fixture
    def mock_client(self):
        """Mock the OpenAI client."""
        # First patch the OPENAI_AVAILABLE flag to True
        with patch('src.ai.link_filter.OPENAI_AVAILABLE', True):
            # Then patch the OpenAI class for the new API
            with patch('src.ai.link_filter.OpenAI') as mock:
                mock_instance = MagicMock()
                mock_instance.responses.create = MagicMock()
                mock.return_value = mock_instance
                yield mock_instance
    
    def test_initialization(self, link_filter):
        """Test initializing the AILinkFilter."""
        assert link_filter._model == "gpt-4.1-nano"
        assert link_filter._temperature == 0.0
        assert link_filter._batch_size == 20
        assert link_filter._relevance_threshold == 0.7
        assert isinstance(link_filter._cache, dict)
    
    def test_pattern_initialization(self, link_filter):
        """Test the pattern initialization."""
        # Check that doc patterns were initialized
        assert len(link_filter._doc_regex) > 0
        assert len(link_filter._exclude_regex) > 0
        
        # These patterns should be compiled regex objects
        assert hasattr(link_filter._doc_regex[0], 'search')
    
    def test_is_likely_documentation(self, link_filter):
        """Test pattern-based detection of documentation URLs."""
        # URLs that should be identified as documentation
        doc_urls = [
            "https://example.com/docs/api",
            "https://example.com/documentation/guide",
            "https://example.com/manual/intro",
            "https://example.com/guide/getting-started",
            "https://example.com/api/v1/endpoints",
            "https://example.com/help/faq",
            "https://example.com/reference/methods",
            "https://example.com/v2/api-reference",
            "https://example.com/learn/tutorial",
            "https://example.com/examples/code.html",
            "https://example.com/how-to/deploy",
        ]
        
        # URLs that should NOT be identified as documentation
        non_doc_urls = [
            "https://example.com/blog/new-features",
            "https://example.com/download/latest",
            "https://example.com/about-us",
            "https://example.com/contact",
            "https://example.com/profile",
            "https://example.com/login",
            "https://example.com/signup",
            "https://example.com/img/logo.png",
            "https://example.com/video/demo.mp4",
            "https://example.com/twitter",
            "https://example.com/?utm_source=google",
        ]
        
        # Test documentation URLs
        for url in doc_urls:
            assert link_filter.is_likely_documentation(url), f"URL should be doc: {url}"
            
        # Test non-documentation URLs
        for url in non_doc_urls:
            assert not link_filter.is_likely_documentation(url), f"URL should NOT be doc: {url}"
    
    def test_cache_key_generation(self, link_filter):
        """Test the cache key generation logic."""
        url = "https://example.com/docs/api"
        page_url = "https://example.com/docs"
        
        # Generate cache key
        key = link_filter._get_cache_key(url, page_url)
        
        # Key should include URL and page URL
        assert url in key
        assert page_url in key
        assert "|" in key  # Separator
    
    def test_is_same_site(self, link_filter):
        """Test same site detection logic."""
        base_url = "https://docs.example.com"
        
        # Should match exact domain
        assert link_filter._is_same_site("https://docs.example.com/guide", base_url)
        
        # Should match subdomains of the same domain
        assert link_filter._is_same_site("https://api.example.com/docs", base_url)
        
        # Should NOT match different domains
        assert not link_filter._is_same_site("https://otherdomain.com/docs", base_url)
        
        # Should NOT match different TLDs
        assert not link_filter._is_same_site("https://example.org/docs", base_url)
    
    @pytest.mark.asyncio
    async def test_analyze_link_no_client(self):
        """Test analyze_link when no client is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create link filter with no API key
            link_filter = AILinkFilter(api_key=None, cache_dir=temp_dir)
            link_filter._client = None
            
            url = "https://example.com/docs/api"
            page_url = "https://example.com/docs"
            result = await link_filter.analyze_link(
                url=url,
                page_url=page_url,
                page_title="Docs Home",
                page_content="<h1>Documentation</h1>",
                link_text="API Reference"
            )
            
            # Should use pattern matching and return a valid result
            assert result["url"] == url
            assert isinstance(result["is_relevant"], bool)
            assert isinstance(result["relevance_score"], float)
            assert result["method"] == "pattern_matching"
    
    @pytest.mark.asyncio
    async def test_analyze_link_with_cache_hit(self, link_filter):
        """Test analyze_link with a cache hit."""
        # Make sure the client is available for this test
        with patch('src.ai.link_filter.OPENAI_AVAILABLE', True):
            with patch.object(link_filter, '_client', MagicMock()):
                url = "https://example.com/docs/api"
                page_url = "https://example.com/docs"
                cache_key = link_filter._get_cache_key(url, page_url)
                
                # Populate cache
                cached_result = {
                    "url": url,
                    "is_relevant": True,
                    "relevance_score": 0.95,
                    "method": "ai_analysis",
                    "reason": "API documentation",
                    "analyzed_at": "2025-05-03T00:00:00"
                }
                link_filter._cache[cache_key] = cached_result
                
                # Analyze link
                result = await link_filter.analyze_link(
                    url=url,
                    page_url=page_url,
                    page_title="Docs Home",
                    page_content="<h1>Documentation</h1>",
                    link_text="API Reference"
                )
                
                # Should return cached result
                assert result == cached_result
                assert link_filter._cache_hits == 1
                assert link_filter._cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_analyze_link_api_call(self, link_filter, mock_client):
        """Test analyze_link makes correct API call."""
        with patch('src.ai.link_filter.OPENAI_AVAILABLE', True):
            url = "https://example.com/docs/api"
            page_url = "https://example.com/docs"
            page_title = "Documentation Home"
            page_content = "<h1>Documentation</h1><p>Welcome to our docs.</p>"
            link_text = "API Reference"
            
            # Setup mock API response for the new responses API
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "is_relevant": True,
                "relevance_score": 0.95,
                "reason": "API documentation page"
            })
            
            link_filter._client = MagicMock()
            link_filter._client.responses.create = MagicMock(return_value=mock_response)
            
            # Analyze link
            result = await link_filter.analyze_link(
                url=url,
                page_url=page_url,
                page_title=page_title,
                page_content=page_content,
                link_text=link_text
            )
            
            # Check result
            assert result["url"] == url
            assert result["is_relevant"] is True
            assert result["relevance_score"] == 0.95
            assert result["method"] == "ai_analysis"
            assert "API documentation" in result["reason"]
            
            # Verify API call
            call_args = link_filter._client.chat.completions.create.call_args[1]
            assert call_args["model"] == link_filter._model
            assert call_args["temperature"] == link_filter._temperature
            
            # Check messages
            messages = call_args["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "documentation analyzer" in messages[0]["content"].lower()
            assert messages[1]["role"] == "user"
            assert url in messages[1]["content"]
            assert page_url in messages[1]["content"]
            assert page_title in messages[1]["content"]
            assert link_text in messages[1]["content"]
    
    @pytest.mark.asyncio
    async def test_analyze_links_batch(self, link_filter, mock_client):
        """Test batch processing of links."""
        with patch('src.ai.link_filter.OPENAI_AVAILABLE', True):
            # Create mock response for the new responses API
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "is_relevant": True,
                "relevance_score": 0.95,
                "reason": "API documentation page"
            })
            
            link_filter._client = MagicMock()
            link_filter._client.responses.create = MagicMock(return_value=mock_response)
            
            # Create test batch of links
            base_url = "https://example.com"
            links = [
                {
                    "url": f"https://example.com/docs/page{i}",
                    "page_url": "https://example.com/docs",
                    "page_title": "Docs Home",
                    "page_content": "<h1>Documentation</h1>",
                    "link_text": f"Page {i}"
                } 
                for i in range(25)  # Create 25 items to test multiple batches
            ]
            
            # Process batch (should split into 2 batches with batch_size=20)
            results = await link_filter.analyze_links_batch(links, base_url)
            
            # Should return results for all items
            assert len(results) == 25
            for result in results:
                assert result["is_relevant"] is True
                assert result["relevance_score"] == 0.95
                assert "API documentation" in result["reason"]
                
            # API should be called for each item
            assert link_filter._client.chat.completions.create.call_count == 25
    
    @pytest.mark.asyncio
    async def test_filter_links(self, link_filter):
        """Test filtering a list of links."""
        with patch('src.ai.link_filter.OPENAI_AVAILABLE', True):
            # Setup links
            base_url = "https://example.com"
            page_url = "https://example.com/docs"
            links = [
                "/docs/api",
                "/docs/tutorial",
                "/docs/reference",
                "/blog/news",
                "/download",
                "/contact",
                "https://otherdomain.com/docs"
            ]
            
            # Mock analyze_links_batch to return predetermined results
            async def mock_analyze_batch(links_batch, base):
                results = []
                for link in links_batch:
                    url = link["url"]
                    # Only mark docs URLs as relevant
                    is_relevant = "docs" in url and "blog" not in url and "example.com" in url
                    results.append({
                        "url": url,
                        "is_relevant": is_relevant,
                        "relevance_score": 0.95 if is_relevant else 0.2,
                        "method": "test_mock",
                        "reason": "Test mock result"
                    })
                return results
                
            # Apply mock
            link_filter.analyze_links_batch = mock_analyze_batch
            link_filter._client = MagicMock()
            
            # Filter links
            filtered_links = await link_filter.filter_links(
                links=links,
                base_url=base_url,
                page_url=page_url,
                page_title="Docs Home",
                page_content="<h1>Documentation</h1>"
            )
            
            # Should only include relevant doc links from the same domain
            assert len(filtered_links) == 3
            assert "https://example.com/docs/api" in filtered_links
            assert "https://example.com/docs/tutorial" in filtered_links
            assert "https://example.com/docs/reference" in filtered_links
            
            # Should NOT include blog, download, contact or external domain
            for link in filtered_links:
                assert "blog" not in link
                assert "download" not in link
                assert "contact" not in link
                assert "otherdomain.com" not in link
    
    def test_extract_link_text(self, link_filter):
        """Test extracting link text from HTML content."""
        url = "/docs/api"
        html_content = """
        <html>
        <body>
            <nav>
                <a href="/home">Home</a>
                <a href="/docs/api">API Reference</a>
                <a href="/contact">Contact</a>
            </nav>
        </body>
        </html>
        """
        
        link_text = link_filter._extract_link_text(url, html_content)
        assert link_text == "API Reference"
        
        # Test with non-existent URL
        non_existent_url = "/non-existent"
        empty_text = link_filter._extract_link_text(non_existent_url, html_content)
        assert empty_text == ""
    
    def test_cache_stats(self, link_filter):
        """Test cache statistics reporting."""
        # Set up some hits and misses
        link_filter._cache_hits = 15
        link_filter._cache_misses = 5
        link_filter._cache = {"key1": "value1", "key2": "value2", "key3": "value3"}
        
        # Get stats
        stats = link_filter.get_cache_stats()
        
        # Check stats
        assert stats["cache_size"] == 3
        assert stats["cache_hits"] == 15
        assert stats["cache_misses"] == 5
        assert stats["hit_rate_percent"] == 15 / 20 * 100
        assert stats["cache_dir"] == link_filter._cache_dir
    
    def test_clear_cache(self, link_filter):
        """Test clearing the cache."""
        # Populate cache
        link_filter._cache = {"key1": "value1", "key2": "value2"}
        link_filter._cache_hits = 10
        link_filter._cache_misses = 5
        
        # Clear cache
        link_filter.clear_cache()
        
        # Check cache is empty
        assert link_filter._cache == {}
        assert link_filter._cache_hits == 0
        assert link_filter._cache_misses == 0
