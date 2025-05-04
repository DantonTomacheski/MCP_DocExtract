"""
Unit tests for MCP request schema models.

These tests verify that the request models work correctly,
including validation, defaults, and conversion.
"""

import pytest
from pydantic import ValidationError, HttpUrl

from src.server.schemas.requests import (
    ScrapingMode,
    ExtractDocumentRequest,
    ProcessContentRequest,
    ExportContentRequest,
    StatusCheckRequest
)


class TestScrapingMode:
    """Tests for the ScrapingMode enum."""
    
    def test_valid_modes(self):
        """Test that valid scraping modes can be used."""
        assert ScrapingMode.GENERIC == "generic"
        assert ScrapingMode.DEEPWIKI == "deepwiki"
        assert ScrapingMode.AUTO == "auto"
        
    def test_from_string(self):
        """Test that a ScrapingMode can be created from a string."""
        assert ScrapingMode("generic") == ScrapingMode.GENERIC
        assert ScrapingMode("deepwiki") == ScrapingMode.DEEPWIKI
        assert ScrapingMode("auto") == ScrapingMode.AUTO
        
    def test_invalid_mode(self):
        """Test that an invalid mode raises a ValueError."""
        with pytest.raises(ValueError):
            ScrapingMode("invalid_mode")


class TestExtractDocumentRequest:
    """Tests for the ExtractDocumentRequest model."""
    
    def test_minimal_valid_request(self):
        """Test that a request with just the required fields is valid."""
        request = ExtractDocumentRequest(url="https://example.com")
        
        # Check that defaults are set correctly
        assert request.url == "https://example.com"
        assert request.mode == ScrapingMode.AUTO
        assert request.parallel is True
        assert request.max_depth == 5
        assert request.concurrency == 3
        assert request.use_ai is True
        assert request.filters is None
        
    def test_full_request(self):
        """Test that a request with all fields is valid."""
        request = ExtractDocumentRequest(
            url="https://example.com",
            mode=ScrapingMode.DEEPWIKI,
            parallel=False,
            max_depth=3,
            concurrency=5,
            use_ai=False,
            filters={"include": ["docs/*"], "exclude": ["blog/*"]}
        )
        
        assert request.url == "https://example.com"
        assert request.mode == ScrapingMode.DEEPWIKI
        assert request.parallel is False
        assert request.max_depth == 3
        assert request.concurrency == 5
        assert request.use_ai is False
        assert request.filters["include"] == ["docs/*"]
        
    def test_invalid_url(self):
        """Test that an invalid URL raises a ValidationError."""
        with pytest.raises(ValidationError):
            ExtractDocumentRequest(url="not_a_url")
            
    def test_invalid_max_depth(self):
        """Test that invalid max_depth values raise ValidationError."""
        with pytest.raises(ValueError) as exc_info:
            ExtractDocumentRequest(url="https://example.com", max_depth=0)
        assert "max_depth must be between 1 and 10" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            ExtractDocumentRequest(url="https://example.com", max_depth=11)
        assert "max_depth must be between 1 and 10" in str(exc_info.value)
        
    def test_invalid_concurrency(self):
        """Test that invalid concurrency values raise ValidationError."""
        with pytest.raises(ValueError) as exc_info:
            ExtractDocumentRequest(url="https://example.com", concurrency=0)
        assert "concurrency must be between 1 and 10" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            ExtractDocumentRequest(url="https://example.com", concurrency=11)
        assert "concurrency must be between 1 and 10" in str(exc_info.value)


class TestProcessContentRequest:
    """Tests for the ProcessContentRequest model."""
    
    def test_minimal_valid_request(self):
        """Test that a request with just the required fields is valid."""
        request = ProcessContentRequest(content="<p>Test content</p>")
        
        # Check that defaults are set correctly
        assert request.content == "<p>Test content</p>"
        assert request.context is None
        assert request.content_type == "documentation"
        assert request.processing_mode == "clean"
        
    def test_full_request(self):
        """Test that a request with all fields is valid."""
        request = ProcessContentRequest(
            content="<p>Test content</p>",
            context="This is a page about testing",
            content_type="tutorial",
            processing_mode="summarize"
        )
        
        assert request.content == "<p>Test content</p>"
        assert request.context == "This is a page about testing"
        assert request.content_type == "tutorial"
        assert request.processing_mode == "summarize"
        
    def test_empty_content(self):
        """Test that empty content raises ValidationError."""
        with pytest.raises(ValueError) as exc_info:
            ProcessContentRequest(content="")
        assert "content cannot be empty" in str(exc_info.value)
        
    def test_content_too_large(self):
        """Test that content that is too large raises ValidationError."""
        large_content = "x" * 100001  # Just over 100KB
        with pytest.raises(ValueError) as exc_info:
            ProcessContentRequest(content=large_content)
        assert "content is too large" in str(exc_info.value)


class TestExportContentRequest:
    """Tests for the ExportContentRequest model."""
    
    def test_with_operation_id(self):
        """Test request with operation_id is valid."""
        request = ExportContentRequest(operation_id="abc123")
        
        assert request.operation_id == "abc123"
        assert request.content_map is None
        assert request.format == "json"
        assert request.project_name is None
        assert request.include_metadata is True
        
    def test_with_content_map(self):
        """Test request with content_map is valid."""
        content_map = {
            "https://example.com/page1": "<p>Page 1 content</p>",
            "https://example.com/page2": "<p>Page 2 content</p>"
        }
        request = ExportContentRequest(content_map=content_map)
        
        assert request.operation_id is None
        assert request.content_map == content_map
        assert request.format == "json"
        
    def test_without_content_source(self):
        """Test that missing both operation_id and content_map raises ValidationError."""
        with pytest.raises(ValueError) as exc_info:
            ExportContentRequest()
        assert "Either content_map or operation_id must be provided" in str(exc_info.value)
        
    def test_invalid_format(self):
        """Test that invalid format raises ValidationError."""
        with pytest.raises(ValueError) as exc_info:
            ExportContentRequest(
                operation_id="abc123",
                format="invalid_format"
            )
        assert "format must be one of" in str(exc_info.value)
        
    def test_valid_formats(self):
        """Test that all valid formats are accepted."""
        for fmt in ["json", "markdown", "both"]:
            request = ExportContentRequest(
                operation_id="abc123",
                format=fmt
            )
            assert request.format == fmt


class TestStatusCheckRequest:
    """Tests for the StatusCheckRequest model."""
    
    def test_minimal_valid_request(self):
        """Test that a request with just the required fields is valid."""
        request = StatusCheckRequest(operation_id="abc123")
        
        assert request.operation_id == "abc123"
        assert request.include_details is False
        
    def test_full_request(self):
        """Test that a request with all fields is valid."""
        request = StatusCheckRequest(
            operation_id="abc123",
            include_details=True
        )
        
        assert request.operation_id == "abc123"
        assert request.include_details is True
        
    def test_missing_operation_id(self):
        """Test that missing operation_id raises ValidationError."""
        with pytest.raises(ValidationError):
            StatusCheckRequest()
