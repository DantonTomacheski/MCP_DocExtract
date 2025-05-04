"""
Unit tests for the AIContentProcessor class.
"""

import os
import pytest
import json
import asyncio
from typing import Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile

from src.ai.content_processor import AIContentProcessor


class TestAIContentProcessor:
    """Tests for the AIContentProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Return an AIContentProcessor instance with mocked API."""
        with tempfile.TemporaryDirectory() as temp_dir:
            processor = AIContentProcessor(
                api_key="test_api_key",
                model="gpt-4.1-nano",
                cache_dir=temp_dir
            )
            yield processor
    
    @pytest.fixture
    def mock_client(self):
        """Mock the OpenAI client."""
        # First patch the OPENAI_AVAILABLE flag to True
        with patch('src.ai.content_processor.OPENAI_AVAILABLE', True):
            # Then patch the OpenAI class for the new API
            with patch('src.ai.content_processor.OpenAI') as mock:
                mock_instance = MagicMock()
                mock_instance.responses.create = MagicMock()
                mock.return_value = mock_instance
                yield mock_instance
    
    def test_initialization(self, processor):
        """Test initializing the AIContentProcessor."""
        assert processor._model == "gpt-4.1-nano"
        assert processor._temperature == 0.0
        assert processor._batch_size == 5
        assert isinstance(processor._cache, dict)
    
    def test_cache_key_generation(self, processor):
        """Test the cache key generation logic."""
        content = "Test content " * 20
        mode = "clean"
        
        # Generate cache key
        key = processor._get_cache_key(content, mode)
        
        # Key should include beginning, end, mode, and length
        assert content[:100] in key
        assert content[-100:] in key
        assert mode in key
        assert str(len(content)) in key
    
    def test_prompt_generation(self, processor):
        """Test prompt generation for different modes."""
        # Test clean mode
        clean_prompt = processor._get_prompt("clean", "API documentation")
        assert "documentation cleaner" in clean_prompt.lower()
        assert "api documentation" in clean_prompt.lower()
        
        # Test summarize mode
        summarize_prompt = processor._get_prompt("summarize", "tutorial")
        assert "summarizer" in summarize_prompt.lower()
        assert "tutorial" in summarize_prompt.lower()
        
        # Test restructure mode
        restructure_prompt = processor._get_prompt("restructure", "code examples")
        assert "restructurer" in restructure_prompt.lower()
        assert "code examples" in restructure_prompt.lower()
        
        # Test with unknown mode (should default to clean)
        unknown_prompt = processor._get_prompt("unknown_mode", "documentation")
        assert "cleaner" in unknown_prompt.lower()
    
    @pytest.mark.asyncio
    async def test_process_content_no_client(self):
        """Test process_content when no client is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create processor with no API key
            processor = AIContentProcessor(api_key=None, cache_dir=temp_dir)
            processor._client = None
            
            content = "<h1>Test Content</h1><p>This is a test.</p>"
            result = await processor.process_content(content)
            
            # Should return original content with error indicator
            assert result["content"] == content
            assert result["success"] is False
            assert "AI client not available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_process_content_with_cache_hit(self, processor):
        """Test process_content with a cache hit."""
        # Make sure the client is available for this test
        with patch('src.ai.content_processor.OPENAI_AVAILABLE', True):
            with patch.object(processor, '_client', MagicMock()):
                content = "<h1>Test Content</h1><p>This is a test.</p>"
                mode = "clean"
                cache_key = processor._get_cache_key(content, mode)
                
                # Populate cache
                cached_result = {
                    "content": "<article><h1>Test Content</h1><p>This is a test.</p></article>",
                    "success": True,
                    "processing_time": 0.5,
                    "mode": mode,
                    "processed_at": "2025-05-03T00:00:00"
                }
                processor._cache[cache_key] = cached_result
                
                # Process content
                result = await processor.process_content(content, mode)
                
                # Should return cached result
                assert result == cached_result
                assert processor._cache_hits == 1
                assert processor._cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_process_content_api_call(self, processor, mock_client):
        """Test process_content makes correct API call."""
        # Set up the mock client
        with patch('src.ai.content_processor.OPENAI_AVAILABLE', True):
            content = "<h1>Test Content</h1><p>This is a test.</p>"
            mock_response = MagicMock()
            mock_response.text = "<article><h1>Test Content</h1><p>This is a test.</p></article>"
            
            processor._client = MagicMock()
            processor._client.responses.create = MagicMock(return_value=mock_response)
            
            # Process content
            result = await processor.process_content(
                content, 
                mode="clean",
                content_type="documentation",
                metadata={"title": "Test Title"}
            )
            
            # Check result
            assert result["success"] is True
            assert result["content"] == mock_message.content
            assert result["mode"] == "clean"
            assert result["content_type"] == "documentation"
            
            # Verify API call
            call_args = processor._client.chat.completions.create.call_args[1]
            assert call_args["model"] == processor._model
            assert call_args["temperature"] == processor._temperature
            assert call_args["max_tokens"] == processor._max_tokens
            
            # Check messages
            messages = call_args["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "cleaner" in messages[0]["content"].lower()
            assert messages[1]["role"] == "user"
            assert content in messages[1]["content"]
            assert "Test Title" in messages[1]["content"]
    
    @pytest.mark.asyncio
    async def test_process_batch(self, processor, mock_client):
        """Test batch processing of content."""
        with patch('src.ai.content_processor.OPENAI_AVAILABLE', True):
            # Create mock response for the new responses API
            mock_response = MagicMock()
            mock_response.text = "<article><h1>Processed Content</h1></article>"
            
            processor._client = MagicMock()
            processor._client.responses.create = MagicMock(return_value=mock_response)
            
            # Create test batch
            content_items = [
                {"content": f"<h1>Test {i}</h1>", "title": f"Title {i}"} 
                for i in range(7)  # Create 7 items to test multiple batches
            ]
            
            # Process batch (should split into 2 batches with batch_size=5)
            results = await processor.process_batch(content_items)
            
            # Should return results for all items
            assert len(results) == 7
            for result in results:
                assert result["success"] is True
                assert result["content"] == mock_message.content
                
            # API should be called for each item (no actual batching in the mock)
            assert processor._client.chat.completions.create.call_count == 7
    
    @pytest.mark.asyncio
    async def test_process_batch_error_handling(self, processor, mock_client):
        """Test batch processing error handling."""
        with patch('src.ai.content_processor.OPENAI_AVAILABLE', True):
            # Set up the mock client
            processor._client = MagicMock()
            
            # Mock gather to simulate a batch failure
            original_gather = asyncio.gather
            
            async def mock_gather(*args, **kwargs):
                # Simulate batch exception
                raise Exception("Test error")
                
            # Patch the asyncio.gather function to fail
            with patch('asyncio.gather', side_effect=mock_gather):
                # Create test batch
                content_items = [
                    {"content": "<h1>Item 1</h1>"},
                    {"content": "<h1>Item 2</h1>"},
                    {"content": "<h1>Item 3</h1>"}
                ]
                
                # Process batch with simulated batch failure
                results = await processor.process_batch(content_items)
                
                # Should return results for all items with failure indicators
                assert len(results) == 3
                
                # Each result should contain the original content and failure indicator
                for i, result in enumerate(results):
                    assert result["success"] is False
                    assert "Batch error" in result["message"]
                    assert f"Item {i+1}" in content_items[i]["content"]
    
    def test_cache_stats(self, processor):
        """Test cache statistics reporting."""
        # Set up some hits and misses
        processor._cache_hits = 10
        processor._cache_misses = 5
        processor._cache = {"key1": "value1", "key2": "value2"}
        
        # Get stats
        stats = processor.get_cache_stats()
        
        # Check stats
        assert stats["cache_size"] == 2
        assert stats["cache_hits"] == 10
        assert stats["cache_misses"] == 5
        assert stats["hit_rate_percent"] == 10 / 15 * 100
        assert stats["cache_dir"] == processor._cache_dir
    
    def test_clear_cache(self, processor):
        """Test clearing the cache."""
        # Populate cache
        processor._cache = {"key1": "value1", "key2": "value2"}
        processor._cache_hits = 10
        processor._cache_misses = 5
        
        # Clear cache
        processor.clear_cache()
        
        # Check cache is empty
        assert processor._cache == {}
        assert processor._cache_hits == 0
        assert processor._cache_misses == 0
        
    @pytest.mark.asyncio
    async def test_estimate_token_count(self, processor):
        """Test token count estimation."""
        # Test with various texts
        short_text = "This is a short text."
        long_text = "This is a longer text with multiple sentences. " * 10
        
        # Test token count estimation
        short_count = await processor.estimate_token_count(short_text)
        long_count = await processor.estimate_token_count(long_text)
        
        # Simple checks
        assert short_count > 0
        assert long_count > short_count
        assert short_count == len(short_text) // 4
        assert long_count == len(long_text) // 4
