"""
Unit tests for MCP protocol schema models.

These tests verify that the MCP protocol schema models work correctly,
including validation, serialization, and helper functions.
"""

import pytest
from pydantic import ValidationError
from typing import Dict, Any

from src.server.schemas.mcp import (
    MCPToolReference,
    MCPToolsResponse,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPError,
    tool_schema_to_reference
)


class TestMCPToolReference:
    """Tests for the MCPToolReference model."""

    def test_valid_tool_reference(self):
        """Test that a valid tool reference can be created."""
        tool_ref = MCPToolReference(
            name="test_tool",
            description="A test tool",
            parameters_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                }
            }
        )
        
        assert tool_ref.name == "test_tool"
        assert tool_ref.description == "A test tool"
        assert tool_ref.parameters_schema["type"] == "object"
        
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            MCPToolReference(name="test_tool")
        
        with pytest.raises(ValidationError):
            MCPToolReference(description="A test tool")
            
        with pytest.raises(ValidationError):
            MCPToolReference(parameters_schema={"type": "object"})


class TestMCPToolsResponse:
    """Tests for the MCPToolsResponse model."""
    
    def test_valid_tools_response(self):
        """Test that a valid tools response can be created."""
        tool_ref = MCPToolReference(
            name="test_tool",
            description="A test tool",
            parameters_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                }
            }
        )
        
        response = MCPToolsResponse(tools=[tool_ref])
        assert len(response.tools) == 1
        assert response.tools[0].name == "test_tool"
        
    def test_empty_tools_list(self):
        """Test that an empty tools list raises ValidationError."""
        with pytest.raises(ValidationError):
            MCPToolsResponse(tools=[])


class TestMCPInvokeRequest:
    """Tests for the MCPInvokeRequest model."""
    
    def test_valid_invoke_request(self):
        """Test that a valid invoke request can be created."""
        request = MCPInvokeRequest(
            name="extract_document",
            parameters={"url": "https://example.com"}
        )
        
        assert request.name == "extract_document"
        assert request.parameters["url"] == "https://example.com"
        
    def test_missing_name(self):
        """Test that missing name raises ValidationError."""
        with pytest.raises(ValidationError):
            MCPInvokeRequest(parameters={"url": "https://example.com"})
            
    def test_default_empty_parameters(self):
        """Test that parameters default to empty dict if not provided."""
        request = MCPInvokeRequest(name="extract_document")
        assert request.parameters == {}
        
    def test_tool_name_validation(self):
        """Test that invalid tool names are rejected."""
        with pytest.raises(ValueError) as exc_info:
            MCPInvokeRequest(name="invalid_tool")
        
        # Check that the error message contains the list of valid tools
        error_msg = str(exc_info.value)
        assert "invalid_tool" in error_msg
        assert "extract_document" in error_msg
        assert "process_content" in error_msg


class TestMCPInvokeResponse:
    """Tests for the MCPInvokeResponse model."""
    
    def test_valid_invoke_response(self):
        """Test that a valid invoke response can be created."""
        response = MCPInvokeResponse(
            tool_name="extract_document",
            result={"operation_id": "123456"}
        )
        
        assert response.tool_name == "extract_document"
        assert response.result["operation_id"] == "123456"
        assert response.error is None
        
    def test_with_error(self):
        """Test that a response with an error can be created."""
        response = MCPInvokeResponse(
            tool_name="extract_document",
            result={},
            error="Something went wrong"
        )
        
        assert response.tool_name == "extract_document"
        assert response.error == "Something went wrong"


class TestMCPError:
    """Tests for the MCPError model."""
    
    def test_valid_error(self):
        """Test that a valid error can be created."""
        error = MCPError(error="Something went wrong")
        assert error.error == "Something went wrong"
        assert error.details is None
        
    def test_with_details(self):
        """Test that an error with details can be created."""
        error = MCPError(
            error="Validation failed",
            details={"field": "url", "message": "Invalid URL"}
        )
        
        assert error.error == "Validation failed"
        assert error.details["field"] == "url"
        assert error.details["message"] == "Invalid URL"


class TestToolSchemaToReference:
    """Tests for the tool_schema_to_reference helper function."""
    
    def test_conversion(self):
        """Test that a tool schema can be converted to a reference."""
        tool_schema = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "URL to scrape",
                    "required": True
                },
                "depth": {
                    "type": "integer",
                    "description": "Crawl depth",
                    "required": False
                }
            }
        }
        
        ref = tool_schema_to_reference(tool_schema)
        assert isinstance(ref, MCPToolReference)
        assert ref.name == "test_tool"
        assert ref.description == "A test tool"
        
        # Verify parameters schema structure
        params = ref.parameters_schema
        assert params["type"] == "object"
        assert "url" in params["properties"]
        assert "depth" in params["properties"]
        
        # Verify required fields
        assert "url" in params["required"]
        assert "depth" not in params["required"]
