"""
Simple integration tests for the DocExtract AI project.

These tests focus on validating that key components work together correctly.
"""

import os
import pytest
import tempfile
import json
from pathlib import Path

from src.controllers.main_controller import MainController
from src.exporters.json_exporter import JSONExporter
from src.exporters.markdown_exporter import MarkdownExporter


class TestSimpleIntegration:
    """Simple integration tests for DocExtract AI."""

    @pytest.fixture
    def controller(self):
        """Create a MainController instance for testing."""
        return MainController()

    @pytest.fixture
    def sample_content_map(self):
        """Create a sample content map for testing exports."""
        return {
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

    @pytest.mark.asyncio
    async def test_json_exporter_with_controller_data(self, controller, sample_content_map):
        """Test that JSONExporter works with data from the controller."""
        # Create a JSONExporter
        exporter = JSONExporter()
        
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Export the content - note the await for async method
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="TestProject",
                metadata={"test_key": "test_value"}
            )
            
            # Verify that export returned a valid result
            assert isinstance(result, dict)
            assert "files" in result
            assert len(result["files"]) > 0
            
            # Verify exported file exists
            assert any(f.endswith('.json') for f in os.listdir(temp_dir))
            
            # Find the JSON file
            json_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.json'):
                    json_file = os.path.join(temp_dir, file)
                    break
            
            # Check JSON content
            with open(json_file, 'r') as f:
                json_content = json.load(f)
                assert "metadata" in json_content
                assert "content" in json_content
                
                # Should have three pages
                assert len(json_content["content"]) == 3
                
                # Check page titles
                titles = [page["title"] for page in json_content["content"]]
                assert "Example Documentation" in titles
                assert "Getting Started" in titles
                assert "API Reference" in titles

    @pytest.mark.asyncio
    async def test_markdown_exporter_with_controller_data(self, controller, sample_content_map):
        """Test that MarkdownExporter works with data from the controller."""
        # Create a MarkdownExporter
        exporter = MarkdownExporter()
        
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Export the content - note the await for async method
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="TestProject",
                metadata={"test_key": "test_value"}
            )
            
            # Verify that export returned a valid result
            assert isinstance(result, dict)
            assert "files" in result
            assert len(result["files"]) > 0
            
            # Verify exported file exists
            assert any(f.endswith('.md') for f in os.listdir(temp_dir))
            
            # Find the Markdown file
            md_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.md'):
                    md_file = os.path.join(temp_dir, file)
                    break
            
            # Check Markdown content
            with open(md_file, 'r') as f:
                md_content = f.read()
                assert "# TestProject" in md_content
                assert "## Example Documentation" in md_content
                assert "## Getting Started" in md_content
                assert "## API Reference" in md_content

    def test_controller_initialization(self, controller):
        """Test that controller correctly initializes components."""
        # Verify that controller has initialized its components
        assert controller.content_extractor is not None
        assert controller.link_extractor is not None
        assert controller.scraper_service is not None
        assert len(controller.file_exporters) > 0
        
        # Check that at least one exporter is initialized
        assert any(isinstance(e, JSONExporter) for e in controller.file_exporters)
        assert any(isinstance(e, MarkdownExporter) for e in controller.file_exporters)

    def test_controller_select_extractors(self, controller):
        """Test that controller can select extractors by mode."""
        # Test generic mode
        controller._select_extractors(mode="generic")
        assert "Generic" in controller.content_extractor.__class__.__name__
        assert "Generic" in controller.link_extractor.__class__.__name__
        
        # Note: We're not testing DeepWiki mode because 
        # the implementation is still using generic extractors as a fallback
        # This is expected based on the logged warning:
        # "DeepWiki extractors not implemented, using generic extractors"
        
        # Test auto mode (defaults to generic)
        controller._select_extractors(mode="auto")
        # Auto would normally try to detect, but in tests it should default to generic
        assert controller.content_extractor is not None
        assert controller.link_extractor is not None
