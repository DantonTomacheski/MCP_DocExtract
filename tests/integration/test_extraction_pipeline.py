"""
Integration tests for the full extraction pipeline.

These tests verify the end-to-end workflow of the extraction pipeline
using real or mocked documentation websites.
"""

import os
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from src.controllers.main_controller import MainController
from src.extractors.content.generic import GenericContentExtractor
from src.extractors.content.deepwiki import DeepWikiContentExtractor
from src.extractors.links.generic import GenericLinkExtractor 
from src.extractors.links.deepwiki import DeepWikiLinkExtractor


class TestExtractionPipeline:
    """Integration tests for the full extraction pipeline."""

    @pytest.fixture
    def controller(self):
        """Create a MainController instance for testing."""
        return MainController()

    @pytest.fixture
    def mock_html_response(self):
        """Mock HTML response for testing without network access."""
        mock_responses = {
            "https://example.com/docs": "<html><body><h1>Example Documentation</h1></body></html>",
            "https://example.com/docs/getting-started": "<html><body><h1>Getting Started</h1></body></html>",
            "https://example.com/docs/api-reference": "<html><body><h1>API Reference</h1></body></html>"
        }
        
        def _get_html(url):
            return mock_responses.get(url, "<html><body><h1>Page Not Found</h1></body></html>")
            
        return _get_html

    @pytest.mark.asyncio
    async def test_generic_extraction_pipeline(self, controller, mock_html_response):
        """Test the full extraction pipeline with generic extractors."""
        # Set up the controller with generic extractors
        controller.content_extractor = GenericContentExtractor()
        controller.link_extractor = GenericLinkExtractor()
        
        # Create a mock for the fetch_content method
        mock_fetch = MagicMock(return_value={
            "success": True, 
            "html": mock_html_response("https://example.com/docs"), 
            "status_code": 200
        })
        
        # Patch the scraper to use our mock HTML responses
        with patch('src.services.sequential_service.SequentialScraperService._fetch_content', 
                   side_effect=mock_fetch):
            
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run the extraction pipeline
                result = await controller.async_run(
                    url="https://example.com/docs",
                    mode="generic",
                    output_dir=temp_dir,
                    parallel=False,
                    max_depth=2,
                    use_ai=False
                )
                
                # Check that the operation was started
                assert result["status"] == "running"
                
                # Get the operation ID
                operation_id = result["operation_id"]
                
                # Wait for the operation to complete (simple polling)
                max_retries = 3
                retry_count = 0
                status = "running"
                
                while status == "running" and retry_count < max_retries:
                    # Check the operation status
                    status_result = controller.get_operation_status(operation_id)
                    status = status_result["status"]
                    await asyncio.sleep(0.5)
                    retry_count += 1

    @pytest.mark.asyncio
    async def test_deepwiki_extraction_pipeline(self, mock_html_response):
        """Test the full extraction pipeline with DeepWiki-specific extractors."""
        # Create a controller with DeepWiki extractors
        controller = MainController()
        controller.content_extractor = DeepWikiContentExtractor()
        controller.link_extractor = DeepWikiLinkExtractor()
        
        # Create a mock for the fetch_content method
        mock_fetch = MagicMock(return_value={
            "success": True, 
            "html": mock_html_response("https://example.com/docs"), 
            "status_code": 200
        })
        
        # Patch the scraper to use our mock HTML responses
        with patch('src.services.sequential_service.SequentialScraperService._fetch_content', 
                   side_effect=mock_fetch):
            
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run the extraction pipeline
                result = await controller.async_run(
                    url="https://example.com/docs",
                    mode="deepwiki",
                    output_dir=temp_dir,
                    parallel=False,
                    max_depth=2,
                    use_ai=False
                )
                
                # Check that the operation was started
                assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_multi_page_extraction(self, controller):
        """Test extracting and processing multiple pages."""
        # Create a simulated content map with multiple pages
        mock_content_map = {
            "https://example.com/docs/": {
                "title": "Example Documentation",
                "content": "<article><h1>Example Documentation</h1><p>This is the main page.</p></article>",
                "metadata": {"depth": 0},
            },
            "https://example.com/docs/getting-started": {
                "title": "Getting Started",
                "content": "<article><h1>Getting Started</h1><p>This is the getting started page.</p></article>",
                "metadata": {"depth": 1},
            },
            "https://example.com/docs/api-reference": {
                "title": "API Reference",
                "content": "<article><h1>API Reference</h1><p>This is the API reference page.</p></article>",
                "metadata": {"depth": 1},
            }
        }
        
        # Create a mock scraping result
        mock_scrape_result = {
            "content_map": mock_content_map,
            "stats": {
                "urls_discovered": 5,
                "urls_processed": 3,
                "extraction_time_ms": 1500,
                "progress_percent": 100.0,
                "is_complete": True
            }
        }
        
        # Patch the _run_scraping method to return our mock result
        with patch.object(controller, '_run_scraping', return_value=mock_scrape_result):
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run the extraction pipeline
                result = controller.run(
                    url="https://example.com/docs",
                    mode="generic",
                    output_dir=temp_dir,
                    parallel=False,
                    max_depth=2,
                    use_ai=False,
                    export_format="both"
                )
                
                # Check that the operation was successful
                assert result["status"] == "completed"
                
                # Check that an operation ID was returned
                assert "operation_id" in result

    @pytest.mark.asyncio
    async def test_extraction_error_handling(self, controller):
        """Test handling of errors during extraction."""
        # Patch the _run_scraping method to raise an exception
        with patch.object(controller, '_run_scraping', side_effect=Exception("Test extraction error")):
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run the extraction pipeline
                result = controller.run(
                    url="https://example.com/docs",
                    mode="generic",
                    output_dir=temp_dir,
                    parallel=False,
                    max_depth=2,
                    use_ai=False,
                    export_format="both"
                )
                
                # Check that the operation failed
                assert result["status"] == "failed"
                assert "Error" in result["message"]
