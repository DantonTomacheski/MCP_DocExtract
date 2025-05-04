"""
Unit tests for the JSON exporter.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path

from src.exporters.json_exporter import JSONExporter


class TestJSONExporter:
    """Tests for the JSONExporter class."""

    @pytest.fixture
    def sample_content_map(self):
        """Create a sample content map for testing."""
        return {
            "https://example.com/docs/": {
                "title": "Example Documentation",
                "content": "<article><h1>Example Documentation</h1><p>This is the main page.</p></article>",
                "metadata": {"depth": 0}
            },
            "https://example.com/docs/page1": {
                "title": "Page 1",
                "content": "<article><h1>Page 1</h1><p>This is page 1 with a link.</p></article>",
                "metadata": {"depth": 1}
            },
            "https://example.com/docs/page2": {
                "title": "Page 2",
                "content": "<article><h1>Page 2</h1><p>This is page 2.</p></article>",
                "metadata": {"depth": 1}
            }
        }

    @pytest.fixture
    def exporter(self):
        """Create a JSONExporter instance for testing."""
        return JSONExporter()

    @pytest.mark.asyncio
    async def test_export_format(self, exporter):
        """Test that the exporter returns the correct format."""
        assert exporter.format == "json"

    @pytest.mark.asyncio
    async def test_export_creates_files(self, exporter, sample_content_map):
        """Test that export creates expected files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the export
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="TestProject",
                metadata={"test_key": "test_value"}
            )

            # Check result structure
            assert "files" in result
            assert "total_size" in result
            assert "file_count" in result
            assert "format" in result
            assert result["format"] == "json"

            # Check that main file was created
            main_file = Path(temp_dir) / "TestProject.json"
            assert main_file.exists()
            assert main_file.is_file()

            # Load and check JSON content
            with open(main_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # Check structure
                assert "metadata" in content
                assert "content" in content
                assert "test_key" in content["metadata"]
                assert len(content["content"]) == 3  # 3 pages
                
                # Check content data
                page_urls = [page["url"] for page in content["content"]]
                assert "https://example.com/docs/" in page_urls
                assert "https://example.com/docs/page1" in page_urls
                assert "https://example.com/docs/page2" in page_urls

    @pytest.mark.asyncio
    async def test_export_with_pretty_print(self, sample_content_map):
        """Test export with pretty_print option."""
        exporter = JSONExporter(pretty_print=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="PrettyJSON",
                metadata={}
            )
            
            main_file = Path(temp_dir) / "PrettyJSON.json"
            content = main_file.read_text()
            
            # Check for indentation (pretty printing)
            assert "{\n  " in content
            assert "  \"metadata\": {" in content

    @pytest.mark.asyncio
    async def test_export_without_pretty_print(self, sample_content_map):
        """Test export without pretty_print option."""
        exporter = JSONExporter(pretty_print=False)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="CompactJSON",
                metadata={}
            )
            
            main_file = Path(temp_dir) / "CompactJSON.json"
            content = main_file.read_text()
            
            # Check for lack of newlines and indentation
            assert not "{\n  " in content
            assert "{\"metadata\":" in content

    @pytest.mark.asyncio
    async def test_metadata_inclusion(self, exporter, sample_content_map):
        """Test that metadata is properly included."""
        metadata = {
            "extractor_version": "1.0.0",
            "extraction_date": "2023-01-01T00:00:00Z",
            "extraction_parameters": {
                "max_depth": 3,
                "parallel": False
            },
            "stats": {
                "total_pages": 3,
                "extraction_time_seconds": 1.5
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="MetadataTest",
                metadata=metadata
            )
            
            main_file = Path(temp_dir) / "MetadataTest.json"
            
            with open(main_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # Check that all metadata is included
                for key, value in metadata.items():
                    assert key in content["metadata"]
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            assert sub_key in content["metadata"][key]
                            assert content["metadata"][key][sub_key] == sub_value
                    else:
                        assert content["metadata"][key] == value
