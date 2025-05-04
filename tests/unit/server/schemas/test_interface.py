"""
Unit tests for MCP interface components.

These tests verify that the MCP interface components work correctly,
including the MCPToolRegistry functionality.
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError
from typing import Dict, List, Any

from src.server.schemas.interface import (
    MCPToolRegistry,
    mcp_registry
)
from src.server.schemas.mcp import (
    MCPInvokeRequest,
    MCPToolsResponse,
    MCPInvokeResponse,
    MCPError
)
from src.server.schemas.requests import (
    ExtractDocumentRequest,
    ProcessContentRequest,
    ExportContentRequest,
    StatusCheckRequest
)


class TestMCPToolRegistry:
    """Tests for the MCPToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test that the registry is initialized correctly."""
        registry = MCPToolRegistry()
        
        # Verify that all tools are registered
        assert "extract_document" in registry.tools
        assert "process_content" in registry.tools
        assert "export_content" in registry.tools
        assert "check_status" in registry.tools
        assert "detect_framework" in registry.tools
        assert len(registry.tools) == 5
        
    def test_get_tools_response(self):
        """Test that the get_tools_response method returns a valid response."""
        registry = MCPToolRegistry()
        response = registry.get_tools_response()
        
        # Verify response structure
        assert isinstance(response, MCPToolsResponse)
        assert len(response.tools) == 5
        
        # Check that each tool has the expected fields
        for tool in response.tools:
            assert tool.name in registry.tools.keys()
            assert tool.description
            assert tool.parameters_schema
            assert tool.parameters_schema["type"] == "object"
            assert "properties" in tool.parameters_schema
        
    def test_validate_request_valid(self):
        """Test that valid requests pass validation."""
        registry = MCPToolRegistry()
        
        # Valid extract_document request
        request = MCPInvokeRequest(
            name="extract_document",
            parameters={"url": "https://example.com"}
        )
        error = registry.validate_request(request)
        assert error is None
        
        # Valid process_content request
        request = MCPInvokeRequest(
            name="process_content",
            parameters={"content": "Test content"}
        )
        error = registry.validate_request(request)
        assert error is None
        
        # Valid export_content request with operation_id
        request = MCPInvokeRequest(
            name="export_content",
            parameters={"operation_id": "abc123"}
        )
        error = registry.validate_request(request)
        assert error is None
        
        # Valid export_content request with content_map
        request = MCPInvokeRequest(
            name="export_content",
            parameters={"content_map": {"url": "content"}}
        )
        error = registry.validate_request(request)
        assert error is None
        
        # Valid check_status request
        request = MCPInvokeRequest(
            name="check_status",
            parameters={"operation_id": "abc123"}
        )
        error = registry.validate_request(request)
        assert error is None
        
        # Valid detect_framework request
        request = MCPInvokeRequest(
            name="detect_framework",
            parameters={"url": "https://example.com"}
        )
        error = registry.validate_request(request)
        assert error is None
        
    def test_validate_request_invalid_tool(self):
        """Test that requests with invalid tool names fail validation."""
        registry = MCPToolRegistry()
        
        # Invalid tool name
        request = MCPInvokeRequest(
            name="invalid_tool",
            parameters={}
        )
        
        # This will not reach the registry validation because the model validator will catch it first
        with pytest.raises(ValueError):
            error = registry.validate_request(request)
            
    def test_validate_request_invalid_parameters(self):
        """Test that requests with invalid parameters fail validation."""
        registry = MCPToolRegistry()
        
        # Invalid extract_document request (missing url)
        request = MCPInvokeRequest(
            name="extract_document",
            parameters={}
        )
        error = registry.validate_request(request)
        assert error is not None
        assert "url" in error.lower()
        
        # Invalid process_content request (missing content)
        request = MCPInvokeRequest(
            name="process_content",
            parameters={}
        )
        error = registry.validate_request(request)
        assert error is not None
        assert "content" in error.lower()
        
        # Invalid export_content request (missing both operation_id and content_map)
        request = MCPInvokeRequest(
            name="export_content",
            parameters={}
        )
        error = registry.validate_request(request)
        assert error is not None
        assert "operation_id" in error.lower() or "content_map" in error.lower()
        
        # Invalid check_status request (missing operation_id)
        request = MCPInvokeRequest(
            name="check_status",
            parameters={}
        )
        error = registry.validate_request(request)
        assert error is not None
        assert "operation_id" in error.lower()
        
        # Invalid detect_framework request (missing url)
        request = MCPInvokeRequest(
            name="detect_framework",
            parameters={}
        )
        error = registry.validate_request(request)
        assert error is not None
        assert "url" in error.lower()
        
    def test_format_response(self):
        """Test that format_response returns a valid response."""
        registry = MCPToolRegistry()
        tool_name = "extract_document"
        result = {"operation_id": "abc123", "status": "pending"}
        
        response = registry.format_response(tool_name, result)
        
        assert isinstance(response, MCPInvokeResponse)
        assert response.tool_name == tool_name
        assert response.result == result
        assert response.error is None
        
    def test_format_error(self):
        """Test that format_error returns a valid error response."""
        registry = MCPToolRegistry()
        error_msg = "An error occurred"
        details = {"field": "url", "message": "Invalid URL format"}
        
        error = registry.format_error(error_msg, details)
        
        assert isinstance(error, MCPError)
        assert error.error == error_msg
        assert error.details == details
        
        # Test with no details
        error = registry.format_error(error_msg)
        assert error.error == error_msg
        assert error.details is None
        
    def test_global_registry_singleton(self):
        """Test that the global registry singleton exists and is properly initialized."""
        assert mcp_registry is not None
        assert isinstance(mcp_registry, MCPToolRegistry)
        assert len(mcp_registry.tools) == 5
