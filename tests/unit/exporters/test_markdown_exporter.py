"""
Unit tests for the Markdown exporter.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from src.exporters.markdown_exporter import MarkdownExporter, FileExportError


class TestMarkdownExporter:
    """Tests for the MarkdownExporter class."""

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
                "content": "<article><h1>Page 1</h1><p>This is page 1 with <a href='page2'>a link</a>.</p><pre><code class='language-python'>def hello():\n    print('Hello world')</code></pre></article>",
                "metadata": {"depth": 1}
            },
            "https://example.com/docs/page2": {
                "title": "Page 2",
                "content": "<article><h1>Page 2</h1><p>This is page 2 with <strong>bold text</strong> and <em>italics</em>.</p><ul><li>Item 1</li><li>Item 2</li></ul></article>",
                "metadata": {"depth": 1}
            }
        }

    @pytest.fixture
    def exporter(self):
        """Create a MarkdownExporter instance for testing."""
        return MarkdownExporter(
            table_of_contents=True,
            include_links=True,
            include_images=True
        )

    @pytest.mark.asyncio
    async def test_export_format(self, exporter):
        """Test that the exporter returns the correct format."""
        assert exporter.format == "markdown"

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
            assert result["format"] == "markdown"

            # Check that main file was created
            main_file = Path(temp_dir) / "TestProject.md"
            assert main_file.exists()
            assert main_file.is_file()

            # Check the content of the main file
            content = main_file.read_text()
            assert "# TestProject" in content
            assert "## Metadata" in content
            assert "test_key" in content
            assert "## Table of Contents" in content
            assert "- [Example Documentation](#example-documentation)" in content
            assert "## Example Documentation" in content
            assert "## Page 1" in content
            assert "## Page 2" in content
            assert "```python" in content  # Code block with language

    @pytest.mark.asyncio
    async def test_export_with_no_toc(self, sample_content_map):
        """Test export without table of contents."""
        exporter = MarkdownExporter(table_of_contents=False)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await exporter.export(
                content_map=sample_content_map,
                output_dir=temp_dir,
                project_name="NoTOC",
                metadata={}
            )
            
            main_file = Path(temp_dir) / "NoTOC.md"
            content = main_file.read_text()
            
            assert "## Table of Contents" not in content
            assert "## Example Documentation" in content

    @pytest.mark.asyncio
    async def test_export_individual_files(self, exporter, sample_content_map):
        """Test export with many pages creates individual files."""
        # Create a larger content map to trigger individual file creation
        large_content_map = {f"https://example.com/docs/page{i}": {
            "title": f"Page {i}",
            "content": f"<article><h1>Page {i}</h1><p>Content {i}</p></article>",
            "metadata": {"depth": 1}
        } for i in range(20)}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await exporter.export(
                content_map=large_content_map,
                output_dir=temp_dir,
                project_name="LargeProject",
                metadata={}
            )
            
            # Check that pages directory was created
            pages_dir = Path(temp_dir) / "LargeProject_pages"
            assert pages_dir.exists()
            assert pages_dir.is_dir()
            
            # Check that README index was created
            index_file = pages_dir / "README.md"
            assert index_file.exists()
            
            # Check that individual page files were created
            assert len(list(pages_dir.glob("*.md"))) > 20  # README + page files

    @pytest.mark.asyncio
    async def test_html_to_markdown_conversion(self, exporter):
        """Test HTML to Markdown conversion features."""
        html = """
        <article>
            <h1>Test Document</h1>
            <p>This is a <strong>test</strong> with <em>formatting</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2 with <a href="https://example.com">link</a></li>
            </ul>
            <pre><code class="language-python">
def example():
    return "Hello World"
            </code></pre>
        </article>
        """
        
        markdown = exporter._html_to_markdown(html)
        
        # Check that headings are preserved
        assert "# Test Document" in markdown
        
        # Check that formatting is preserved
        assert "**test**" in markdown
        assert "*formatting*" in markdown
        
        # Check that lists are preserved
        assert "* Item 1" in markdown
        assert "* Item 2 with" in markdown
        
        # Check that links are preserved
        assert "[link](https://example.com)" in markdown
        
        # Check that code blocks are preserved with language
        assert "```python" in markdown
        assert "def example():" in markdown
        assert "return \"Hello World\"" in markdown
        assert "```" in markdown

    @pytest.mark.asyncio
    async def test_sanitize_filename(self, exporter):
        """Test filename sanitization."""
        # Test invalid characters
        assert exporter._sanitize_filename("file:with?invalid*chars") == "file_with_invalid_chars"
        
        # Test whitespace
        assert exporter._sanitize_filename("  trim spaces  ") == "trim spaces"
        
        # Test empty string
        assert exporter._sanitize_filename("") == "untitled"
        
        # Test very long name
        long_name = "a" * 200
        assert len(exporter._sanitize_filename(long_name)) <= 100

    @pytest.mark.asyncio
    async def test_make_anchor(self, exporter):
        """Test anchor creation for linking."""
        # Test spaces to hyphens
        assert exporter._make_anchor("Test Heading") == "test-heading"
        
        # Test special characters removed
        assert exporter._make_anchor("Test & Heading!") == "test-heading"
        
        # Test case conversion
        assert exporter._make_anchor("ALL CAPS") == "all-caps"
