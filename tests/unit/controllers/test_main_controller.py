"""
Unit tests for the MainController class.
"""
import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from src.controllers.main_controller import MainController
from src.extractors.content.generic import GenericContentExtractor
from src.extractors.links.generic import GenericLinkExtractor
from src.exporters.json_exporter import JSONExporter
from src.exporters.markdown_exporter import MarkdownExporter
from src.services.sequential_service import SequentialScraperService


class TestMainController:
    """Tests for the MainController class."""

    @pytest.fixture
    def controller(self):
        """Create a MainController instance for testing."""
        return MainController()

    @pytest.fixture
    def sample_scrape_result(self):
        """Create a sample scraping result for mocking."""
        return {
            "content_map": {
                "https://example.com/docs/": {
                    "title": "Example Documentation",
                    "content": "<article><h1>Example Documentation</h1><p>Main page</p></article>",
                    "metadata": {"depth": 0}
                },
                "https://example.com/docs/page1": {
                    "title": "Page 1",
                    "content": "<article><h1>Page 1</h1><p>Content 1</p></article>",
                    "metadata": {"depth": 1}
                }
            },
            "stats": {
                "urls_discovered": 5,
                "urls_processed": 2,
                "extraction_time_ms": 1500,
                "progress_percent": 100.0,
                "is_complete": True
            }
        }

    def test_initialization(self, controller):
        """Test controller initialization."""
        assert controller.content_extractor is not None
        assert controller.link_extractor is not None
        assert controller.scraper_service is not None
        assert len(controller.file_exporters) > 0
        assert isinstance(controller.operations, dict)

    def test_select_extractors(self, controller):
        """Test extraction strategy selection based on mode."""
        # Test generic mode
        controller._select_extractors("generic")
        assert isinstance(controller.content_extractor, GenericContentExtractor)
        assert isinstance(controller.link_extractor, GenericLinkExtractor)

        # Test auto mode
        controller._select_extractors("auto")
        assert isinstance(controller.content_extractor, GenericContentExtractor)
        assert isinstance(controller.link_extractor, GenericLinkExtractor)

        # Test deepwiki mode (falls back to generic for now)
        controller._select_extractors("deepwiki")
        assert isinstance(controller.content_extractor, GenericContentExtractor)
        assert isinstance(controller.link_extractor, GenericLinkExtractor)

        # Test invalid mode
        with pytest.raises(ValueError):
            controller._select_extractors("invalid_mode")

    def test_initialize_scraper_service(self, controller):
        """Test scraper service initialization."""
        # Test sequential service
        controller._initialize_scraper_service(parallel=False, concurrency=3, max_depth=5, use_ai=False)
        assert isinstance(controller.scraper_service, SequentialScraperService)
        assert controller.scraper_service.max_depth == 5

        # Test parallel service (falls back to sequential for now)
        controller._initialize_scraper_service(parallel=True, concurrency=5, max_depth=3, use_ai=False)
        assert isinstance(controller.scraper_service, SequentialScraperService)
        assert controller.scraper_service.max_depth == 3

    def test_initialize_exporters(self, controller):
        """Test file exporter initialization."""
        # Test 'json' format
        controller._initialize_exporters("json")
        assert len(controller.file_exporters) == 1
        assert isinstance(controller.file_exporters[0], JSONExporter)

        # Test 'markdown' format
        controller._initialize_exporters("markdown")
        assert len(controller.file_exporters) == 1
        assert isinstance(controller.file_exporters[0], MarkdownExporter)

        # Test 'both' format
        controller._initialize_exporters("both")
        assert len(controller.file_exporters) == 2
        formats = [exporter.format for exporter in controller.file_exporters]
        assert "json" in formats
        assert "markdown" in formats

        # Test invalid format
        with pytest.raises(ValueError):
            controller._initialize_exporters("invalid_format")

    @patch("src.controllers.main_controller.SequentialScraperService")
    @pytest.mark.asyncio
    async def test_run_scraping(self, mock_service_class, controller, sample_scrape_result):
        """Test the full scraping process."""
        # Set up mocks
        mock_service = AsyncMock()
        mock_service.scrape.return_value = sample_scrape_result
        mock_service_class.return_value = mock_service
        controller.scraper_service = mock_service

        # Set up mock exporters
        mock_json_exporter = AsyncMock()
        mock_json_exporter.format = "json"
        mock_json_exporter.export.return_value = {
            "format": "json",
            "files": [{"path": "/mock/path/output.json", "size": 1000}],
            "total_size": 1000,
            "file_count": 1
        }

        mock_md_exporter = AsyncMock()
        mock_md_exporter.format = "markdown"
        mock_md_exporter.export.return_value = {
            "format": "markdown",
            "files": [{"path": "/mock/path/output.md", "size": 800}],
            "total_size": 800,
            "file_count": 1
        }

        controller.file_exporters = [mock_json_exporter, mock_md_exporter]

        # Create a temporary directory for testing
        with patch("os.makedirs"):
            with patch("os.path.join", return_value="/mock/path"):
                with patch("builtins.open", MagicMock()):
                    with patch("json.dump"):
                        # Execute the method
                        operation_id = "test_op_123"
                        url = "https://example.com/docs/"
                        output_dir = "/mock/output"
                        
                        # Create operation entry
                        controller.operations[operation_id] = {
                            "type": "extraction",
                            "url": url,
                            "status": "running",
                            "started_at": datetime.now(),
                        }
                        
                        # Run the scraping process
                        result = await controller._run_scraping(operation_id, url, output_dir)

                        # Check that scraper service was called correctly
                        mock_service.scrape.assert_called_once_with(url, operation_id)
                        
                        # Check that both exporters were called
                        mock_json_exporter.export.assert_called_once()
                        mock_md_exporter.export.assert_called_once()
                        
                        # Check the result structure
                        assert "operation_id" in result
                        assert "stats" in result
                        assert "exports" in result
                        assert len(result["exports"]) == 2

    @patch("asyncio.get_event_loop")
    @patch("src.controllers.main_controller.MainController._run_scraping")
    def test_run(self, mock_run_scraping, mock_get_event_loop, controller):
        """Test the synchronous run method."""
        # Set up mocks
        mock_loop = MagicMock()
        mock_get_event_loop.return_value = mock_loop
        
        mock_run_future = AsyncMock()
        mock_run_scraping.return_value = mock_run_future
        
        mock_loop.run_until_complete.return_value = {
            "stats": {"urls_discovered": 10, "urls_processed": 5},
            "exports": [{"format": "json"}, {"format": "markdown"}]
        }
        
        # Run the controller with default arguments
        result = controller.run(url="https://example.com/docs/")
        
        # Check that methods were called correctly
        assert mock_get_event_loop.called
        assert mock_loop.run_until_complete.called
        
        # Check the result structure
        assert "operation_id" in result
        assert "status" in result
        assert "message" in result
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_async_run(self, controller):
        """Test the asynchronous run method."""
        # Patch the create_task method
        with patch("asyncio.create_task") as mock_create_task:
            # Run the controller with default arguments
            result = await controller.async_run(url="https://example.com/docs/")
            
            # Check that create_task was called
            assert mock_create_task.called
            
            # Check the result structure
            assert "operation_id" in result
            assert "status" in result
            assert "message" in result
            assert result["status"] == "running"

    def test_get_operation_status(self, controller):
        """Test the operation status retrieval."""
        # Create a test operation
        operation_id = "test_op_456"
        controller.operations[operation_id] = {
            "type": "extraction",
            "url": "https://example.com/docs/",
            "status": "completed",
            "started_at": datetime.now(),
            "updated_at": datetime.now(),
            "progress": 100.0,
            "urls_discovered": 10,
            "urls_processed": 5,
            "message": "Operation completed successfully"
        }
        
        # Get and check the status
        status = controller.get_operation_status(operation_id)
        assert status["type"] == "extraction"
        assert status["status"] == "completed"
        assert status["progress"] == 100.0
        
        # Test non-existent operation
        with pytest.raises(KeyError):
            controller.get_operation_status("non_existent_id")
